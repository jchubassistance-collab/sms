import csv
import io
import unicodedata

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import redirect, render

from .models import Contact
from .serializers import ContactSerializer
from users.phone_utils import normalize_congo_phone


def _header_token(value):
    normalized = unicodedata.normalize('NFKD', value.casefold().strip())
    return ''.join(character for character in normalized if not unicodedata.combining(character)).replace('_', '').replace(' ', '')


def _import_contacts_csv(uploaded_file, user, require_phone):
    if not uploaded_file.name.lower().endswith('.csv'):
        raise ValueError('Importez un fichier CSV (.csv).')

    try:
        content = uploaded_file.read().decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValueError('Le fichier doit être encodé en UTF-8.') from error

    sample = content[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=';,')
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ';'

    reader = csv.DictReader(io.StringIO(content), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError('Le fichier CSV doit contenir une ligne de titres.')

    columns = {_header_token(column): column for column in reader.fieldnames if column}
    name_column = next((columns[key] for key in ('name', 'nom', 'contact') if key in columns), None)
    phone_column = next((columns[key] for key in ('phone', 'telephone', 'numero', 'mobile') if key in columns), None)
    email_column = next((columns[key] for key in ('email', 'courriel', 'mail') if key in columns), None)
    if require_phone and (not name_column or not phone_column):
        raise ValueError('Le CSV doit contenir les colonnes nom et téléphone.')
    if not require_phone and not email_column:
        raise ValueError('Le CSV doit contenir une colonne e-mail.')

    existing_phones = set(
        Contact.objects.filter(user=user).exclude(phone='').values_list('phone', flat=True)
    )
    existing_emails = {
        email.casefold() for email in
        Contact.objects.filter(user=user).exclude(email__isnull=True).values_list('email', flat=True)
    }
    new_contacts = []
    skipped = 0

    for row in reader:
        raw_name = (row.get(name_column) or '').strip() if name_column else ''
        raw_phone = (row.get(phone_column) or '').strip() if phone_column else ''
        email = (row.get(email_column) or '').strip().lower() if email_column else ''
        phone = normalize_congo_phone(raw_phone) if raw_phone else ''

        if (require_phone and (not raw_name or len(phone) != 12)) or (not require_phone and not email):
            skipped += 1
            continue
        if email:
            try:
                validate_email(email)
            except ValidationError:
                skipped += 1
                continue
        if (phone and phone in existing_phones) or (email and email in existing_emails):
            skipped += 1
            continue

        contact_name = raw_name or email
        new_contacts.append(Contact(user=user, name=contact_name, phone=phone, email=email or None))
        if phone:
            existing_phones.add(phone)
        if email:
            existing_emails.add(email)

    if new_contacts:
        with transaction.atomic():
            Contact.objects.bulk_create(new_contacts)
    return len(new_contacts), skipped


def _handle_contact_post(request, require_phone, require_email=False):
    action = request.POST.get('action')
    if action == 'add':
        name = request.POST.get('name', '').strip()
        raw_phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = normalize_congo_phone(raw_phone) if raw_phone else ''

        if not name:
            messages.error(request, 'Saisissez le nom du contact.')
        elif require_phone and len(phone) != 12:
            messages.error(request, 'Saisissez un numéro valide avec le préfixe 242.')
        elif require_email and not email:
            messages.error(request, 'Saisissez une adresse e-mail pour ce contact.')
        else:
            try:
                if email:
                    validate_email(email)
            except ValidationError:
                messages.error(request, 'Saisissez une adresse e-mail valide.')
            else:
                duplicate = Contact.objects.filter(user=request.user).filter(
                    **({'phone': phone} if phone else {'email__iexact': email})
                ).exists()
                if duplicate:
                    messages.error(request, 'Ce contact existe déjà dans votre liste.')
                else:
                    Contact.objects.create(user=request.user, name=name, phone=phone, email=email or None)
                    messages.success(request, 'Le contact a été enregistré.')
    elif action == 'import':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, 'Choisissez un fichier CSV à importer.')
        else:
            try:
                added, skipped = _import_contacts_csv(uploaded_file, request.user, require_phone)
            except ValueError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, f'{added} contact(s) importé(s), {skipped} ignoré(s).')


class ContactListView(generics.ListCreateAPIView):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@login_required(login_url='login')
def contacts_page_view(request):
    if request.method == 'POST':
        _handle_contact_post(request, require_phone=True)
        return redirect('contacts-page')
    contacts = Contact.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'contacts/contact_page.html', {'contacts': contacts})


@login_required(login_url='login')
def contact_mail_page_view(request):
    if request.method == 'POST':
        _handle_contact_post(request, require_phone=False, require_email=True)
        return redirect('contact-mail-page')
    contacts = Contact.objects.filter(user=request.user, email__isnull=False).order_by('-created_at')
    return render(request, 'contacts/contact_mail_page.html', {'contacts': contacts})
