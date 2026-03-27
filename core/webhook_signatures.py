"""
Проверка подписей входящих вебхуков (секреты только из переменных окружения, вызов с сервера).

Для Stripe рекомендуется: pip install stripe и stripe.Webhook.construct_event.
"""

import hashlib
import hmac
import os
import secrets
import time
from typing import Optional


def verify_stripe_signature(payload: bytes, header_signature: str, secret: str) -> bool:
    """
    Stripe-Signature. Секрет — signing secret вида whsec_... из кабинета Stripe.
    """
    if not header_signature or not secret:
        return False
    try:
        import stripe
    except ImportError:
        return False
    try:
        stripe.Webhook.construct_event(payload, header_signature, secret)
        return True
    except Exception:
        return False


def verify_yookassa_hmac_sha256(body: bytes, received_hex_digest: str, secret_key: str) -> bool:
    """
    Сравнение HMAC-SHA256(body, secret) с переданным дайджестом (нижний регистр hex).
    Уточните формат заголовка/тела по актуальной документации ЮKassa для вашего сценария.
    """
    if not received_hex_digest or not secret_key:
        return False
    try:
        digest = hmac.new(secret_key.encode('utf-8'), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, received_hex_digest.strip().lower())
    except Exception:
        return False


def verify_telegram_webhook_secret(request_meta, expected_token: Optional[str]) -> bool:
    """Заголовок X-Telegram-Bot-Api-Secret-Token (как задан в BotFather)."""
    if not expected_token:
        return False
    got = request_meta.get('HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN', '')
    try:
        return secrets.compare_digest(got, expected_token)
    except Exception:
        return False


def get_env_secret(name: str) -> str:
    return (os.environ.get(name) or '').strip()
