from Mozhi.settings import PAGE_NUM, SAVE_DIR, BATCH_SIZE
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, JsonResponse, FileResponse
import os
import shutil
from .forms import ProjectForm, ImportProjectForm
from .models import Transcript, Project
from django.core.paginator import Paginator
import json
from django.contrib import messages
from pathlib import Path


def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    form = ProjectForm()
    
    paginator = Paginator(projects, PAGE_NUM) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'transcription/project_list.html', {
        'projects': projects, 
        'form': form,
        'page_obj': page_obj,
        'import_form': ImportProjectForm(),
        })



def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    transcripts_list = project.transcripts.all().order_by('-created_at')
    
    paginator = Paginator(transcripts_list, PAGE_NUM) # Show 10 transcripts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'transcription/project_detail.html', {
        'project': project,
        'page_obj': page_obj,
    })


def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project_name = form.cleaned_data['name']
            target_dir = os.path.join(settings.SAVE_DIR, project_name)
            
            # 1. Validation: Check if a folder with the same name already exists
            if os.path.exists(target_dir):
                messages.error(request, f'A folder named "{project_name}" already exists in the save directory.')
                return redirect('project_list')

            project = form.save(commit=False)
            project.folder_path = settings.SAVE_DIR
            project.save()
            
            # Create the physical folder since it doesn't exist yet
            os.makedirs(target_dir, exist_ok=True)
            
            messages.success(request, 'Project created successfully.')
            return redirect('project_list')
    else:
        form = ProjectForm()
    return render(request, 'transcription/create_project.html', {'form': form})

def import_project(request):
    """View to import an existing project folder and batch-load its JSON."""
    if request.method == 'POST':
        form = ImportProjectForm(request.POST)
        if not form.is_valid():
            for error in form.errors.values():
                messages.error(request, error.as_text())
            return redirect('project_list')

        folder_name = form.cleaned_data['folder_name']
        # folder_path = form.cleaned_data['folder_path']
        sample_rate = form.cleaned_data['sample_rate']  # already an int

        # if folder_path != SAVE_DIR:
        #     messages.error(request, "Folder is not in the correct directory")
        #     return redirect('project_list')
            
        full_target_dir = os.path.join(SAVE_DIR, folder_name)
        
        # 2. Validation: Ensure it doesn't already exist in the database
        if Project.objects.filter(name=folder_name).exists():
            messages.error(request, f'Project "{folder_name}" already exists in the database.')
            return redirect('project_list')

        # Validation: Check if the folder physically exists to import from
        if not os.path.exists(full_target_dir):
            messages.error(request, f'The folder "{full_target_dir}" does not exist on the server.')
            return redirect('project_list')

        try:
            # Create Project Record
            project = Project.objects.create(
                name=folder_name,
                folder_path=SAVE_DIR,
                sample_rate=sample_rate,
                # Note: Add default sample_rate or other fields here if your model requires them
            )

            # 3. Batch import the JSON data
            # Assumes your JSON is a list of dicts: [{"text": "hjkl", "audio_filepath": "audio/d01e9212-f383-415b-849d-1efb41737982.wav"}]
            json_path = os.path.join(full_target_dir, 'details.json') 
            
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Fetch fallback user
                user = request.user if request.user.is_authenticated else None
                if not user:
                    from django.contrib.auth.models import User
                    user = User.objects.filter(is_superuser=True).first() or User.objects.first()

                # Build Transcript instances in memory
                transcripts_to_create = [
                    Transcript(
                        project=project,
                        user=user,
                        transcript=item.get('text'),
                        audio_file=item.get('audio_filepath')
                    ) for item in data
                ]
                
                # Execute batched DB commit (500 items per query) to heavily reduce server load
                Transcript.objects.bulk_create(transcripts_to_create, batch_size=BATCH_SIZE)
                messages.success(request, f'Project "{folder_name}" imported successfully with {len(transcripts_to_create)} transcripts.')
            else:
                messages.warning(request, f'Project "{folder_name}" imported, but no "details.json" was found in the folder.')

        except Exception as e:
            if 'project' in locals():
                project.delete()  # Rollback project creation if something crashes
            messages.error(request, f'Error during import: {str(e)}')
            
        # return redirect('project_list')
        
    return redirect('project_list')

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

            # 1. Create Transcript record FIRST to get UUID
            transcript_instance = Transcript.objects.create(
                project=project,
                user=user,
                transcript=transcript_text,
                audio_file="PENDING"
            )

            # 2. Save audio to project folder using the UUID
            target_dir = os.path.join(project.folder_path, project.name, 'audio')
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            filename = f"{transcript_instance.id}.wav"
            target_path = os.path.join(target_dir, filename)
            
            with open(target_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)

            # 3. Update the record with actual filename
            transcript_instance.audio_file = filename
            transcript_instance.save()

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