from rest_framework import serializers

from .models import Contact, ContactGroup, ContactGroupMember


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'name', 'phone', 'email', 'tags', 'created_at']
        read_only_fields = ['id', 'created_at']


class ContactGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactGroup
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ContactGroupMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactGroupMember
        fields = ['id', 'group', 'contact']
        read_only_fields = ['id']
