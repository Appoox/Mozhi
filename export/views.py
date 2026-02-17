import json
import os
import shutil
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from transcription.models import Project, Transcript

def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    return render(request, 'export/project_list.html', {'projects': projects})


from django.core.paginator import Paginator

def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    transcripts_list = project.transcripts.all().order_by('-created_at')
    
    paginator = Paginator(transcripts_list, 10) # Show 10 transcripts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'export/project_detail.html', {
        'project': project,
        'page_obj': page_obj
    })


from django.http import StreamingHttpResponse
import time

def export_project_json(request, project_id):
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        transcripts = Transcript.objects.filter(project=project)
        total_count = transcripts.count()

        def stream_progress():
            data = []
            # Send initial count
            yield json.dumps({"type": "init", "total": total_count}) + "\n"
            
            for i, t in enumerate(transcripts, 1):
                # audio_file is now a CharField storing the filename
                filename = os.path.basename(t.audio_file)
                entry = {
                    "audio_filepath": f"audio/{filename}",
                    "text": t.transcript if t.transcript else ""
                }
                data.append(entry)
                
                # Send progress update
                yield json.dumps({"type": "progress", "current": i}) + "\n"
            
            response_content = json.dumps(data, indent=4)
            
            # Save to project folder as details.json
            try:
                project_dir = os.path.join(project.folder_path, project.name)
                if not os.path.exists(project_dir):
                    os.makedirs(project_dir, exist_ok=True)
                    
                json_file_path = os.path.join(project_dir, 'details.json')
                with open(json_file_path, 'w') as f:
                    f.write(response_content)
                
                yield json.dumps({"type": "success", "message": f"Exported to {json_file_path}"}) + "\n"
            except Exception as e:
                yield json.dumps({"type": "error", "error": str(e)}) + "\n"

        return StreamingHttpResponse(stream_progress(), content_type='application/x-ndjson')

    return JsonResponse({'status': 'error', 'error': 'Method not allowed'}, status=405)

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
    """View to delete an individual transcript and optionally its physical file."""
    if request.method == 'POST':
        transcript = get_object_or_404(Transcript, id=transcript_id)
        delete_files = request.POST.get('delete_files') == 'true'

        try:
            if delete_files:
                project = transcript.project
                # audio_file is a CharField
                filename = os.path.basename(transcript.audio_file)
                target_path = os.path.join(project.folder_path, project.name, 'audio', filename)
                if os.path.exists(target_path):
                    os.remove(target_path)
            
            # Delete from DB
            transcript.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)