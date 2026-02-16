from django.shortcuts import render, redirect
from .forms import TranscriptUploadForm, ProjectForm
from .models import Transcript, Project


def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    return render(request, 'transcription/project_list.html', {'projects': projects})


def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('project_list')
    else:
        form = ProjectForm()
    return render(request, 'transcription/create_project.html', {'form': form})

def upload_audio(request):
    if request.method == 'POST':
        # NOTE: You MUST pass request.FILES for file uploads to work
        form = TranscriptUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            # commit=False allows us to modify the object before saving to DB
            transcript_instance = form.save(commit=False)
            
            # Attach the currently logged-in user
            transcript_instance.user = request.user
            
            # 1. Save the file and record to the database
            transcript_instance.save()
            
            # 2. TRIGGER TRANSCRIPTION HERE
            # Now that the file is saved, you can access its path:
            file_path = transcript_instance.audio_file.path
            
            # Example logic (pseudo-code):
            # text_result = run_whisper_ai(file_path)
            # transcript_instance.content = text_result
            # transcript_instance.save()
            
            return redirect('upload_success') # Replace with your success URL
    else:
        form = TranscriptUploadForm()

    return render(request, 'transcription/transcription.html', {'form': form})

from django.http import JsonResponse
import os
from django.conf import settings

def browse_folders(request):
    """View to list subdirectories of a given path for the folder picker."""
    path = request.GET.get('path', str(settings.BASE_DIR))
    
    # Basic security: ensure path is within BASE_DIR or allowed areas
    # For now, let's keep it simple but functional.
    
    try:
        subdirs = [
            d for d in os.listdir(path) 
            if os.path.isdir(os.path.join(path, d)) and not d.startswith('.')
        ]
        subdirs.sort()
        return JsonResponse({
            'current_path': path,
            'parent_path': os.path.dirname(path),
            'subdirs': subdirs
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)