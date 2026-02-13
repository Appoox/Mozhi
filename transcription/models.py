import uuid
from django.db import models
from django.contrib.auth.models import User 

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    sample_rate = models.IntegerField(help_text="Sample rate in Hz (e.g., 44100)")
    created_at = models.DateTimeField(auto_now_add=True)

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