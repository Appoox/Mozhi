from Mozhi.settings import PAGE_NUM, BATCH_SIZE
import json
import os
import shutil
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from transcription.models import Project, Transcript
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt


@login_required
def project_list(request):
    projects = Project.objects.all().order_by('-created_at')

    paginator = Paginator(projects, PAGE_NUM) # Show 10 projects per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'export/project_list.html', {
        'projects': projects, 
        'page_obj': page_obj,
        })

@login_required
def _audio_path(transcript):
    """Return the absolute path to a transcript's audio file."""
    project = transcript.project
    return os.path.join(project.folder_path, project.name, 'audio', transcript.audio_file)


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    transcripts_list = project.transcripts.all().order_by('-created_at')

    paginator = Paginator(transcripts_list, PAGE_NUM)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    transcripts_count = transcripts_list.count()

    # Annotate each transcript on the current page with audio_exists so the
    # template can show a warning badge without an extra DB or fs round-trip.
    for t in page_obj:
        t.audio_exists = os.path.exists(_audio_path(t))

    return render(request, 'export/project_detail.html', {
        'project': project,
        'page_obj': page_obj,
        'transcripts_count': transcripts_list,

    })


from django.http import StreamingHttpResponse
import time

@csrf_exempt
@login_required
def export_project_json(request, project_id):
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        total_count = Transcript.objects.filter(project=project).count()
        batch_size = int(BATCH_SIZE)

        def stream_progress():
            data = []
            processed = 0
            missing_files = []

            # Send initial count
            yield json.dumps({"type": "init", "total": total_count}) + "\n"

            # Process in batches using iterator() to avoid loading all records into memory
            transcripts = (
                Transcript.objects
                .filter(project=project)
                .only('audio_file', 'transcript')  # fetch only needed fields
                .iterator(chunk_size=batch_size)
            )

            for t in transcripts:
                filename = os.path.basename(t.audio_file)
                file_path = os.path.join(project.folder_path, project.name, 'audio', filename)

                if not os.path.exists(file_path):
                    missing_files.append(filename)
                    continue  # log and skip missing file

                data.append({
                    "audio_filepath": f"audio/{filename}",
                    "text": t.transcript if t.transcript else ""
                })
                processed += 1

                # Yield a progress update after each batch boundary
                if processed % batch_size == 0:
                    yield json.dumps({"type": "progress", "current": processed}) + "\n"

            # Yield final progress if the total wasn't a clean multiple of batch_size
            if processed % batch_size != 0:
                yield json.dumps({"type": "progress", "current": processed}) + "\n"

            # Save to project folder as details.json
            try:
                project_dir = os.path.join(project.folder_path, project.name)
                os.makedirs(project_dir, exist_ok=True)

                json_file_path = os.path.join(project_dir, 'details.json')
                with open(json_file_path, 'w') as f:
                    json.dump(data, f, indent=4)

                yield json.dumps({
                    "type": "success", 
                    "message": f"Exported to {json_file_path}",
                    "missing_files": missing_files
                }) + "\n"
            except Exception as e:
                yield json.dumps({"type": "error", "error": str(e)}) + "\n"

        return StreamingHttpResponse(stream_progress(), content_type='application/x-ndjson')

    return JsonResponse({'status': 'error', 'error': 'Method not allowed'}, status=405)

@csrf_exempt
@login_required
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


@csrf_exempt
@login_required
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