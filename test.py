import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Mozhi.settings')
django.setup()
from transcription.models import Project, Transcript
print("Projects:", Project.objects.count())
print("Transcripts:", Transcript.objects.count())
