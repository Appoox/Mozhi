from django import forms
from .models import Transcript

class TranscriptUploadForm(forms.ModelForm):
    class Meta:
        model = Transcript
        # We only ask for the file and project. 
        # The 'user' will be filled in automatically by the view.
        fields = ['project', 'audio_file']