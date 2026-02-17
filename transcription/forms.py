from django import forms
from .models import Transcript, Project

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'sample_rate']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)