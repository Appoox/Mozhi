from django.apps import AppConfig
from django.db.models.signals import post_migrate
from Mozhi.settings import SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD
from django.core.management import call_command
import sys
import os

class TranscriptionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transcription'

    def ready(self):
        post_migrate.connect(create_default_superuser, sender=self)

        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') == 'true':
            try:
                print("Automating migrations...")
                call_command('migrate', interactive=False)
            except Exception as e:
                print(f"Migration failed during startup: {e}")

            

def create_default_superuser(sender, **kwargs):
    from django.contrib.auth.models import User
    try:
        if not User.objects.filter(username=SUPERUSER_USERNAME).exists():
            print(f"Creating default superuser: {SUPERUSER_USERNAME}")
            User.objects.create_superuser(SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        else:
            print(f"Superuser '{SUPERUSER_USERNAME}' already exists.")
    except Exception as e:
        print(f"Could not check/create superuser: {e}")