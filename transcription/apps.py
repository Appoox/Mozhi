from django.apps import AppConfig
from django.db.models.signals import post_migrate
from Mozhi.settings import SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD

class TranscriptionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transcription'

    def ready(self):
        post_migrate.connect(create_default_superuser, sender=self)

def create_default_superuser(sender, **kwargs):
    from django.contrib.auth.models import User
    if not User.objects.filter(username=SUPERUSER_USERNAME).exists():
        User.objects.create_superuser(SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)