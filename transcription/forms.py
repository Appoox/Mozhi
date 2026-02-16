from django import forms
from .models import Transcript, Project

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'sample_rate']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class TranscriptUploadForm(forms.ModelForm):
    class Meta:
        model = Transcript
        # We only ask for the file and project. 
        # The 'user' will be filled in automatically by the view.
        fields = ['project', 'audio_file']