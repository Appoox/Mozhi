import uuid
from django.db import models
from django.contrib.auth.models import User 

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    SAMPLE_RATE_CHOICES = [
        (8000, '8000 Hz'),
        (16000, '16000 Hz'),
        (22050, '22050 Hz'),
        (44100, '44100 Hz'),
        (48000, '48000 Hz'),
    ]
    sample_rate = models.IntegerField(choices=SAMPLE_RATE_CHOICES, default=44100, help_text="Sample rate in Hz")
    created_at = models.DateTimeField(auto_now_add=True)
    folder_path = models.CharField(max_length=255, default='./', help_text="Select a folder to save audio files")

    def __str__(self):
        return self.name

class Transcript(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audio_file = models.FileField(upload_to='audio_uploads/')
    transcript = models.TextField(blank=True, null=True)
    
    # Relationships
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='transcripts')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcript {self.id} for {self.project.name}"