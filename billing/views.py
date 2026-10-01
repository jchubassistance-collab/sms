from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Sum
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from uuid import uuid4

from .models import SMSPackage, Transaction
from .airtel import airtel_is_configured, create_payment_request, get_payment_status
from .momo import create_request_to_pay, get_request_to_pay_status, momo_is_configured
from .payment_errors import PaymentAPIError
from .serializers import SMSPackageSerializer, TransactionSerializer
from users.phone_utils import normalize_congo_phone


class PackageListView(generics.ListAPIView):
    queryset = SMSPackage.objects.filter(is_active=True)
    serializer_class = SMSPackageSerializer
    permission_classes = [IsAuthenticated]


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


def package_store_view(request):
    packages = SMSPackage.objects.filter(is_active=True).order_by('price')

    balance = 0
    if request.user.is_authenticated:
        balance = Transaction.objects.filter(
            user=request.user,
            status='paid',
            package__isnull=False,
        ).aggregate(total=Sum('package__quantity'))['total'] or 0
    payment_phone = normalize_congo_phone(request.user.phone) if request.user.is_authenticated else ''
    return render(request, 'billing/package_store.html', {
        'packages': packages,
        'balance': balance,
        'payment_phone': payment_phone,
    })


@login_required(login_url='login')
def purchase_package_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    try:
        package_id = int(request.POST.get('package_id', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Forfait invalide.'}, status=400)

    package = SMSPackage.objects.filter(
        pk=package_id,
        is_active=True,
    ).first()
    if package is None:
        return JsonResponse({'error': 'Forfait introuvable.'}, status=404)

    phone = normalize_congo_phone(request.POST.get('phone', ''))
    if len(phone) != 12:
        return JsonResponse({'error': 'Saisissez un numéro Mobile Money valide avec le préfixe pays 242.'}, status=400)

    local_phone = phone[3:]
    selected_method = request.POST.get('payment_method')
    if selected_method == 'mtn' and local_phone.startswith('06'):
        payment_method = 'MTN MoMo'
        operator = 'MTN Mobile Money'
        is_configured = momo_is_configured()
    elif selected_method == 'airtel' and local_phone.startswith(('04', '05')):
        payment_method = 'Airtel Money'
        operator = payment_method
        is_configured = airtel_is_configured()
    else:
        return JsonResponse({'error': 'Le numéro ne correspond pas au mode de paiement choisi.'}, status=400)

    transaction = Transaction.objects.create(
        user=request.user,
        package=package,
        amount=package.price,
        payment_method=payment_method,
        status='pending' if is_configured else 'failed',
        provider_reference=str(uuid4()) if is_configured else '',
    )
    if not is_configured:
        return JsonResponse({
            'error': f'Le paiement {operator} n’est pas configuré. Aucun paiement n’a été envoyé au fournisseur.',
            'transaction_id': transaction.pk,
            'status': transaction.status,
        }, status=503)

    try:
        if payment_method == 'MTN MoMo':
            create_request_to_pay(transaction, phone)
        else:
            create_payment_request(transaction, phone)
    except PaymentAPIError as error:
        if not error.uncertain:
            transaction.status = 'failed'
            transaction.save(update_fields=['status'])
        return JsonResponse({
            'error': str(error),
            'transaction_id': transaction.pk,
            'status': transaction.status,
            'status_url': reverse('purchase-status', args=[transaction.pk]),
        }, status=502)

    return JsonResponse({
        'transaction_id': transaction.pk,
        'operator': operator,
        'message': f'Demande envoyée à {operator}. Confirmez le paiement sur votre téléphone.',
        'phone': phone,
        'status': transaction.status,
        'status_url': reverse('purchase-status', args=[transaction.pk]),
    }, status=202)


@login_required(login_url='login')
def purchase_status_view(request, transaction_id):
    transaction = Transaction.objects.filter(
        pk=transaction_id,
        user=request.user,
    ).first()
    if transaction is None:
        return JsonResponse({'error': 'Transaction introuvable.'}, status=404)

    if transaction.status == 'pending':
        if transaction.payment_method == 'MTN MoMo':
            is_configured = momo_is_configured()
        elif transaction.payment_method == 'Airtel Money':
            is_configured = airtel_is_configured()
        else:
            is_configured = False
        if not transaction.provider_reference or not is_configured:
            return JsonResponse({'error': 'Statut de paiement indisponible.'}, status=503)
        try:
            if transaction.payment_method == 'MTN MoMo':
                provider_status = get_request_to_pay_status(transaction.provider_reference)
            else:
                provider_status = get_payment_status(transaction.provider_reference)
        except PaymentAPIError as error:
            return JsonResponse({'error': str(error), 'status': transaction.status}, status=502)

        if provider_status in ('SUCCESSFUL', 'SUCCESS', 'TS'):
            transaction.status = 'paid'
            transaction.save(update_fields=['status'])
        elif provider_status in ('FAILED', 'FAILURE', 'TF'):
            transaction.status = 'failed'
            transaction.save(update_fields=['status'])

    return JsonResponse({'status': transaction.status, 'operator': transaction.payment_method})


@login_required(login_url='login')
def transaction_page_view(request):
    transactions = Transaction.objects.filter(user=request.user).select_related('package').order_by('-created_at')
    summary = transactions.aggregate(
        total_collected=Sum('amount', filter=Q(status='paid')),
        transaction_count=Count('id'),
        successful_transactions=Count('id', filter=Q(status='paid')),
        failed_transactions=Count('id', filter=Q(status='failed')),
        pending_transactions=Count('id', filter=Q(status='pending')),
    )
    total_collected = summary['total_collected'] or 0
    completed_transactions = summary['successful_transactions'] + summary['failed_transactions']
    success_rate = (
        summary['successful_transactions'] * 100 / completed_transactions
        if completed_transactions else 0
    )
    return render(request, 'billing/transactions.html', {
        'transactions': transactions,
        'total_collected': total_collected,
        'transaction_count': summary['transaction_count'],
        'successful_transactions': summary['successful_transactions'],
        'failed_transactions': summary['failed_transactions'],
        'pending_transactions': summary['pending_transactions'],
        'success_rate': success_rate,
    })
