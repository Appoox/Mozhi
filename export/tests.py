import os
import shutil
import tempfile
import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from transcription.models import Project, Transcript
from django.contrib.auth.models import User

# Create a temporary directory for media files during tests
TEST_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a user for transcription relationship
        self.user = User.objects.create_user(username='testuser', password='password')
        
        self.project = Project.objects.create(
            name="ExportProject",
            sample_rate=16000,
            folder_path=TEST_MEDIA_ROOT
        )
        self.transcript = Transcript.objects.create(
            project=self.project,
            audio_file="export_test.wav",
            transcript="Export this text.",
            user=self.user
        )

    def tearDown(self):
        if os.path.exists(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)
        if not os.path.exists(TEST_MEDIA_ROOT):
            os.makedirs(TEST_MEDIA_ROOT)

    def test_project_list_view(self):
        """Test export project list view."""
        response = self.client.get(reverse('export:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'export/project_list.html')
        self.assertContains(response, "ExportProject")

    def test_project_detail_view(self):
        """Test export project detail view."""
        response = self.client.get(reverse('export:project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'export/project_detail.html')
        self.assertContains(response, "ExportProject")
        self.assertContains(response, "Export this text.")

    def test_export_project_json_view(self):
        """Test NDJSON streaming export and details.json file creation."""
        # Create the audio file on disk — the export now aborts if it's missing.
        audio_dir = os.path.join(TEST_MEDIA_ROOT, self.project.name, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        with open(os.path.join(audio_dir, self.transcript.audio_file), 'wb') as f:
            f.write(b'RIFF')  # minimal stub

        response = self.client.post(reverse('export:export_project_json', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/x-ndjson')

        # Collect streamed content
        content = b"".join(response.streaming_content).decode()
        lines = content.strip().split('\n')
        
        # Verify JSON structure in stream
        self.assertTrue(any('"type": "init"' in line for line in lines))
        self.assertTrue(any('"type": "success"' in line for line in lines))

        # Verify details.json creation inside project folder
        project_dir = os.path.join(self.project.folder_path, self.project.name)
        details_json_path = os.path.join(project_dir, 'details.json')
        self.assertTrue(os.path.exists(details_json_path))

        with open(details_json_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['text'], "Export this text.")

    def test_delete_project_view(self):
        """Test deleting a project in export app."""
        response = self.client.post(reverse('export:delete_project', args=[self.project.id]), {
            'delete_files': 'false'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

    def test_delete_transcript_view(self):
        """Test deleting a transcript in export app."""
        response = self.client.post(reverse('export:delete_transcript', args=[self.transcript.id]), {
            'delete_files': 'false'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(Transcript.objects.filter(id=self.transcript.id).exists())

    # ── Audio validation tests ────────────────────────────────────────

    def test_project_detail_audio_exists_flag(self):
        """When the audio file exists, audio_exists is True on the context object."""
        # Create the actual file that serve_audio would look for
        audio_dir = os.path.join(TEST_MEDIA_ROOT, self.project.name, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        audio_path = os.path.join(audio_dir, self.transcript.audio_file)
        with open(audio_path, 'wb') as f:
            f.write(b'RIFF')  # minimal stub

        response = self.client.get(reverse('export:project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

        page_obj = response.context['page_obj']
        transcript_in_ctx = list(page_obj)[0]
        self.assertTrue(transcript_in_ctx.audio_exists)

    def test_project_detail_audio_missing_flag(self):
        """When the audio file is absent, audio_exists is False and badge appears in HTML."""
        # Do NOT create the audio file — it should be missing
        response = self.client.get(reverse('export:project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

        page_obj = response.context['page_obj']
        transcript_in_ctx = list(page_obj)[0]
        self.assertFalse(transcript_in_ctx.audio_exists)
        self.assertContains(response, 'Audio file missing')

    def test_export_json_without_audio_succeeds_and_lists_missing(self):
        """If an audio file is missing on disk, export yields success with a missing_files list."""
        response = self.client.post(reverse('export:export_project_json', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

        content = b''.join(response.streaming_content).decode()
        lines = [l for l in content.strip().split('\n') if l.strip()]

        success_lines = [l for l in lines if '"type": "success"' in l]
        self.assertTrue(len(success_lines) > 0, "Expected a success message in the stream")

        success_data = json.loads(success_lines[-1])
        self.assertIn(os.path.basename(self.transcript.audio_file), success_data.get('missing_files', []))

        project_dir = os.path.join(self.project.folder_path, self.project.name)
        details_json_path = os.path.join(project_dir, 'details.json')
        self.assertTrue(os.path.exists(details_json_path), "details.json should be written")

    def test_delete_project_with_files(self):
        target_dir = os.path.join(self.project.folder_path, self.project.name)
        os.makedirs(target_dir, exist_ok=True)
        response = self.client.post(reverse('export:delete_project', args=[self.project.id]), {
            'delete_files': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())
        self.assertFalse(os.path.exists(target_dir))

    def test_delete_transcript_with_files(self):
        target_dir = os.path.join(self.project.folder_path, self.project.name, 'audio')
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, os.path.basename(self.transcript.audio_file))
        with open(target_path, 'wb') as f:
            f.write(b'dummy')
        response = self.client.post(reverse('export:delete_transcript', args=[self.transcript.id]), {
            'delete_files': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(Transcript.objects.filter(id=self.transcript.id).exists())
        self.assertFalse(os.path.exists(target_path))

