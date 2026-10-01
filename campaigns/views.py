import re
from zoneinfo import ZoneInfo
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils.html import escape, strip_tags
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from contacts.models import Contact, ContactGroup
from users.phone_utils import normalize_congo_phone
from users.sms import SmsDeliveryError, send_sms
from users.models import SMTPConfiguration
from .models import Campaign, CampaignRecipient, MailLog, SenderNameRequest, SMSLog
from .serializers import CampaignSerializer


def _campaign_form_context(user):
    return {
        'contact_groups': ContactGroup.objects.filter(user=user).order_by('name'),
        'sender_name': settings.SMS_SENDER,
        'recent_logs': SMSLog.objects.filter(campaign__user=user).select_related('campaign').order_by('-sent_at')[:10],
    }


def _process_sms_form(request, mode):
    message = request.POST.get('message', '').strip()
    if not message:
        messages.error(request, 'Saisissez le texte du SMS.')
        return
    if len(message) > 160:
        messages.error(request, 'Le SMS ne peut pas dépasser 160 caractères.')
        return

    recipient_contacts = []
    if mode in ('bulk', 'scheduled'):
        contact_group_id = request.POST.get('contact_group', 'all')
        recipient_query = Contact.objects.filter(user=request.user).exclude(phone='')
        if contact_group_id != 'all':
            recipient_query = recipient_query.filter(
                group_memberships__group_id=contact_group_id,
                group_memberships__group__user=request.user,
            )
        recipient_contacts = list(recipient_query.distinct().order_by('pk'))
        if not recipient_contacts:
            messages.error(request, 'Aucun contact avec un numéro valide dans cette sélection.')
            return
        phones = [normalize_congo_phone(contact.phone) for contact in recipient_contacts]
    else:
        raw_phones = request.POST.get('phone_numbers', '').strip()
        phones = list(dict.fromkeys(
            normalize_congo_phone(phone)
            for phone in re.split(r'[,;\s]+', raw_phones)
            if phone
        ))
        if not phones or any(len(phone) != 12 for phone in phones):
            messages.error(request, 'Saisissez un ou plusieurs numéros valides au format 242XXXXXXXXX.')
            return
        if len(phones) > 10:
            messages.error(request, 'Un envoi simple est limité à 10 numéros.')
            return

    scheduled_at = None
    if mode == 'scheduled' or request.POST.get('send_at'):
        scheduled_at = parse_datetime(request.POST.get('send_at', ''))
        if not scheduled_at:
            messages.error(request, 'Choisissez une date et une heure de planification valides.')
            return
        if timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at, ZoneInfo('Africa/Brazzaville'))
        if scheduled_at <= timezone.now():
            messages.error(request, 'La date de planification doit être dans le futur.')
            return

    title = request.POST.get('title', '').strip() or f'SMS {timezone.localtime().strftime("%Y-%m-%d %H:%M")}'
    campaign = Campaign.objects.create(
        user=request.user,
        title=title,
        message=message,
        scheduled_at=scheduled_at,
        status='scheduled' if scheduled_at else 'draft',
    )
    if recipient_contacts:
        CampaignRecipient.objects.bulk_create([
            CampaignRecipient(campaign=campaign, contact=contact)
            for contact in recipient_contacts
        ])
    log_recipients = (
        [(contact, normalize_congo_phone(contact.phone)) for contact in recipient_contacts]
        if recipient_contacts else [(None, phone) for phone in phones]
    )
    SMSLog.objects.bulk_create([
        SMSLog(
            campaign=campaign,
            recipient=contact,
            recipient_phone=phone,
            provider='tinda',
            status='pending',
        )
        for contact, phone in log_recipients
    ])

    try:
        if scheduled_at:
            send_sms(','.join(phones), message, scheduled_at=scheduled_at)
        else:
            send_sms(','.join(phones), message)
    except SmsDeliveryError as error:
        campaign.status = 'failed'
        campaign.save(update_fields=['status'])
        campaign.sms_logs.update(status='failed', response_code=str(error.status_code))
        campaign.recipients.update(status='failed')
        messages.error(request, f'L’envoi a échoué : {error}')
        return

    if scheduled_at:
        messages.success(request, f'La campagne a été planifiée auprès de Tinda pour le {timezone.localtime(scheduled_at):%d/%m/%Y à %H:%M}.')
        return

    campaign.status = 'sent'
    campaign.save(update_fields=['status'])
    campaign.sms_logs.update(status='sent', response_code='200')
    campaign.recipients.update(status='sent', sent_at=timezone.now())
    messages.success(request, f'SMS envoyé à {len(phones)} destinataire(s).')


class CampaignListView(generics.ListCreateAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Campaign.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@login_required(login_url='login')
def sender_name_view(request):
    if request.method == 'POST':
        sender_name = request.POST.get('sender_name', '').strip()
        reason = request.POST.get('reason', '').strip()
        document = request.FILES.get('document')
        if not sender_name or len(sender_name) > 11 or not reason:
            messages.error(request, 'Saisissez un Sender Name de 1 à 11 caractères et son motif.')
        elif document and (
            Path(document.name).suffix.lower() not in {'.pdf', '.png', '.jpg', '.jpeg'}
            or document.size > 5 * 1024 * 1024
        ):
            messages.error(request, 'Le justificatif doit être un PDF ou une image de 5 Mo maximum.')
        else:
            SenderNameRequest.objects.create(
                user=request.user,
                sender_name=sender_name,
                reason=reason,
                document=document,
            )
            messages.success(request, 'La demande de Sender Name a été enregistrée pour validation.')
        return redirect('sender-name')
    requests = SenderNameRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'campaigns/sender_name.html', {'sender_requests': requests})


@login_required(login_url='login')
def simple_message_view(request):
    if request.method == 'POST':
        _process_sms_form(request, 'simple')
        return redirect('simple-message')
    return render(request, 'campaigns/simple_message.html', _campaign_form_context(request.user))


@login_required(login_url='login')
def bulk_sms_view(request):
    if request.method == 'POST':
        _process_sms_form(request, 'bulk')
        return redirect('bulk-sms')
    return render(request, 'campaigns/bulk_sms.html', _campaign_form_context(request.user))


@login_required(login_url='login')
def sms_history_view(request):
    logs = SMSLog.objects.filter(campaign__user=request.user).select_related('campaign', 'recipient').order_by('-sent_at')
    return render(request, 'campaigns/sms_history.html', {
        'sms_logs': logs,
        'sender_name': settings.SMS_SENDER,
    })


@login_required(login_url='login')
def bulk_mail_view(request):
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        group_id = request.POST.get('contact_group', 'all')
        contacts = Contact.objects.filter(user=request.user).exclude(email__isnull=True).exclude(email='')
        if group_id != 'all':
            contacts = contacts.filter(
                group_memberships__group_id=group_id,
                group_memberships__group__user=request.user,
            )
        email_addresses = list(contacts.values_list('email', flat=True).distinct())
        if not subject or not body:
            messages.error(request, 'Saisissez l’objet et le contenu du mail.')
        elif not email_addresses:
            messages.error(request, 'Aucun contact avec une adresse e-mail dans cette sélection.')
        else:
            smtp_configuration = SMTPConfiguration.objects.filter(user=request.user).first()
            smtp_connection = None
            if smtp_configuration:
                try:
                    smtp_connection = get_connection(
                        backend='django.core.mail.backends.smtp.EmailBackend',
                        host=smtp_configuration.host,
                        port=smtp_configuration.port,
                        username=smtp_configuration.username,
                        password=smtp_configuration.get_password(),
                        use_tls=smtp_configuration.use_tls,
                        use_ssl=smtp_configuration.use_ssl,
                        timeout=20,
                    )
                    if not smtp_connection.open():
                        raise OSError('The SMTP server did not open the connection.')
                except Exception:
                    for email_address in email_addresses:
                        MailLog.objects.create(
                            user=request.user,
                            recipient=email_address,
                            subject=subject,
                            body=body,
                            status='failed',
                            error='SMTP connection failed; check account settings and provider availability.',
                        )
                    messages.error(request, 'Connexion SMTP impossible. Vérifiez les paramètres dans votre profil.')
                    return redirect('bulk-mail')

            success_count = 0
            for email_address in email_addresses:
                plain_body = strip_tags(body)
                html_body = body
                if smtp_configuration and smtp_configuration.signature:
                    plain_body += '\n\n' + smtp_configuration.signature
                    html_body += '<br><br>' + escape(smtp_configuration.signature).replace('\n', '<br>')
                mail = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_body,
                    from_email=smtp_configuration.from_email if smtp_configuration else settings.DEFAULT_FROM_EMAIL,
                    to=[email_address],
                    connection=smtp_connection,
                )
                mail.attach_alternative(html_body, 'text/html')
                try:
                    mail.send(fail_silently=False)
                except Exception as error:
                    MailLog.objects.create(
                        user=request.user,
                        recipient=email_address,
                        subject=subject,
                        body=body,
                        status='failed',
                        error=str(error)[:2000],
                    )
                else:
                    success_count += 1
                    MailLog.objects.create(
                        user=request.user,
                        recipient=email_address,
                        subject=subject,
                        body=body,
                        status='sent',
                    )
            if smtp_connection:
                smtp_connection.close()
            if not smtp_configuration and settings.EMAIL_BACKEND.endswith('console.EmailBackend'):
                messages.success(request, f'{success_count} mail(s) transmis au backend console; ils ne sont pas livrés à des destinataires en développement.')
            else:
                messages.success(request, f'{success_count} mail(s) accepté(s) par le serveur e-mail.')
        return redirect('bulk-mail')

    smtp_configuration = SMTPConfiguration.objects.filter(user=request.user).first()
    return render(request, 'campaigns/bulk_mail.html', {
        **_campaign_form_context(request.user),
        'email_backend_is_console': not smtp_configuration and settings.EMAIL_BACKEND.endswith('console.EmailBackend'),
        'sender_email': smtp_configuration.from_email if smtp_configuration else settings.DEFAULT_FROM_EMAIL,
        'recent_mail_logs': MailLog.objects.filter(user=request.user).order_by('-created_at')[:10],
    })


@login_required(login_url='login')
def mail_history_view(request):
    return render(request, 'campaigns/mail_history.html', {
        'mail_logs': MailLog.objects.filter(user=request.user).order_by('-created_at'),
    })


def scheduled_message_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        _process_sms_form(request, 'scheduled')
        return redirect('scheduled-message')
    return render(request, 'campaigns/scheduled_message.html', _campaign_form_context(request.user))


def scheduled_history_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    campaigns = Campaign.objects.filter(user=request.user, scheduled_at__isnull=False).annotate(
        total_recipients=Count('recipients', distinct=True),
        sent_logs=Count('sms_logs', filter=Q(sms_logs__status='sent'), distinct=True),
        pending_logs=Count('sms_logs', filter=Q(sms_logs__status='pending'), distinct=True),
    ).order_by('-created_at')
    return render(request, 'campaigns/scheduled_history.html', {
        'campaigns': campaigns,
        'sender_name': settings.SMS_SENDER,
    })
