from rest_framework import serializers

from .models import Campaign, CampaignRecipient, SMSLog


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ['id', 'title', 'message', 'scheduled_at', 'status', 'created_at']
        read_only_fields = ['id', 'created_at', 'status']


class CampaignRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignRecipient
        fields = ['id', 'campaign', 'contact', 'status', 'sent_at']
        read_only_fields = ['id', 'sent_at']


class SMSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSLog
        fields = ['id', 'provider', 'status', 'response_code', 'sent_at']
        read_only_fields = ['id', 'sent_at']
