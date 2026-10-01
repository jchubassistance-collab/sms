import re


COUNTRY_CODE = '242'


def normalize_congo_phone(phone):
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith(COUNTRY_CODE):
        return digits
    return f'{COUNTRY_CODE}{digits}' if digits else ''
