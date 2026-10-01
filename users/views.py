from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import get_connection
from django.core.validators import validate_email
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db import IntegrityError, transaction
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import date, datetime, time, timedelta
import random
import secrets
from django.contrib.auth import password_validation
from django.core.exceptions import ImproperlyConfigured, ValidationError
from rest_framework import generics
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from billing.models import Transaction
from campaigns.models import Campaign, SMSLog
from contacts.models import Contact
from support.models import SupportTicket
from .models import Arrondissement, Department, OtpCode, SMTPConfiguration, User, UserAPIToken
from .serializers import UserSerializer
from .forms import ProfileForm, RegistrationForm
from .phone_utils import normalize_congo_phone
from .sms import SmsDeliveryError, send_sms


def create_captcha(request):
    captcha = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(5))
    request.session['login_captcha'] = captcha
    return captcha


def login_error_response(request, message):
    captcha = create_captcha(request)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': message, 'captcha': captcha}, status=400)
    return render(request, 'users/login.html', {'login_error': message, 'captcha': captcha})


def login_view(request):
    if request.method == 'GET' and request.GET.get('refresh_captcha') == '1':
        captcha = create_captcha(request)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'captcha': captcha})
    else:
        captcha = request.session.get('login_captcha') or create_captcha(request)
    if request.method == 'POST':
        phone = normalize_congo_phone(request.POST.get('phone', ''))
        password = request.POST.get('password', '')
        captcha_input = request.POST.get('captcha', '').strip().upper()
        if not secrets.compare_digest(captcha_input, captcha):
            return login_error_response(request, 'Le code de vérification est incorrect.')
        user_record = User.objects.filter(phone=phone).first()
        if user_record is None:
            return login_error_response(request, 'Aucun compte n’est associé à ce numéro de téléphone.')
        user = authenticate(request, username=user_record.username, password=password)
        if user is None:
            return login_error_response(request, 'Identifiants incorrects.')
        if not user.phone:
            return login_error_response(request, 'Aucun numéro de téléphone n’est associé à ce compte.')

        code = f'{random.randint(0, 999999):06d}'
        try:
            send_sms(user.phone, f'Votre code de connexion SMS PLATFORM est : {code}. Il expire dans 5 minutes.')
        except SmsDeliveryError as error:
            return login_error_response(request, str(error))

        OtpCode.objects.filter(phone=user.phone, purpose='login', verified=False).update(verified=True)
        otp = OtpCode.objects.create(
            phone=user.phone,
            code=code,
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        request.session['pending_login_user_id'] = user.pk
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'redirect_url': reverse('login-otp')})
        return redirect('login-otp')
    return render(request, 'users/login.html', {'captcha': captcha})


def login_otp_view(request):
    user_id = request.session.get('pending_login_user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.get(pk=user_id)
    resend_message = None
    if request.method == 'POST' and request.POST.get('action') == 'resend':
        code = f'{random.randint(0, 999999):06d}'
        try:
            send_sms(user.phone, f'Votre nouveau code de connexion SMS PLATFORM est : {code}. Il expire dans 5 minutes.')
        except SmsDeliveryError as error:
            return render(request, 'users/login_otp.html', {'error': str(error), 'phone': user.phone})
        OtpCode.objects.filter(phone=user.phone, purpose='login', verified=False).update(verified=True)
        OtpCode.objects.create(
            phone=user.phone,
            code=code,
            purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        resend_message = 'Un nouveau code a été envoyé par SMS.'

    if request.method == 'POST' and request.POST.get('action') != 'resend':
        code = request.POST.get('code', '').strip()
        otp = OtpCode.objects.filter(
            phone=user.phone,
            code=code,
            purpose='login',
            verified=False,
        ).order_by('-created_at').first()
        if otp and otp.is_valid():
            otp.verified = True
            otp.save(update_fields=['verified'])
            request.session.pop('pending_login_user_id', None)
            login(request, user)
            return redirect('dashboard')
        return render(request, 'users/login_otp.html', {'error': 'Le code est invalide ou a expiré.', 'phone': user.phone})

    return render(request, 'users/login_otp.html', {'phone': user.phone, 'resend_message': resend_message})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


def password_reset_view(request):
    phone = request.session.get('pending_password_reset_phone', '')
    generic_message = 'Si un compte correspond à ce numéro, un code de vérification a été envoyé.'

    if request.method == 'POST' and request.POST.get('action') == 'send_code':
        phone = normalize_congo_phone(request.POST.get('phone', ''))
        if len(phone) != 12:
            return render(request, 'users/password_reset.html', {'error': 'Saisissez un numéro valide avec le préfixe 242.'})

        request.session['pending_password_reset_phone'] = phone
        user = User.objects.filter(phone=phone, is_active=True).first()
        if user:
            code = f'{random.randint(0, 999999):06d}'
            try:
                send_sms(phone, f'Votre code de réinitialisation SMS PLATFORM est : {code}. Il expire dans 5 minutes.')
            except SmsDeliveryError:
                return render(request, 'users/password_reset.html', {
                    'phone': phone,
                    'error': 'Le code n’a pas pu être envoyé. Réessayez plus tard.',
                })
            OtpCode.objects.filter(phone=phone, purpose='password_reset', verified=False).update(verified=True)
            OtpCode.objects.create(
                phone=phone,
                code=code,
                purpose='password_reset',
                expires_at=timezone.now() + timedelta(minutes=5),
            )
        return render(request, 'users/password_reset.html', {
            'phone': phone,
            'notice': generic_message,
            'code_sent': True,
        })

    if request.method == 'POST' and request.POST.get('action') == 'reset_password':
        phone = request.session.get('pending_password_reset_phone', '')
        code = request.POST.get('code', '').strip()
        user = User.objects.filter(phone=phone, is_active=True).first()
        otp = OtpCode.objects.filter(
            phone=phone,
            code=code,
            purpose='password_reset',
            verified=False,
        ).order_by('-created_at').first()
        new_password = request.POST.get('new_password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not otp or not otp.is_valid() or not user:
            return render(request, 'users/password_reset.html', {
                'phone': phone,
                'code_sent': True,
                'error': 'Code invalide ou expiré. Demandez un nouveau code.',
            })
        if new_password != password_confirm:
            return render(request, 'users/password_reset.html', {
                'phone': phone,
                'code_sent': True,
                'error': 'Les mots de passe ne correspondent pas.',
            })
        try:
            password_validation.validate_password(new_password, user)
        except ValidationError as error:
            return render(request, 'users/password_reset.html', {
                'phone': phone,
                'code_sent': True,
                'error': ' '.join(error.messages),
            })

        user.set_password(new_password)
        user.save(update_fields=['password'])
        otp.verified = True
        otp.save(update_fields=['verified'])
        request.session.pop('pending_password_reset_phone', None)
        messages.success(request, 'Mot de passe modifié. Connectez-vous avec votre nouveau mot de passe.')
        return redirect('login')

    return render(request, 'users/password_reset.html', {'phone': phone})


@login_required(login_url='login')
def dashboard_view(request):
    contacts = Contact.objects.filter(user=request.user)
    campaigns = Campaign.objects.filter(user=request.user)
    transactions = Transaction.objects.filter(user=request.user)
    tickets = SupportTicket.objects.filter(user=request.user)

    recent_activity = [
        {
            'operation': campaign.title,
            'date': campaign.created_at,
            'category': 'Campagne SMS',
            'value': campaign.get_status_display(),
            'is_amount': False,
        }
        for campaign in campaigns.order_by('-created_at')[:10]
    ]
    recent_activity.extend(
        {
            'operation': transaction.package.name if transaction.package else 'Achat forfait',
            'date': transaction.created_at,
            'category': 'Forfait - ' + transaction.get_status_display(),
            'value': transaction.amount,
            'is_amount': True,
        }
        for transaction in transactions.select_related('package').order_by('-created_at')[:10]
    )
    recent_activity.sort(key=lambda activity: activity['date'], reverse=True)
    activity_count = campaigns.count() + transactions.count()
    sms_balance = transactions.filter(
        status='paid', package__isnull=False
    ).aggregate(total=Sum('package__quantity'))['total'] or 0
    current_month = timezone.localdate().replace(day=1)
    chart_months = []
    for months_ago in range(5, -1, -1):
        month_number = current_month.month - months_ago
        chart_months.append(date(
            current_month.year + (month_number - 1) // 12,
            (month_number - 1) % 12 + 1,
            1,
        ))
    chart_start = timezone.make_aware(datetime.combine(chart_months[0], time.min))
    monthly_sms_counts = SMSLog.objects.filter(
        campaign__in=campaigns,
        sent_at__gte=chart_start,
        status__in=['sent', 'pending'],
    ).annotate(month=TruncMonth('sent_at')).values('month', 'status').annotate(total=Count('id'))
    monthly_sms = {'sent': {}, 'pending': {}}
    for row in monthly_sms_counts:
        month = row['month']
        monthly_sms[row['status']][(month.year, month.month)] = row['total']
    month_names = ('Janv', 'Fev', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Aout', 'Sept', 'Oct', 'Nov', 'Dec')

    return render(request, 'users/dashboard.html', {
        'dashboard_user_name': request.user.first_name or request.user.phone or request.user.username,
        'contact_count': contacts.count(),
        'campaign_count': campaigns.count(),
        'sent_count': SMSLog.objects.filter(campaign__in=campaigns, status='sent').count(),
        'pending_count': SMSLog.objects.filter(campaign__in=campaigns, status='pending').count(),
        'sms_balance': sms_balance,
        'chart_labels': [f'{month_names[month.month - 1]} {month.year}' for month in chart_months],
        'sent_monthly_counts': [monthly_sms['sent'].get((month.year, month.month), 0) for month in chart_months],
        'pending_monthly_counts': [monthly_sms['pending'].get((month.year, month.month), 0) for month in chart_months],
        'recent_campaigns': campaigns.order_by('-created_at')[:5],
        'recent_activity': recent_activity[:10],
        'activity_count': activity_count,
        'upcoming_campaigns': campaigns.filter(status='scheduled').order_by('scheduled_at')[:3],
        'open_tickets': tickets.exclude(status='closed').order_by('-created_at')[:3],
    })


def _smtp_configuration_from_post(user, data, current):
    host = data.get('smtp_host', '').strip()
    username = data.get('smtp_username', '').strip()
    from_email = data.get('smtp_from_email', '').strip()
    provider = data.get('smtp_provider', 'custom')
    security = data.get('smtp_security', 'tls')
    try:
        port = int(data.get('smtp_port', '587'))
    except (TypeError, ValueError) as error:
        raise ValidationError('Saisissez un port SMTP valide.') from error
    if not host or any(char.isspace() for char in host):
        raise ValidationError('Saisissez un serveur SMTP valide.')
    if not 1 <= port <= 65535:
        raise ValidationError('Le port doit être compris entre 1 et 65535.')
    if not username:
        raise ValidationError('Saisissez le nom d’utilisateur SMTP.')
    try:
        validate_email(from_email)
    except ValidationError as error:
        raise ValidationError('Saisissez une adresse e-mail expéditeur valide.') from error
    if provider not in {'gmail', 'outlook', 'yahoo', 'custom'}:
        raise ValidationError('Choisissez un fournisseur SMTP valide.')
    if security not in {'tls', 'ssl', 'none'}:
        raise ValidationError('Choisissez un mode de sécurité valide.')

    password = data.get('smtp_password', '')
    if not password and current:
        password = current.get_password()
    if not password:
        raise ValidationError('Saisissez le mot de passe SMTP ou un mot de passe d’application.')

    configuration = current or SMTPConfiguration(user=user)
    configuration.provider = provider
    configuration.host = host
    configuration.port = port
    configuration.username = username
    configuration.from_email = from_email
    configuration.security = security
    configuration.signature = data.get('smtp_signature', '').strip()
    configuration.set_password(password)
    return configuration


@login_required(login_url='login')
def profile_view(request):
    form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    smtp_configuration = SMTPConfiguration.objects.filter(user=request.user).first()
    if request.method == 'POST':
        action = request.POST.get('profile_action', 'profile')
        if action == 'api_token_rotate':
            with transaction.atomic():
                UserAPIToken.objects.filter(user=request.user).delete()
                UserAPIToken.objects.create(user=request.user)
            messages.success(request, 'Votre jeton API a été renouvelé. Mettez à jour les applications qui l’utilisent.')
            return redirect(f"{reverse('profile')}#profile-api")
        if action in {'smtp_save', 'smtp_test'}:
            try:
                configuration = _smtp_configuration_from_post(request.user, request.POST, smtp_configuration)
                if action == 'smtp_test':
                    connection = get_connection(
                        backend='django.core.mail.backends.smtp.EmailBackend',
                        host=configuration.host,
                        port=configuration.port,
                        username=configuration.username,
                        password=configuration.get_password(),
                        use_tls=configuration.use_tls,
                        use_ssl=configuration.use_ssl,
                        timeout=12,
                    )
                    if not connection.open():
                        raise OSError('SMTP connection could not be opened.')
                    connection.close()
                    messages.success(request, 'Connexion SMTP vérifiée avec succès. La configuration n’a pas été enregistrée.')
                else:
                    configuration.save()
                    smtp_configuration = configuration
                    messages.success(request, 'Configuration SMTP enregistrée. Le mot de passe est chiffré avant stockage.')
                return redirect(f"{reverse('profile')}#profile-smtp")
            except Exception as error:
                if isinstance(error, ImproperlyConfigured):
                    detail = 'Le serveur doit définir SMTP_ENCRYPTION_KEY avant l’enregistrement des identifiants.'
                elif isinstance(error, ValidationError) and error.messages:
                    detail = error.messages[0]
                else:
                    detail = 'Vérifiez le serveur, le port, la sécurité et les identifiants fournis par votre fournisseur.'
                messages.error(request, f'Échec de la configuration SMTP : {detail}')
                return redirect(f"{reverse('profile')}#profile-smtp")
        if action == 'password_change':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Votre mot de passe a été modifié.')
                return redirect('profile')
        elif action == 'alert_settings':
            request.user.low_balance_alerts = request.POST.get('low_balance_alerts') == 'on'
            request.user.save(update_fields=['low_balance_alerts'])
            messages.success(request, 'Votre préférence d’alerte a été enregistrée.')
            return redirect('profile')
        else:
            form = ProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Votre profil a été mis à jour.')
                return redirect('profile')
    return render(request, 'users/profile.html', {
        'form': form,
        'password_form': password_form,
        'profile_user': request.user,
        'profile_preview': False,
        'low_balance_alerts': request.user.low_balance_alerts,
        'api_token': UserAPIToken.objects.get_or_create(user=request.user)[0],
        'smtp_configuration': smtp_configuration,
        'smtp_password_configured': bool(smtp_configuration and smtp_configuration.encrypted_password),
    })


def register_view(request):
    form = RegistrationForm(request.POST or None)
    departments = Department.objects.prefetch_related('arrondissements')
    departments_data = [
        {
            'name': department.name,
            'arrondissements': [arrondissement.name for arrondissement in department.arrondissements.all()],
        }
        for department in departments
    ]
    if request.method == 'POST' and form.is_valid():
        if request.session.get('otp_verified_phone') != form.cleaned_data.get('phone'):
            form.add_error('phone', 'Vérifiez d’abord votre numéro de téléphone avec le code reçu par SMS.')
            return render(request, 'users/register.html', {'form': form, 'departments': departments, 'departments_data': departments_data})
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error('email', 'Cette adresse e-mail est déjà associée à un compte.')
            return render(request, 'users/register.html', {'form': form, 'departments': departments, 'departments_data': departments_data})
        login(request, user)
        messages.success(request, 'Votre compte a été créé avec succès.')
        return redirect('dashboard')

    return render(request, 'users/register.html', {'form': form, 'departments': departments, 'departments_data': departments_data})


def send_otp_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)

    phone = normalize_congo_phone(request.POST.get('phone', ''))
    if len(phone) != 12:
        return JsonResponse({'error': 'Le numéro doit contenir 9 chiffres après le préfixe 242.'}, status=400)

    code = f'{random.randint(0, 999999):06d}'
    try:
        send_sms(phone, f'Votre code de verification SMS PLATFORM est : {code}. Il expire dans 5 minutes.')
    except SmsDeliveryError as error:
        return JsonResponse({'error': str(error)}, status=error.status_code)

    OtpCode.objects.filter(phone=phone, verified=False).update(verified=True)
    otp = OtpCode.objects.create(
        phone=phone,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    request.session['otp_phone'] = phone
    return JsonResponse({'message': 'Code de vérification envoyé par SMS.'})


def verify_otp_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)

    phone = normalize_congo_phone(request.POST.get('phone', ''))
    code = request.POST.get('code', '').strip()
    otp = OtpCode.objects.filter(phone=phone, code=code, verified=False).order_by('-created_at').first()
    if not otp or not otp.is_valid():
        return JsonResponse({'error': 'Le code est invalide ou a expiré.'}, status=400)

    otp.verified = True
    otp.save(update_fields=['verified'])
    request.session['otp_verified_phone'] = phone
    return JsonResponse({'message': 'Numéro de téléphone vérifié avec succés.'})


class UserListView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
