from time import monotonic

import requests
from django.conf import settings

from .payment_errors import PaymentAPIError

_cached_access_token = None
_access_token_expires_at = 0


def airtel_is_configured():
    return bool(settings.AIRTEL_CLIENT_ID and settings.AIRTEL_CLIENT_SECRET)


def _access_token():
    global _cached_access_token, _access_token_expires_at
    if _cached_access_token and monotonic() < _access_token_expires_at:
        return _cached_access_token

    try:
        response = requests.post(
            f'{settings.AIRTEL_API_BASE_URL}/auth/oauth2/token',
            json={
                'client_id': settings.AIRTEL_CLIENT_ID,
                'client_secret': settings.AIRTEL_CLIENT_SECRET,
                'grant_type': 'client_credentials',
            },
            headers={'Content-Type': 'application/json'},
            timeout=settings.AIRTEL_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        token_data = response.json()
        _cached_access_token = token_data['access_token']
        _access_token_expires_at = monotonic() + max(int(token_data.get('expires_in', 3600)) - 30, 0)
        return _cached_access_token
    except (requests.RequestException, KeyError, ValueError) as error:
        raise PaymentAPIError('Airtel Money authentication failed.') from error


def _headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'X-Country': settings.AIRTEL_COUNTRY_CODE,
        'X-Currency': settings.AIRTEL_CURRENCY,
        'Content-Type': 'application/json',
        'Accept': '*/*',
    }


def create_payment_request(transaction, phone):
    token = _access_token()
    payload = {
        'reference': f'SMS package transaction {transaction.pk}',
        'subscriber': {
            'country': settings.AIRTEL_COUNTRY_CODE,
            'currency': settings.AIRTEL_CURRENCY,
            'msisdn': phone[3:],
        },
        'transaction': {
            'amount': str(transaction.amount),
            'country': settings.AIRTEL_COUNTRY_CODE,
            'currency': settings.AIRTEL_CURRENCY,
            'id': transaction.provider_reference,
        },
    }
    try:
        response = requests.post(
            f'{settings.AIRTEL_API_BASE_URL}/merchant/v1/payments/',
            headers=_headers(token),
            json=payload,
            timeout=settings.AIRTEL_REQUEST_TIMEOUT,
        )
    except requests.RequestException as error:
        raise PaymentAPIError(
            'La réponse d’Airtel est incertaine. Vérifiez le statut avant de réessayer.',
            uncertain=True,
        ) from error

    if response.status_code not in (200, 202):
        raise PaymentAPIError(
            'Airtel Money a refusé la demande de paiement.',
            uncertain=response.status_code >= 500,
        )


def get_payment_status(provider_reference):
    token = _access_token()
    try:
        response = requests.get(
            f'{settings.AIRTEL_API_BASE_URL}/standard/v1/payments/{provider_reference}',
            headers=_headers(token),
            timeout=settings.AIRTEL_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise PaymentAPIError('Impossible de vérifier le statut auprès d’Airtel Money.') from error

    status = data.get('data', {}).get('transaction', {}).get('status', '')
    return status.upper()