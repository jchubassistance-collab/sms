from django.urls import reverse

from billing.models import Transaction
from campaigns.models import MailLog, SMSLog, SenderNameRequest


def account_notifications(request):
    """Build a compact notification menu from the signed-in user's saved records."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'account_notifications': [], 'account_notification_count': 0}

    notifications = []
    failed_sms = SMSLog.objects.filter(
        campaign__user=user,
        status='failed',
    ).select_related('campaign').order_by('-sent_at')[:3]
    notifications.extend({
        'title': 'Échec d’envoi SMS',
        'detail': log.campaign.title if log.campaign else log.recipient_phone,
        'url': reverse('sms-history'),
        'date': log.sent_at,
    } for log in failed_sms)

    failed_mail = MailLog.objects.filter(user=user, status='failed').order_by('-created_at')[:3]
    notifications.extend({
        'title': 'Échec d’envoi e-mail',
        'detail': log.subject or log.recipient,
        'url': reverse('mail-history'),
        'date': log.created_at,
    } for log in failed_mail)

    pending_payments = Transaction.objects.filter(user=user, status='pending').order_by('-created_at')[:2]
    notifications.extend({
        'title': 'Paiement en attente',
        'detail': f'{transaction.amount} FCFA · {transaction.payment_method}',
        'url': reverse('transaction-page'),
        'date': transaction.created_at,
    } for transaction in pending_payments)

    pending_sender_names = SenderNameRequest.objects.filter(user=user, status='pending').order_by('-created_at')[:2]
    notifications.extend({
        'title': 'Demande d’expéditeur en attente',
        'detail': request.sender_name,
        'url': reverse('sender-name'),
        'date': request.created_at,
    } for request in pending_sender_names)

    notifications.sort(key=lambda item: item['date'], reverse=True)
    notifications = notifications[:7]
    return {
        'account_notifications': notifications,
        'account_notification_count': len(notifications),
    }
