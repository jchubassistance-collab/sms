import requests
from time import monotonic
from django.conf import settings
from .payment_errors import PaymentAPIError

_cached_access_token = None
_access_token_expires_at = 0


def momo_is_configured():
    return all((
        settings.MOMO_COLLECTION_SUBSCRIPTION_KEY,
        settings.MOMO_API_USER,
        settings.MOMO_API_KEY,
    ))


def _headers():
    return {
        'Ocp-Apim-Subscription-Key': settings.MOMO_COLLECTION_SUBSCRIPTION_KEY,
        'X-Target-Environment': settings.MOMO_TARGET_ENVIRONMENT,
    }


def _access_token():
    global _cached_access_token, _access_token_expires_at
    if _cached_access_token and monotonic() < _access_token_expires_at:
        return _cached_access_token

    try:
        response = requests.post(
            f'{settings.MOMO_API_BASE_URL}/collection/token/',
            headers=_headers(),
            auth=(settings.MOMO_API_USER, settings.MOMO_API_KEY),
            timeout=settings.MOMO_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        token_data = response.json()
        _cached_access_token = token_data['access_token']
        _access_token_expires_at = monotonic() + max(int(token_data.get('expires_in', 3600)) - 30, 0)
        return _cached_access_token
    except (requests.RequestException, KeyError, ValueError) as error:
        raise PaymentAPIError('MTN MoMo authentication failed.') from error


def create_request_to_pay(transaction, phone):
    token = _access_token()
    headers = {
        **_headers(),
        'Authorization': f'Bearer {token}',
        'X-Reference-Id': transaction.provider_reference,
        'Content-Type': 'application/json',
    }
    payload = {
        'amount': str(transaction.amount),
        'currency': settings.MOMO_CURRENCY,
        'externalId': str(transaction.pk),
        'payer': {
            'partyIdType': 'MSISDN',
            'partyId': phone,
        },
        'payerMessage': f'Achat forfait SMS {transaction.package.name}',
        'payeeNote': f'Transaction #{transaction.pk}',
    }
    try:
        response = requests.post(
            f'{settings.MOMO_API_BASE_URL}/collection/v1_0/requesttopay',
            headers=headers,
            json=payload,
            timeout=settings.MOMO_REQUEST_TIMEOUT,
        )
    except requests.RequestException as error:
        raise PaymentAPIError(
            'La réponse de MTN est incertaine. Vérifiez le statut avant de réessayer.',
            uncertain=True,
        ) from error

    if response.status_code != 202:
        raise PaymentAPIError(
            'MTN MoMo a refusé la demande de paiement.',
            uncertain=response.status_code >= 500,
        )


def get_request_to_pay_status(provider_reference):
    token = _access_token()
    headers = {
        **_headers(),
        'Authorization': f'Bearer {token}',
    }
    try:
        response = requests.get(
            f'{settings.MOMO_API_BASE_URL}/collection/v1_0/requesttopay/{provider_reference}',
            headers=headers,
            timeout=settings.MOMO_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get('status', '').upper()
    except (requests.RequestException, ValueError) as error:
        raise PaymentAPIError('Impossible de vérifier le statut auprès de MTN MoMo.') from error