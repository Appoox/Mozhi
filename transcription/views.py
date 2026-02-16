from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
import os
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
            transcript_instance.save()
            project = transcript_instance.project

            try:
                target_dir = os.path.join(project.folder_path, project.name, 'audio')
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                
                filename = os.path.basename(transcript_instance.audio_file.name)
                target_path = os.path.join(target_dir, filename)
                
                with transcript_instance.audio_file.open('rb') as f:
                    with open(target_path, 'wb+') as destination:
                        for chunk in f.chunks():
                            destination.write(chunk)
            except Exception as e:
                print(f"Error saving to external folder: {e}")
            
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
            return JsonResponse({'error': 'Missing data'}, status=400)

        project = get_object_or_404(Project, id=project_id)

        # 1. Save Transcript record to DB (standard Django way)
        transcript_instance = Transcript.objects.create(
            project=project,
            user=request.user,
            transcript=transcript_text,
            audio_file=audio_file
        )

        # 2. ALSO save a copy to the project's specified physical folder
        try:
            # New structure: <base_path>/<project_name>/audio/
            target_dir = os.path.join(project.folder_path, project.name, 'audio')
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # Use the same name as the one saved in MEDIA_ROOT
            filename = os.path.basename(transcript_instance.audio_file.name)
            target_path = os.path.join(target_dir, filename)
            
            # Copy the file
            with transcript_instance.audio_file.open('rb') as f:
                with open(target_path, 'wb+') as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)
        except Exception as e:
            # We log the error but the record is already saved in DB
            print(f"Error saving to external folder: {e}")

        return JsonResponse({'status': 'success', 'transcript_id': str(transcript_instance.id)})

    return JsonResponse({'error': 'Method not allowed'}, status=405)

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