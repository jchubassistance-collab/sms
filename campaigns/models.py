from django.db import models
from django.conf import settings

from contacts.models import Contact
from users.models import User


class Campaign(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=255)
    message = models.TextField()
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class CampaignRecipient(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='recipients')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='campaigns')
    status = models.CharField(max_length=20, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.campaign.title} -> {self.contact.name}'


class SMSLog(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='sms_logs', null=True, blank=True)
    recipient = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='sms_logs', null=True, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    provider = models.CharField(max_length=50, default='twilio')
    status = models.CharField(max_length=20, default='pending')
    response_code = models.CharField(max_length=50, blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_received_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.provider} - {self.status}'


class MailLog(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Envoyé'),
        ('failed', 'Échec'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mail_logs', db_constraint=False)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.subject} -> {self.recipient} ({self.status})'


class SenderNameRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sender_name_requests', db_constraint=False)
    sender_name = models.CharField(max_length=11)
    reason = models.TextField()
    document = models.FileField(upload_to='sender-name-documents/', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sender_name} ({self.status})'
