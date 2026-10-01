from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from billing.models import SMSPackage, Transaction
from campaigns.models import Campaign, SMSLog
from contacts.models import Contact
from .forms import RegistrationForm
from .models import User


class DashboardViewTests(TestCase):
	def test_dashboard_shows_data_for_authenticated_user(self):
		user = User.objects.create_user(username='dashboard-user', password='test-password')
		other_user = User.objects.create_user(username='other-user', password='test-password')
		self.client.force_login(user)

		Contact.objects.create(user=user, name='Dashboard Contact', phone='242060000001')
		Contact.objects.create(user=other_user, name='Other Contact', phone='242060000002')
		campaign = Campaign.objects.create(user=user, title='Database Campaign', message='Test message')
		Campaign.objects.create(user=other_user, title='Other Campaign', message='Other message')
		SMSLog.objects.create(campaign=campaign, status='sent')
		SMSLog.objects.create(campaign=campaign, status='pending')
		package = SMSPackage.objects.create(name='Test package', quantity=250, price='10.00')
		Transaction.objects.create(user=user, package=package, amount='10.00', status='paid')

		response = self.client.get(reverse('dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['contact_count'], 1)
		self.assertEqual(response.context['campaign_count'], 1)
		self.assertEqual(response.context['sms_balance'], 250)
		self.assertEqual(response.context['activity_count'], 2)
		self.assertEqual(response.context['sent_monthly_counts'][-1], 1)
		self.assertEqual(response.context['pending_monthly_counts'][-1], 1)
		self.assertContains(response, 'Database Campaign')
		self.assertContains(response, 'Test package')
		self.assertNotContains(response, 'Other Campaign')
		self.assertNotContains(response, 'Other Contact')

	def test_dashboard_requires_authentication(self):
		response = self.client.get(reverse('dashboard'))

		self.assertRedirects(response, f'{reverse("login")}?next={reverse("dashboard")}')


class LoginAjaxTests(TestCase):
	def setUp(self):
		self.login_url = reverse('login')
		self.client.get(self.login_url)

	def post_ajax(self, **data):
		return self.client.post(
			self.login_url,
			data,
			HTTP_X_REQUESTED_WITH='XMLHttpRequest',
		)

	def test_invalid_captcha_returns_json_and_rotates_captcha(self):
		response = self.post_ajax(phone='242060000001', password='wrong', captcha='WRONG')

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.json()['error'], 'Le code de vérification est incorrect.')
		self.assertEqual(response.json()['captcha'], self.client.session['login_captcha'])

	def test_invalid_password_returns_json_without_page_html(self):
		user = User.objects.create_user(
			username='login-user',
			phone='242060000001',
			password='correct-password',
		)
		captcha = self.client.session['login_captcha']

		response = self.post_ajax(
			phone=user.phone,
			password='wrong-password',
			captcha=captcha,
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.json()['error'], 'Identifiants incorrects.')
		self.assertEqual(response['Content-Type'], 'application/json')

	def test_captcha_refresh_returns_json(self):
		response = self.client.get(
			f'{self.login_url}?refresh_captcha=1',
			HTTP_X_REQUESTED_WITH='XMLHttpRequest',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['captcha'], self.client.session['login_captcha'])

	@patch('users.views.send_sms')
	def test_successful_login_returns_otp_redirect_as_json(self, send_sms):
		user = User.objects.create_user(
			username='login-user',
			phone='242060000001',
			password='correct-password',
		)
		captcha = self.client.session['login_captcha']

		response = self.post_ajax(
			phone=user.phone,
			password='correct-password',
			captcha=captcha,
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['ok'])
		self.assertEqual(response.json()['redirect_url'], reverse('login-otp'))
		self.assertEqual(self.client.session['pending_login_user_id'], user.pk)
		send_sms.assert_called_once()


class RegistrationTests(TestCase):
	def test_email_matching_existing_username_is_rejected(self):
		User.objects.create_user(
			username='existing@example.com',
			email='another-address@example.com',
			phone='242060000001',
			password='test-password',
		)

		form = RegistrationForm(data={
			'email': 'EXISTING@example.com',
			'phone': '242060000002',
			'birth_date': '2000-01-01',
		})

		self.assertFalse(form.is_valid())
		self.assertIn('déjà associée', str(form.errors['email']))

	def test_registration_logs_user_in_and_redirects_to_dashboard(self):
		phone = '242060000003'
		session = self.client.session
		session['otp_verified_phone'] = phone
		session.save()

		response = self.client.post(reverse('register'), {
			'phone': phone,
			'email': 'new-user@example.com',
			'first_name': 'New',
			'last_name': 'User',
			'birth_date': '2000-01-01',
		})

		self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)
		self.assertTrue('_auth_user_id' in self.client.session)
