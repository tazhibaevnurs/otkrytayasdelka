import re

from django import forms


class ContactForm(forms.Form):
    """Форма заявки на контакты (можно сохранять в модель при необходимости)."""
    name = forms.CharField(label='Имя', max_length=100, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 rounded-xl border border-champagne/40 bg-obsidian/50 text-ivory placeholder-ivory/40 focus:border-champagne/70 focus:outline-none transition',
        'placeholder': 'Как к вам обращаться',
        'autocomplete': 'name',
    }))
    phone = forms.CharField(label='Телефон', max_length=20, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 rounded-xl border border-champagne/40 bg-obsidian/50 text-ivory placeholder-ivory/40 focus:border-champagne/70 focus:outline-none transition',
        'type': 'tel',
        'placeholder': '+996 555 123 456',
        'autocomplete': 'tel',
    }))
    message = forms.CharField(
        label='Сообщение',
        required=False,
        max_length=5000,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-champagne/40 bg-obsidian/50 text-ivory placeholder-ivory/40 focus:border-champagne/70 focus:outline-none transition resize-none',
            'rows': 4,
            'placeholder': 'Опишите задачу или вопрос...',
        }),
    )

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError('Укажите имя.')
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise forms.ValidationError('Укажите номер телефона.')
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10:
            raise forms.ValidationError('Номер телефона слишком короткий.')
        return phone

    def clean_message(self):
        return (self.cleaned_data.get('message') or '').strip()

    def save(self):
        from .models import ContactRequest
        return ContactRequest.objects.create(
            name=self.cleaned_data['name'].strip(),
            phone=self.cleaned_data['phone'].strip(),
            message=(self.cleaned_data.get('message') or '').strip(),
        )
