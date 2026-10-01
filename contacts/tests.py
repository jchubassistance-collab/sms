from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from users.models import User
from .models import Contact


class ContactPageTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='contact-owner', password='test-password')
		self.other_user = User.objects.create_user(username='other-owner', password='test-password')
		self.client.force_login(self.user)

	def test_manual_sms_contact_is_saved(self):
		response = self.client.post(reverse('contacts-page'), {
			'action': 'add',
			'name': 'Alice',
			'phone': '061234567',
			'email': 'alice@example.com',
		})

		self.assertRedirects(response, reverse('contacts-page'), fetch_redirect_response=False)
		self.assertTrue(Contact.objects.filter(user=self.user, name='Alice', phone='242061234567').exists())

	def test_mail_contact_can_be_saved_without_phone(self):
		response = self.client.post(reverse('contact-mail-page'), {
			'action': 'add',
			'name': 'Bob',
			'email': 'bob@example.com',
		})

		self.assertRedirects(response, reverse('contact-mail-page'), fetch_redirect_response=False)
		self.assertTrue(Contact.objects.filter(user=self.user, name='Bob', phone='', email='bob@example.com').exists())

	def test_csv_import_adds_contacts_and_skips_existing_phone(self):
		Contact.objects.create(user=self.user, name='Existing', phone='242061234567')
		csv_file = SimpleUploadedFile(
			'contacts.csv',
			b'name;phone;email\nExisting copy;061234567;copy@example.com\nNew contact;061234568;new@example.com\n',
			content_type='text/csv',
		)

		response = self.client.post(reverse('contacts-page'), {'action': 'import', 'file': csv_file})

		self.assertRedirects(response, reverse('contacts-page'), fetch_redirect_response=False)
		self.assertEqual(Contact.objects.filter(user=self.user).count(), 2)
		self.assertTrue(Contact.objects.filter(user=self.user, name='New contact').exists())

	def test_contact_list_is_scoped_to_current_user(self):
		Contact.objects.create(user=self.user, name='My contact', phone='242061234567')
		Contact.objects.create(user=self.other_user, name='Other contact', phone='242061234568')

		response = self.client.get(reverse('contacts-page'))

		self.assertContains(response, 'My contact')
		self.assertNotContains(response, 'Other contact')
