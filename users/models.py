from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured
import secrets
import base64
import hashlib


def generate_api_token():
    return secrets.token_hex(32)


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Arrondissement(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='arrondissements')
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['department', 'name'], name='unique_department_arrondissement'),
        ]

    def __str__(self):
        return f'{self.department.name} - {self.name}'


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('support', 'Support'),
        ('client', 'Client'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    company_address = models.CharField(max_length=255, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    civility = models.CharField(max_length=20, blank=True, null=True)
    activity_sector = models.CharField(max_length=120, blank=True, null=True)
    locality = models.CharField(max_length=120, blank=True, null=True)
    arrondissement = models.CharField(max_length=120, blank=True, null=True)
    low_balance_alerts = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_full_name() or self.username


class UserAPIToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='api_token', db_constraint=False)
    key = models.CharField(max_length=64, unique=True, default=generate_api_token)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'API token for user {self.user_id}'


class SMTPConfiguration(models.Model):
    SECURITY_CHOICES = [
        ('tls', 'STARTTLS'),
        ('ssl', 'SSL/TLS'),
        ('none', 'Aucun'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='smtp_configuration', db_constraint=False)
    provider = models.CharField(max_length=30, default='custom')
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=587)
    username = models.CharField(max_length=255)
    from_email = models.EmailField()
    security = models.CharField(max_length=10, choices=SECURITY_CHOICES, default='tls')
    encrypted_password = models.TextField(blank=True)
    signature = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def _cipher():
        from cryptography.fernet import Fernet

        if not settings.SMTP_ENCRYPTION_KEY:
            raise ImproperlyConfigured('Set SMTP_ENCRYPTION_KEY in the server environment before saving SMTP credentials.')
        key = hashlib.sha256(b'sms-platform:smtp-password:v1:' + settings.SMTP_ENCRYPTION_KEY.encode('utf-8')).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def set_password(self, value):
        self.encrypted_password = self._cipher().encrypt(value.encode('utf-8')).decode('ascii') if value else ''

    def get_password(self):
        if not self.encrypted_password:
            return ''
        try:
            return self._cipher().decrypt(self.encrypted_password.encode('ascii')).decode('utf-8')
        except Exception as error:
            raise ImproperlyConfigured('The SMTP password cannot be decrypted with the current SECRET_KEY.') from error

    @property
    def use_tls(self):
        return self.security == 'tls'

    @property
    def use_ssl(self):
        return self.security == 'ssl'


class OtpCode(models.Model):
    PURPOSE_CHOICES = [
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
    ]

    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='registration')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)

    def is_valid(self):
        return not self.verified and timezone.now() < self.expires_at
