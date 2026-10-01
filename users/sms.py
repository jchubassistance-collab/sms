import json
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone


class SmsDeliveryError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def send_sms(phone, message, scheduled_at=None):
    token = settings.SMS_API_TOKEN.strip()
    scheme = getattr(settings, 'SMS_AUTH_SCHEME', 'Token')
    sender = settings.SMS_SENDER.strip()
    if not sender:
        raise SmsDeliveryError('SMS_SENDER doit contenir un expéditeur enregistré sur Tinda.', 500)
    if not token.lower().startswith(f'{scheme.lower()} '):
        token = f'{scheme} {token}'

    payload = {
        'msg': message,
        'sender': sender,
        'receivers': phone,
    }
    if scheduled_at:
        payload['date_envois'] = timezone.localtime(
            scheduled_at,
            ZoneInfo('Africa/Brazzaville'),
        ).strftime('%Y-%m-%dT%H:%M:%S')

    request = Request(
        settings.SMS_API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Accept': 'application/json',
            'Authorization': token,
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode('utf-8', errors='replace')
            if not 200 <= response.status < 300:
                raise SmsDeliveryError(f'SMS provider returned HTTP {response.status}: {body[:240]}', response.status)
            try:
                result = json.loads(body)
            except json.JSONDecodeError:
                result = {}
            provider_status = str(result.get('status') or result.get('statut') or response.status)
            if provider_status not in {'200', '201'}:
                detail = result.get('detail') or result.get('resultat') or body[:240]
                raise SmsDeliveryError(f'SMS provider rejected the message ({provider_status}): {detail}', 502)
            return result
    except HTTPError as error:
        body = error.read().decode('utf-8', errors='replace')[:240]
        status_code = error.code if 400 <= error.code < 500 else 502
        raise SmsDeliveryError(f'SMS provider returned HTTP {error.code}: {body}', status_code) from error
    except URLError as error:
        raise SmsDeliveryError('SMS provider is unreachable.') from error
