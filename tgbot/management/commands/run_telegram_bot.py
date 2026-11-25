"""Запуск Telegram-бота (long polling): python manage.py run_telegram_bot"""

import logging
import signal
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from tgbot.handlers import Bot
from tgbot.telegram_api import TelegramAPIError, TelegramClient

logger = logging.getLogger('tgbot')


class Command(BaseCommand):
    help = 'Запускает Telegram-бота для загрузки объектов на сайт (long polling).'

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise CommandError('Задайте переменную окружения TELEGRAM_BOT_TOKEN.')

        client = TelegramClient(token)
        bot = Bot(client)
        self._stop = False

        def _request_stop(signum, frame):
            self._stop = True

        signal.signal(signal.SIGTERM, _request_stop)
        signal.signal(signal.SIGINT, _request_stop)

        try:
            client.delete_webhook()
        except TelegramAPIError as e:
            logger.warning('tgbot: deleteWebhook: %s', e)

        logger.info('tgbot: бот запущен')
        offset = None
        backoff = 1
        while not self._stop:
            try:
                updates = client.get_updates(offset)
                backoff = 1
            except TelegramAPIError as e:
                logger.warning('tgbot: getUpdates: %s (повтор через %s с)', e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            for update in updates or []:
                offset = update['update_id'] + 1
                close_old_connections()
                bot.handle_update(update)

        # Подтверждаем обработанные update, чтобы после рестарта они не пришли повторно.
        if offset is not None:
            try:
                client.get_updates(offset, timeout=0)
            except TelegramAPIError:
                pass
        logger.info('tgbot: бот остановлен')
