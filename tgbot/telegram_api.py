"""Минимальный синхронный клиент Telegram Bot API (stdlib, без сторонних зависимостей)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger('tgbot')

API_BASE = 'https://api.telegram.org'
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024  # лимит Bot API на скачивание файла


class TelegramAPIError(Exception):
    pass


class TelegramClient:
    def __init__(self, token: str, timeout: int = 40):
        if not token:
            raise ValueError('Не задан TELEGRAM_BOT_TOKEN')
        self._token = token
        self._timeout = timeout

    def call(self, method: str, payload: dict | None = None, timeout: int | None = None):
        url = f'{API_BASE}/bot{self._token}/{method}'
        data = json.dumps(payload or {}, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=timeout or self._timeout) as resp:
                body = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode('utf-8'))
            except Exception:
                raise TelegramAPIError(f'{method}: HTTP {e.code}') from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TelegramAPIError(f'{method}: {e}') from None
        if not body.get('ok'):
            raise TelegramAPIError(f"{method}: {body.get('description', 'unknown error')}")
        return body.get('result')

    def get_updates(self, offset: int | None, timeout: int = 25):
        payload = {'timeout': timeout, 'allowed_updates': ['message', 'callback_query']}
        if offset is not None:
            payload['offset'] = offset
        return self.call('getUpdates', payload, timeout=timeout + 15)

    def delete_webhook(self):
        return self.call('deleteWebhook', {'drop_pending_updates': False})

    def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None):
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup
        return self.call('sendMessage', payload)

    def send_photo(self, chat_id: int, file_id: str, caption: str = '', reply_markup: dict | None = None):
        payload = {'chat_id': chat_id, 'photo': file_id, 'caption': caption, 'parse_mode': 'HTML'}
        if reply_markup:
            payload['reply_markup'] = reply_markup
        return self.call('sendPhoto', payload)

    def send_document(self, chat_id: int, file_id: str, caption: str = ''):
        return self.call(
            'sendDocument',
            {'chat_id': chat_id, 'document': file_id, 'caption': caption, 'parse_mode': 'HTML'},
        )

    def send_media_group(self, chat_id: int, media: list[dict]):
        return self.call('sendMediaGroup', {'chat_id': chat_id, 'media': media})

    def answer_callback_query(self, callback_query_id: str, text: str = ''):
        return self.call('answerCallbackQuery', {'callback_query_id': callback_query_id, 'text': text})

    def download_file(self, file_id: str) -> tuple[bytes, str]:
        """Скачивает файл по file_id. Возвращает (данные, file_path на стороне Telegram)."""
        info = self.call('getFile', {'file_id': file_id})
        file_path = info.get('file_path') or ''
        if not file_path:
            raise TelegramAPIError('getFile: пустой file_path')
        if info.get('file_size') and info['file_size'] > MAX_DOWNLOAD_BYTES:
            raise TelegramAPIError('Файл больше 20 МБ')
        url = f'{API_BASE}/file/bot{self._token}/{file_path}'
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                data = resp.read(MAX_DOWNLOAD_BYTES + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TelegramAPIError(f'download: {e}') from None
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise TelegramAPIError('Файл больше 20 МБ')
        return data, file_path
