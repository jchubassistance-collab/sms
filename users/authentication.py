from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import UserAPIToken


class UserAPITokenAuthentication(BaseAuthentication):
    keyword = b'token'

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != self.keyword:
            return None
        if len(parts) != 2:
            raise AuthenticationFailed(_('Invalid token header.'))
        try:
            key = parts[1].decode('ascii')
        except UnicodeDecodeError as error:
            raise AuthenticationFailed(_('Invalid token.')) from error

        try:
            token = UserAPIToken.objects.select_related('user').get(key=key)
        except UserAPIToken.DoesNotExist as error:
            raise AuthenticationFailed(_('Invalid token.')) from error
        if not token.user.is_active:
            raise AuthenticationFailed(_('User inactive or deleted.'))
        return token.user, token

    def authenticate_header(self, request):
        return 'Token'
