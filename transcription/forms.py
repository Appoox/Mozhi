from django import forms
from .models import Transcript, Project

class ProjectForm(forms.ModelForm):
    folder_path = forms.CharField(
        help_text="Select a folder to save audio files",
        widget=forms.TextInput(attrs={'list': 'folders-list', 'placeholder': 'Select or type a path...'})
    )

    class Meta:
        model = Project
        fields = ['name', 'sample_rate', 'folder_path']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.conf import settings
        import os
        
        # Get all directories in BASE_DIR for suggestions
        base_dir = settings.BASE_DIR
        self.folder_suggestions = []
        try:
            for item in os.listdir(base_dir):
                if os.path.isdir(os.path.join(base_dir, item)) and not item.startswith('.'):
                    self.folder_suggestions.append(item)
        except OSError:
            pass
            
        self.folder_suggestions.sort()

class TranscriptUploadForm(forms.ModelForm):
    class Meta:
        model = Transcript
        # We only ask for the file and project. 
        # The 'user' will be filled in automatically by the view.
        fields = ['project', 'audio_file']