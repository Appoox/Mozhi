import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from transcription.models import Project, Transcript

def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    return render(request, 'export/project_list.html', {'projects': projects})


def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    return render(request, 'export/project_detail.html', {'project': project})

def export_project_json(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    transcripts = Transcript.objects.filter(project=project)
    
    data = []
    for t in transcripts:
        # Get the filename from the audio_file field
        filename = os.path.basename(t.audio_file.name)
        data.append({
            "audio_filepath": f"audio/{filename}",
            "text": t.transcript if t.transcript else ""
        })
    
    response_content = json.dumps(data, indent=4)
    response = HttpResponse(response_content, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="{project.name}_export.json"'
    return response