from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import User
from .models import SMSPackage, Transaction


@override_settings(
	MOMO_COLLECTION_SUBSCRIPTION_KEY='test-subscription-key',
	MOMO_API_USER='test-api-user',
	MOMO_API_KEY='test-api-key',
	AIRTEL_CLIENT_ID='test-airtel-client',
	AIRTEL_CLIENT_SECRET='test-airtel-secret',
)
class PurchasePackageTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='package-buyer',
			phone='061234567',
			password='test-password',
		)
		self.package = SMSPackage.objects.create(
			name='Test SMS',
			quantity=100,
			price='500.00',
		)
		self.url = reverse('purchase-package')
		self.client.force_login(self.user)
		self.purchase_data = {
			'package_id': self.package.pk,
			'payment_method': 'mtn',
			'phone': '242061234567',
		}

	@patch('billing.views.create_request_to_pay')
	def test_purchase_starts_mtn_request_and_stays_pending(self, create_request):
		response = self.client.post(self.url, self.purchase_data)

		self.assertEqual(response.status_code, 202)
		self.assertEqual(response.json()['status'], 'pending')
		self.assertEqual(response.json()['operator'], 'MTN Mobile Money')
		self.assertEqual(response.json()['phone'], '242061234567')
		self.assertEqual(Transaction.objects.count(), 1)
		transaction = Transaction.objects.get()
		self.assertEqual(transaction.status, 'pending')
		self.assertTrue(transaction.provider_reference)
		create_request.assert_called_once_with(transaction, '242061234567')

	def test_invalid_package_does_not_create_transaction(self):
		response = self.client.post(self.url, {**self.purchase_data, 'package_id': 'invalid'})

		self.assertEqual(response.status_code, 400)
		self.assertEqual(Transaction.objects.count(), 0)

	def test_unsupported_phone_does_not_create_transaction(self):
		self.user.phone = '079123456'
		self.user.save(update_fields=['phone'])

		response = self.client.post(self.url, {**self.purchase_data, 'phone': '242079123456'})

		self.assertEqual(response.status_code, 400)
		self.assertEqual(Transaction.objects.count(), 0)

	@patch('billing.views.create_payment_request')
	def test_airtel_phone_starts_airtel_request(self, create_request):
		response = self.client.post(self.url, {
			**self.purchase_data,
			'payment_method': 'airtel',
			'phone': '242051234567',
		})

		self.assertEqual(response.status_code, 202)
		self.assertEqual(response.json()['operator'], 'Airtel Money')
		transaction = Transaction.objects.get()
		self.assertEqual(transaction.payment_method, 'Airtel Money')
		create_request.assert_called_once_with(transaction, '242051234567')

	@patch('billing.views.get_request_to_pay_status', return_value='SUCCESSFUL')
	@patch('billing.views.create_request_to_pay')
	def test_successful_mtn_status_marks_transaction_paid(self, create_request, get_status):
		purchase = self.client.post(self.url, self.purchase_data)
		transaction_id = purchase.json()['transaction_id']

		response = self.client.get(reverse('purchase-status', args=[transaction_id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['status'], 'paid')
		self.assertEqual(Transaction.objects.get(pk=transaction_id).status, 'paid')
		get_status.assert_called_once()

	@patch('billing.views.get_payment_status', return_value='TS')
	@patch('billing.views.create_payment_request')
	def test_successful_airtel_status_marks_transaction_paid(self, create_request, get_status):
		purchase = self.client.post(self.url, {
			**self.purchase_data,
			'payment_method': 'airtel',
			'phone': '242051234567',
		})
		transaction_id = purchase.json()['transaction_id']

		response = self.client.get(reverse('purchase-status', args=[transaction_id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['status'], 'paid')
		self.assertEqual(Transaction.objects.get(pk=transaction_id).status, 'paid')
		get_status.assert_called_once()

	def test_purchase_requires_authentication(self):
		self.client.logout()

		response = self.client.post(self.url, self.purchase_data)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(Transaction.objects.count(), 0)
