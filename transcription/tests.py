import os
import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from .models import Project, Transcript
from django.conf import settings

# Create a temporary directory for media files during tests
TEST_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class TranscriptionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.project = Project.objects.create(
            name="TestProject",
            sample_rate=16000,
            folder_path=TEST_MEDIA_ROOT
        )
        self.transcript = Transcript.objects.create(
            project=self.project,
            audio_file="test_audio.wav",
            transcript="This is a test transcription.",
            user=self.user
        )

    def tearDown(self):
        # Clean up temporary media directory after each test
        if os.path.exists(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)
        # Re-create the root for subsequent tests in the same class if needed
        # though usually TestCase handles isolation well. 
        # But since we use mkdtemp outside, let's be careful.
        if not os.path.exists(TEST_MEDIA_ROOT):
            os.makedirs(TEST_MEDIA_ROOT)

    def test_project_model_creation(self):
        """Test that project creation correctly sets attributes."""
        self.assertEqual(self.project.name, "TestProject")
        self.assertEqual(self.project.folder_path, TEST_MEDIA_ROOT)

    def test_transcript_model_relationship(self):
        """Test transcript relationship and string representation."""
        self.assertEqual(self.transcript.project, self.project)
        self.assertEqual(str(self.transcript), f"Transcript {self.transcript.id} for {self.project.name}")

    def test_project_list_view(self):
        """Test project list view returns 200 and uses correct template."""
        response = self.client.get(reverse('project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcription/project_list.html')
        self.assertContains(response, "TestProject")


    def test_project_detail_view(self):
        """Test project detail view."""
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transcription/project_detail.html')
        self.assertContains(response, "TestProject")
        self.assertContains(response, "This is a test transcription.")

    def test_delete_project_view(self):
        """Test deleting a project via AJAX POST."""
        response = self.client.post(reverse('delete_project', args=[self.project.id]), {
            'delete_files': 'false'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

    def test_delete_transcript_view(self):
        """Test deleting a transcript via AJAX POST."""
        response = self.client.post(reverse('delete_transcript', args=[self.transcript.id]), {
            'delete_files': 'false'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(Transcript.objects.filter(id=self.transcript.id).exists())

    def test_save_record_view(self):
        """Test saving a new recording via AJAX POST."""
        audio_content = b"fake audio content"
        audio_file = SimpleUploadedFile("recorded.wav", audio_content, content_type="audio/wav")
        
        response = self.client.post(reverse('save_record'), {
            'project_id': str(self.project.id),
            'transcript': 'Recorded transcript text',
            'audio': audio_file
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Verify Transcript entry created
        new_transcript = Transcript.objects.get(transcript='Recorded transcript text')
        self.assertEqual(new_transcript.project, self.project)
        
        # Verify file exists in project audio folder
        # Files are saved as <id>.wav in <project_path>/audio/
        # Wait, the current logic in views.py is:
        # target_dir = os.path.join(project.folder_path, project.name, 'audio')
        # filename = f"{transcript_instance.id}.wav"
        
        expected_audio_dir = os.path.join(self.project.folder_path, self.project.name, 'audio')
        expected_audio_path = os.path.join(expected_audio_dir, f"{new_transcript.id}.wav")
        self.assertTrue(os.path.exists(expected_audio_path))

    def test_serve_audio_view(self):
        """Test serving an audio file."""
        # First, ensure a file actually exists where serve_audio expects it
        audio_dir = os.path.join(self.project.folder_path, self.project.name, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        audio_path = os.path.join(audio_dir, f"{self.transcript.id}.wav")
        with open(audio_path, 'wb') as f:
            f.write(b"test audio data")
            
        # Update model to point to this filename (just the basename usually stored)
        self.transcript.audio_file = f"{self.transcript.id}.wav"
        self.transcript.save()

        response = self.client.get(reverse('serve_audio', args=[self.transcript.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'audio/wav')
        self.assertEqual(b"".join(response.streaming_content), b"test audio data")

    def test_wrong_url_redirects_to_project_list(self):
        """Test that a non-existent URL redirects to the project list."""
        response = self.client.get('/this-is-a-wrong-url/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('project_list'))

    from unittest.mock import patch

    @patch('transcription.views.SAVE_DIR', new=TEST_MEDIA_ROOT)
    @patch('transcription.views.settings.SAVE_DIR', new=TEST_MEDIA_ROOT)
    def test_create_project_view_post(self):
        response = self.client.post(reverse('create_project'), {
            'name': 'NewProject',
            'sample_rate': 16000
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(name='NewProject').exists())

    def test_edit_transcript_view(self):
        response = self.client.post(reverse('edit_transcript', args=[self.transcript.id]), {
            'text': 'Updated transcript text.'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.transcript.refresh_from_db()
        self.assertEqual(self.transcript.transcript, 'Updated transcript text.')

    def test_delete_project_with_files(self):
        target_dir = os.path.join(self.project.folder_path, self.project.name)
        os.makedirs(target_dir, exist_ok=True)
        response = self.client.post(reverse('delete_project', args=[self.project.id]), {
            'delete_files': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())
        self.assertFalse(os.path.exists(target_dir))

    def test_delete_transcript_with_files(self):
        target_dir = os.path.join(self.project.folder_path, self.project.name, 'audio')
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, self.transcript.audio_file)
        with open(target_path, 'wb') as f:
            f.write(b"dummy")
        response = self.client.post(reverse('delete_transcript', args=[self.transcript.id]), {
            'delete_files': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transcript.objects.filter(id=self.transcript.id).exists())
        self.assertFalse(os.path.exists(target_path))

    @patch('transcription.views.SAVE_DIR', new=TEST_MEDIA_ROOT)
    @patch('transcription.views.settings.SAVE_DIR', new=TEST_MEDIA_ROOT)
    def test_import_project_view(self):
        import json
        import_dir = os.path.join(TEST_MEDIA_ROOT, 'ImportTestProject')
        os.makedirs(os.path.join(import_dir, 'audio'), exist_ok=True)
        
        details_data = [
            {"audio_filepath": "audio/test1.wav", "text": "Test 1"},
            {"audio_filepath": "audio/test2.wav", "text": "Test 2"}
        ]
        with open(os.path.join(import_dir, 'details.json'), 'w') as f:
            json.dump(details_data, f)
            
        with open(os.path.join(import_dir, 'audio', 'test1.wav'), 'wb') as f:
            f.write(b"dummy")

        response = self.client.post(reverse('import_project'), {
            'folder_name': 'ImportTestProject',
            'sample_rate': 16000
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('audio/test2.wav', data['missing_files'])
        self.assertTrue(Project.objects.filter(name='ImportTestProject').exists())
