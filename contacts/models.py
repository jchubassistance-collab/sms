from django.db import models

from users.models import User


class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ContactGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_groups')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ContactGroupMember(models.Model):
    group = models.ForeignKey(ContactGroup, on_delete=models.CASCADE, related_name='members')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='group_memberships')

    class Meta:
        unique_together = ('group', 'contact')

    def __str__(self):
        return f'{self.group.name} - {self.contact.name}'
