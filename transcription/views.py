from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, JsonResponse, FileResponse
import os
import shutil
from .forms import TranscriptUploadForm, ProjectForm
from .models import Transcript, Project

def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    return render(request, 'transcription/project_list.html', {'projects': projects})


def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    return render(request, 'transcription/project_detail.html', {'project': project})


def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            # Automatically set path to Projects folder in parent of BASE_DIR
            project.folder_path = os.path.join(settings.BASE_DIR.parent, 'Projects')
            project.save()
            return redirect('project_list')
    else:
        form = ProjectForm()
    return render(request, 'transcription/create_project.html', {'form': form})

def upload_audio(request):
    if request.method == 'POST':
        form = TranscriptUploadForm(request.POST, request.FILES)
        if form.is_valid():
            transcript_instance = form.save(commit=False)
            transcript_instance.user = request.user
            
            # Manually handle audio file saving
            audio_file = request.FILES.get('audio_file')
            project = transcript_instance.project
            
            if audio_file:
                target_dir = os.path.join(project.folder_path, project.name, 'audio')
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                
                # Use original filename or a secure alternative
                filename = audio_file.name
                target_path = os.path.join(target_dir, filename)
                
                with open(target_path, 'wb+') as destination:
                    for chunk in audio_file.chunks():
                        destination.write(chunk)
                
                transcript_instance.audio_file = filename

            transcript_instance.save()
            return redirect('project_detail', project_id=project.id)
    else:
        form = TranscriptUploadForm()
    return render(request, 'transcription/transcription.html', {'form': form})
from django.core.files.base import ContentFile

def save_record(request):
    """View to save recorded audio and transcript from the browser."""
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        transcript_text = request.POST.get('transcript')
        audio_file = request.FILES.get('audio')

        if not all([project_id, audio_file]):
            return JsonResponse({'status': 'error', 'error': 'Missing data'}, status=400)

        try:
            project = get_object_or_404(Project, id=project_id)

            # Determine user
            user = request.user
            if user.is_anonymous:
                from django.contrib.auth.models import User
                user = User.objects.filter(is_superuser=True).first() or User.objects.first()
                if not user:
                    return JsonResponse({'status': 'error', 'error': 'No user available'}, status=400)

            # Manually save audio to project folder
            target_dir = os.path.join(project.folder_path, project.name, 'audio')
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # Generate filename (mozhi_timestamp.wav)
            import time
            filename = f"record_{int(time.time())}.wav"
            target_path = os.path.join(target_dir, filename)
            
            with open(target_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)

            # Save Transcript record to DB
            transcript_instance = Transcript.objects.create(
                project=project,
                user=user,
                transcript=transcript_text,
                audio_file=filename
            )

            return JsonResponse({'status': 'success', 'transcript_id': str(transcript_instance.id)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'error': 'Method not allowed'}, status=405)


def serve_audio(request, transcript_id):
    """Serves audio files from the project-specific folders."""
    transcript = get_object_or_404(Transcript, id=transcript_id)
    project = transcript.project
    file_path = os.path.join(project.folder_path, project.name, 'audio', transcript.audio_file)
    
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), content_type='audio/wav')
    else:
        return JsonResponse({'error': 'File not found'}, status=404)

import shutil

def delete_project(request, project_id):
    """View to delete a project and optionally its physical files."""
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        delete_files = request.POST.get('delete_files') == 'true'

        try:
            if delete_files:
                target_dir = os.path.join(project.folder_path, project.name)
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
            
            # Delete project from DB (this cascades to Transcripts)
            project.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def delete_transcript(request, transcript_id):
    """View to delete an individual transcript and its physical file."""
    if request.method == 'POST':
        transcript = get_object_or_404(Transcript, id=transcript_id)
        delete_files = request.POST.get('delete_files') == 'true'

        try:
            if delete_files:
                project = transcript.project
                target_path = os.path.join(project.folder_path, project.name, 'audio', transcript.audio_file)
                if os.path.exists(target_path):
                    os.remove(target_path)
            
            transcript.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)