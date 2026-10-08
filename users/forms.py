from django import forms
from django.contrib.auth import password_validation
from django.db.models import Q

from .models import User
from .phone_utils import normalize_congo_phone


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput,
        validators=[password_validation.validate_password],
        required=True,
    )
    password_confirm = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput,
        required=True,
    )

    class Meta:
        model = User
        fields = ['phone', 'email', 'locality', 'arrondissement', 'company_name', 'company_address', 'last_name', 'first_name', 'birth_date', 'civility', 'activity_sector']

    birth_date = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise forms.ValidationError('Cette adresse e-mail est déjà associée à un compte.')
        return email

    def clean_phone(self):
        phone = normalize_congo_phone(self.cleaned_data.get('phone'))
        if len(phone) < 12:
            raise forms.ValidationError('Le numéro doit contenir le préfixe 242 et 9 chiffres.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Les mots de passe ne correspondent pas.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'last_name', 'first_name', 'civility', 'birth_date',
            'company_name', 'activity_sector', 'email', 'company_address',
            'locality', 'arrondissement',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }
