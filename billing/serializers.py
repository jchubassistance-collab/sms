from rest_framework import serializers

from .models import SMSPackage, Transaction


class SMSPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSPackage
        fields = ['id', 'name', 'quantity', 'price', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'payment_method', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']
