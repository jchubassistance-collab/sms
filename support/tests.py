from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from users.models import User
from .models import SupportTicket


class SupportPageTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='support-owner', password='test-password')
		self.client.force_login(self.user)

	def test_ticket_and_screenshot_are_saved(self):
		screenshot = SimpleUploadedFile('screen.png', b'png-data', content_type='image/png')

		response = self.client.post(reverse('support-page'), {
			'category': 'PROBLEME D\'ENVOI',
			'message': 'SMS failure report',
			'include_capture': 'on',
			'screenshot': screenshot,
		})

		self.assertRedirects(response, reverse('support-page'), fetch_redirect_response=False)
		ticket = SupportTicket.objects.get(user=self.user)
		self.assertEqual(ticket.subject, 'PROBLEME D\'ENVOI')
		self.assertTrue(ticket.screenshot.name.endswith('screen.png'))
