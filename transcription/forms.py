from django import forms
from .models import Project

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'sample_rate']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ImportProjectForm(forms.Form):
    folder_name = forms.CharField(
        max_length=50,
        label="Folder Name (Project Name)",
    )
    # folder_path = forms.CharField(
    #     max_length=255,
    #     label="Base Folder Path",
    # )
    sample_rate = forms.TypedChoiceField(
        choices=[(str(k), v) for k, v in Project.SAMPLE_RATE_CHOICES],
        initial='44100',
        label="Sample Rate (Hz)",
        coerce=int,
    )