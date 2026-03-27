from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


_field = 'w-full px-4 py-3 rounded-xl border border-champagne/40 bg-obsidian/50 text-ivory placeholder-ivory/40 focus:border-champagne/70 focus:outline-none'


class StyledPasswordResetForm(DjangoPasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.setdefault('class', _field)
        self.fields['email'].widget.attrs.setdefault('autocomplete', 'email')


class RegistrationForm(forms.Form):
    captcha = CaptchaField(label='Проверка', help_text='Введите символы с картинки')
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': _field, 'autocomplete': 'email'}),
    )
    password1 = forms.CharField(
        label='Пароль',
        max_length=128,
        widget=forms.PasswordInput(attrs={'class': _field, 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Пароль ещё раз',
        max_length=128,
        widget=forms.PasswordInput(attrs={'class': _field, 'autocomplete': 'new-password'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже зарегистрирован.')
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Пароли не совпадают.')
        if p1:
            validate_password(p1)
        return cleaned
