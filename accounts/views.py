from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from core.ratelimit_utils import check_registration_rate_limit, record_successful_registration

from .forms import RegistrationForm

User = get_user_model()


def register(request):
    if not settings.REGISTRATION_OPEN:
        raise Http404()
    if request.method == 'POST':
        blocked = check_registration_rate_limit(request)
        if blocked is not None:
            return blocked
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                is_active=False,
            )
            record_successful_registration(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            verify_path = reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
            link = request.build_absolute_uri(verify_path)
            send_mail(
                subject='Подтвердите email — Открытая Сделка',
                message=(
                    f'Здравствуйте.\n\n'
                    f'Для активации аккаунта перейдите по ссылке (действует 1 час):\n{link}\n\n'
                    f'Если вы не регистрировались, проигнорируйте письмо.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(
                request,
                'На указанный email отправлена ссылка для подтверждения.',
            )
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        messages.error(request, 'Неверная ссылка подтверждения.')
        return redirect('login')
    if user.is_active:
        messages.info(request, 'Аккаунт уже подтверждён. Войдите.')
        return redirect('login')
    if not default_token_generator.check_token(user, token):
        messages.error(request, 'Ссылка недействительна или истекла. Запросите новую регистрацию.')
        return redirect('login')
    user.is_active = True
    user.save(update_fields=['is_active'])
    messages.success(request, 'Email подтверждён. Теперь можно войти.')
    return redirect('login')


def profile(request):
    return render(request, 'accounts/profile.html', {})
