from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from contacts.models import Contact
from users.models import User
from users.sms import SmsDeliveryError
from .models import Campaign, MailLog, SenderNameRequest, SMSLog


class SmsCampaignViewTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='campaign-owner', password='test-password')
		self.client.force_login(self.user)

	@patch('campaigns.views.send_sms')
	def test_simple_message_sends_and_records_logs(self, send_sms_mock):
		response = self.client.post(reverse('simple-message'), {
			'phone_numbers': '242061234567, 051234568',
			'message': 'Test message',
		})

		self.assertRedirects(response, reverse('simple-message'), fetch_redirect_response=False)
		campaign = Campaign.objects.get(user=self.user)
		self.assertEqual(campaign.status, 'sent')
		self.assertEqual(SMSLog.objects.filter(campaign=campaign, status='sent').count(), 2)
		self.assertQuerySetEqual(
			SMSLog.objects.filter(campaign=campaign).order_by('recipient_phone').values_list('recipient_phone', flat=True),
			['242051234568', '242061234567'],
			transform=lambda value: value,
		)
		send_sms_mock.assert_called_once_with('242061234567,242051234568', 'Test message')

	@patch('campaigns.views.send_sms', side_effect=SmsDeliveryError('provider unavailable', 502))
	def test_provider_failure_is_saved_as_failed(self, send_sms_mock):
		self.client.post(reverse('simple-message'), {
			'phone_numbers': '242061234567',
			'message': 'Test message',
		})

		campaign = Campaign.objects.get(user=self.user)
		self.assertEqual(campaign.status, 'failed')
		self.assertEqual(SMSLog.objects.get(campaign=campaign).status, 'failed')

	@patch('campaigns.views.send_sms')
	def test_scheduled_campaign_is_sent_to_provider_with_schedule(self, send_sms_mock):
		Contact.objects.create(user=self.user, name='Scheduled contact', phone='242061234567')
		send_at = (timezone.now() + timedelta(days=1)).replace(microsecond=0).isoformat()

		self.client.post(reverse('scheduled-message'), {
			'contact_group': 'all',
			'send_at': send_at,
			'message': 'Future message',
		})

		campaign = Campaign.objects.get(user=self.user)
		self.assertEqual(campaign.status, 'scheduled')
		self.assertEqual(SMSLog.objects.get(campaign=campaign).status, 'pending')
		send_sms_mock.assert_called_once()
		self.assertEqual(send_sms_mock.call_args.args[0], '242061234567')
		self.assertIsNotNone(send_sms_mock.call_args.kwargs['scheduled_at'])


class OtherCampaignPageTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='mail-owner', email='owner@example.com', password='test-password')
		self.client.force_login(self.user)

	@patch('campaigns.views.EmailMultiAlternatives.send', return_value=1)
	def test_bulk_mail_sends_and_logs_one_record_per_recipient(self, send_mock):
		Contact.objects.create(user=self.user, name='First', phone='', email='first@example.com')
		Contact.objects.create(user=self.user, name='Second', phone='', email='second@example.com')

		response = self.client.post(reverse('bulk-mail'), {
			'contact_group': 'all',
			'subject': 'Hello',
			'body': '<p>Message</p>',
		})

		self.assertRedirects(response, reverse('bulk-mail'), fetch_redirect_response=False)
		self.assertEqual(MailLog.objects.filter(user=self.user, status='sent').count(), 2)
		self.assertEqual(send_mock.call_count, 2)

	def test_sender_name_request_is_saved(self):
		response = self.client.post(reverse('sender-name'), {
			'sender_name': 'MYBRAND',
			'reason': 'Notifications for customers',
		})

		self.assertRedirects(response, reverse('sender-name'), fetch_redirect_response=False)
		self.assertTrue(SenderNameRequest.objects.filter(user=self.user, sender_name='MYBRAND', status='pending').exists())
