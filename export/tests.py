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
