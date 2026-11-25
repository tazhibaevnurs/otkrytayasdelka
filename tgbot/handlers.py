"""Сценарии Telegram-бота: добавление, редактирование и удаление объектов каталога."""

from __future__ import annotations

import html
import logging

from django.utils import timezone

from listings.models import Listing, usd_to_kgs

from . import fields as f
from .models import BotSession, TelegramEmployee
from .publishing import (
    PublishError,
    delete_listing,
    listing_url,
    missing_draft_fields,
    publish_draft,
    update_listing_field,
)
from .telegram_api import TelegramAPIError

logger = logging.getLogger('tgbot')

MENU_ADD = 'Добавить объект'
MENU_MY = 'Мои загруженные объекты'
MENU_EDIT = 'Редактировать объект'
MENU_DELETE = 'Удалить объект'

MAIN_KEYBOARD = {
    'keyboard': [
        [{'text': MENU_ADD}],
        [{'text': MENU_MY}],
        [{'text': MENU_EDIT}, {'text': MENU_DELETE}],
    ],
    'resize_keyboard': True,
    'is_persistent': True,
}

LIST_PAGE_SIZE = 10

STATE_IDLE = 'idle'
STATE_PREVIEW = 'preview'
STATE_PHOTOS_ORDER = 'add_photos_order'
STATE_EDIT_INPUT = 'edit_input'
STATE_EDIT_CONFIRM = 'edit_confirm'
EDIT_STATES = {STATE_EDIT_INPUT, STATE_EDIT_CONFIRM}

# Порядок шагов добавления и признак «шаг пройден» по данным черновика.
ADD_STEPS = [
    ('add_cover', lambda d: bool(d.get('cover'))),
    ('add_photos', lambda d: bool(d.get('photos_done'))),
    ('add_title', lambda d: bool(d.get('title'))),
    ('add_district', lambda d: bool(d.get('district'))),
    ('add_street', lambda d: 'street' in d),
    ('add_rooms', lambda d: d.get('rooms') is not None),
    ('add_area', lambda d: bool(d.get('area'))),
    ('add_kind', lambda d: bool(d.get('kind'))),
    ('add_price', lambda d: bool(d.get('price_usd'))),
    ('add_realtor_name', lambda d: bool(d.get('realtor_name'))),
    ('add_realtor_phone', lambda d: bool(d.get('realtor_phone'))),
    ('add_description', lambda d: bool(d.get('description'))),
]
ADD_STATES = {name for name, _ in ADD_STEPS} | {STATE_PHOTOS_ORDER}
# При правке из предпросмотра эти шаги идут парой.
CHAINED_STEPS = {'add_district': 'add_street', 'add_realtor_name': 'add_realtor_phone'}

STEP_TITLES = {
    'add_cover': 'Шаг 1 из 8. Обложка',
    'add_photos': 'Шаг 2 из 8. Фотографии',
    'add_title': 'Шаг 3 из 8. Заголовок объекта',
    'add_district': 'Шаг 4 из 8. Расположение',
    'add_street': 'Шаг 4 из 8. Расположение',
    'add_rooms': 'Шаг 5 из 8. Основные характеристики',
    'add_area': 'Шаг 5 из 8. Основные характеристики',
    'add_kind': 'Шаг 5 из 8. Основные характеристики',
    'add_price': 'Шаг 6 из 8. Стоимость',
    'add_realtor_name': 'Шаг 7 из 8. Контакт риэлтора',
    'add_realtor_phone': 'Шаг 7 из 8. Контакт риэлтора',
    'add_description': 'Шаг 8 из 8. Описание объекта',
}

STEP_TEXTS = {
    'add_cover': 'Отправьте фасад объекта — одно фото.\nЭто фото будет отображаться первым в карточке объекта на сайте.',
    'add_photos': (
        'Отправьте остальные фотографии объекта. Можно отправить несколько фотографий подряд. '
        'Когда закончите, нажмите кнопку «Далее».'
    ),
    'add_title': 'Введите название объекта.\nПример: 2-комнатная квартира ПСО',
    'add_district': 'Укажите микрорайон или район.\nПример: мкр. Асанбай',
    'add_street': 'Укажите адрес (улица, дом), если необходимо. Если не нужно — нажмите «Пропустить».',
    'add_rooms': 'Количество комнат:',
    'add_area': 'Площадь квартиры (м²):\nПример: 67',
    'add_kind': 'Тип объекта:',
    'add_price': 'Укажите стоимость объекта в долларах.\nПример: 91 000',
    'add_realtor_name': 'Имя риэлтора:\nПример: Наргиза',
    'add_realtor_phone': 'Номер телефона риэлтора:\nПример: 0509 349 199',
    'add_description': (
        'Отправьте полное описание объекта одним сообщением.\n'
        'Абзацы и переносы строк сохранятся на сайте.'
    ),
}

DRAFT_EDIT_FIELDS = [
    ('cover', 'Обложка', 'add_cover'),
    ('photos', 'Фотографии', 'add_photos'),
    ('title', 'Название', 'add_title'),
    ('district', 'Район и адрес', 'add_district'),
    ('rooms', 'Комнаты', 'add_rooms'),
    ('area', 'Площадь', 'add_area'),
    ('kind', 'Тип', 'add_kind'),
    ('price', 'Стоимость', 'add_price'),
    ('realtor', 'Контакт риэлтора', 'add_realtor_name'),
    ('description', 'Описание', 'add_description'),
]
DRAFT_EDIT_STATE = {key: state for key, _, state in DRAFT_EDIT_FIELDS}

LISTING_EDIT_FIELDS = [
    ('price', 'Изменить цену'),
    ('description', 'Изменить описание'),
    ('cover', 'Изменить обложку'),
    ('realtor', 'Изменить контакт риэлтора'),
    ('area', 'Изменить площадь'),
    ('title', 'Изменить заголовок'),
]
LISTING_EDIT_KEYS = {key for key, _ in LISTING_EDIT_FIELDS}


def esc(value) -> str:
    return html.escape(str(value), quote=False)


def inline(rows) -> dict:
    return {
        'inline_keyboard': [
            [
                {'text': text, 'url': data[4:]} if data.startswith('url:') else {'text': text, 'callback_data': data}
                for text, data in row
            ]
            for row in rows
        ]
    }


def extract_photo(message: dict) -> dict | None:
    if message.get('photo'):
        return {'file_id': message['photo'][-1]['file_id'], 'kind': 'photo'}
    doc = message.get('document')
    if doc and (doc.get('mime_type') or '').startswith('image/'):
        return {'file_id': doc['file_id'], 'kind': 'document'}
    return None


def price_line(price_usd: int | None, price_text: str = '') -> str:
    if not price_usd:
        return esc(price_text) if price_text else '—'
    line = f.format_usd(price_usd)
    kgs = usd_to_kgs(price_usd)
    if kgs:
        line += f' (≈ {f.format_kgs(kgs)})'
    return line


def realtor_contact(listing: Listing) -> str:
    return ', '.join(x for x in (listing.realtor_name, listing.realtor_phone) if x)


class Bot:
    def __init__(self, client):
        self.client = client

    # ---------- вход ----------

    def handle_update(self, update: dict) -> None:
        message = update.get('message')
        callback = update.get('callback_query')
        source = message or (callback or {}).get('message')
        user = (message or callback or {}).get('from')
        if not source or not user:
            return
        chat = source.get('chat') or {}
        if chat.get('type') != 'private':
            return

        if callback:
            self._safe(self.client.answer_callback_query, callback['id'])

        employee = TelegramEmployee.objects.filter(telegram_id=user['id'], is_active=True).first()
        if employee is None:
            self._send(
                chat['id'],
                'Доступ к боту есть только у сотрудников агентства «Открытая Сделка».\n'
                f'Передайте администратору ваш Telegram ID: <code>{user["id"]}</code>',
            )
            return

        session, _ = BotSession.objects.get_or_create(employee=employee, defaults={'chat_id': chat['id']})
        session.chat_id = chat['id']
        try:
            if callback:
                self._on_callback(session, callback.get('data') or '')
            else:
                self._on_message(session, message)
        except Exception:
            logger.exception('tgbot: ошибка обработки update %s', update.get('update_id'))
            self._send(session.chat_id, 'Произошла ошибка. Попробуйте ещё раз или нажмите /start.')
            return
        session.save()

    # ---------- отправка ----------

    def _safe(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except TelegramAPIError as e:
            logger.warning('tgbot: %s', e)
            return None

    def _send(self, chat_id, text, keyboard=None):
        return self._safe(self.client.send_message, chat_id, text, keyboard)

    def _send_one_photo(self, chat_id, photo, caption='', keyboard=None):
        if photo.get('kind') == 'document':
            self._safe(self.client.send_document, chat_id, photo['file_id'], caption)
            if keyboard:
                self._send(chat_id, caption or 'Выберите действие:', keyboard)
            return None
        return self._safe(self.client.send_photo, chat_id, photo['file_id'], caption, keyboard)

    def _send_photos(self, chat_id, photos, numbered=False):
        """Отправляет фото альбомами по 10 (Telegram не смешивает photo и document в одном альбоме)."""
        groups, current = [], []
        for i, photo in enumerate(photos, start=1):
            if current and (len(current) == 10 or current[-1][1]['kind'] != photo['kind']):
                groups.append(current)
                current = []
            current.append((i, photo))
        if current:
            groups.append(current)
        for group in groups:
            if len(group) == 1:
                i, photo = group[0]
                self._send_one_photo(chat_id, photo, str(i) if numbered else '')
                continue
            media = []
            for i, photo in group:
                item = {'type': photo['kind'], 'media': photo['file_id']}
                if numbered:
                    item['caption'] = str(i)
                media.append(item)
            self._safe(self.client.send_media_group, chat_id, media)

    def _send_main_menu(self, session, text):
        self._send(session.chat_id, text, MAIN_KEYBOARD)

    # ---------- сообщения ----------

    def _on_message(self, session: BotSession, message: dict):
        text = (message.get('text') or '').strip()
        group_id = message.get('media_group_id')

        if text in ('/start', '/menu'):
            return self._cmd_start(session)
        if text == '/cancel':
            return self._cmd_cancel(session)
        if text == MENU_ADD:
            return self._menu_add(session)
        if text in (MENU_MY, MENU_EDIT, MENU_DELETE):
            if session.state in EDIT_STATES:
                self._reset_state(session)
            mode = {MENU_MY: 'l', MENU_EDIT: 'e', MENU_DELETE: 'x'}[text]
            return self._show_listing_list(session, mode, 0)

        photo = extract_photo(message)
        state = session.state

        if state == 'add_cover':
            return self._on_cover(session, photo, group_id)
        if state == 'add_photos':
            return self._on_gallery_photo(session, photo, group_id)
        if state == STATE_EDIT_INPUT:
            return self._on_edit_input(session, text, photo, message.get('text') or '')

        if photo and group_id and group_id == session.context.get('last_group'):
            return None
        if state in ADD_STATES:
            if photo:
                return self._send(session.chat_id, 'Сейчас нужно ввести текст, а не фото.')
            if not text:
                return self._send(session.chat_id, 'Пожалуйста, отправьте ответ текстом.')
            return self._on_step_text(session, state, text, message.get('text') or '')
        if state == STATE_PREVIEW:
            return self._send(session.chat_id, 'Проверьте карточку и воспользуйтесь кнопками под ней.')
        if state == STATE_EDIT_CONFIRM:
            return self._send(session.chat_id, 'Подтвердите или отмените изменение кнопками выше.')
        return self._send_main_menu(session, 'Выберите действие в меню ниже.')

    def _cmd_start(self, session):
        if session.state in EDIT_STATES:
            self._reset_state(session)
        text = f'Здравствуйте, {esc(session.employee.full_name)}!\nВыберите действие:'
        if session.draft:
            text += '\n\nУ вас есть незавершённая карточка — нажмите «Добавить объект», чтобы продолжить.'
        self._send_main_menu(session, text)

    def _cmd_cancel(self, session):
        had_draft = bool(session.draft) and (session.state in ADD_STATES or session.state == STATE_PREVIEW)
        self._reset_state(session)
        if had_draft:
            self._send_main_menu(session, 'Действие прервано. Черновик карточки сохранён.')
        else:
            self._send_main_menu(session, 'Действие отменено.')

    def _reset_state(self, session):
        session.state = STATE_IDLE
        session.context = {}

    # ---------- добавление объекта ----------

    def _menu_add(self, session):
        if session.state in EDIT_STATES:
            self._reset_state(session)
        if session.draft:
            title = session.draft.get('title') or 'без названия'
            return self._send(
                session.chat_id,
                f'У вас есть незавершённая карточка «{esc(title)}». Продолжить её или начать заново?',
                inline([[('Продолжить', 'dr:cont'), ('Начать заново', 'dr:new')]]),
            )
        return self._start_new_draft(session)

    def _start_new_draft(self, session):
        session.draft = {}
        session.context = {}
        session.state = 'add_cover'
        self._send(
            session.chat_id,
            'Начинаем добавление объекта. Бот последовательно запросит данные.\n'
            'В любой момент можно ввести /cancel — черновик сохранится.',
        )
        self._prompt(session)

    def _next_missing_state(self, draft) -> str:
        for state, done in ADD_STEPS:
            if not done(draft):
                return state
        return STATE_PREVIEW

    def _resume_draft(self, session):
        session.context = {}
        session.state = self._next_missing_state(session.draft)
        if session.state == STATE_PREVIEW:
            return self._show_preview(session)
        self._prompt(session)

    def _advance(self, session, from_state):
        if session.context.get('return_preview'):
            if from_state in CHAINED_STEPS:
                session.state = CHAINED_STEPS[from_state]
                return self._prompt(session)
            session.context = {}
            session.state = STATE_PREVIEW
            return self._show_preview(session)
        session.state = self._next_missing_state(session.draft)
        if session.state == STATE_PREVIEW:
            return self._show_preview(session)
        self._prompt(session)

    def _current_value_hint(self, session) -> str:
        d = session.draft
        values = {
            'add_title': d.get('title'),
            'add_district': d.get('district'),
            'add_street': d.get('street'),
            'add_rooms': d.get('rooms'),
            'add_area': f"{d['area']} м²" if d.get('area') else None,
            'add_kind': f.KIND_CHOICES.get(d.get('kind')),
            'add_price': f.format_usd(d['price_usd']) if d.get('price_usd') else None,
            'add_realtor_name': d.get('realtor_name'),
            'add_realtor_phone': d.get('realtor_phone'),
        }
        value = values.get(session.state)
        if value in (None, ''):
            return ''
        return f'\nСейчас: <b>{esc(value)}</b>'

    def _prompt(self, session):
        state = session.state
        d = session.draft
        rows = []
        if state == 'add_photos':
            count = len(d.get('photos') or [])
            rows.append([('Далее', 'ph:next')])
            if count >= 2:
                rows.append([('Изменить порядок фото', 'ph:order')])
            if count:
                rows.append([('Удалить загруженные фото', 'ph:reset')])
        elif state == 'add_street':
            rows.append([('Пропустить', 'skip')])
        elif state == 'add_rooms':
            rows.append([(str(n), f'val:{n}') for n in range(1, 6)])
        elif state == 'add_kind':
            kinds = list(f.KIND_CHOICES.items())
            rows += [[(label, f'kind:{key}') for key, label in kinds[i:i + 2]] for i in range(0, len(kinds), 2)]
        elif state == 'add_realtor_name':
            emp = session.employee
            if emp.default_realtor_name and emp.default_realtor_phone:
                rows.append([(f'{emp.default_realtor_name}, {emp.default_realtor_phone}', 'rc:def')])
        if session.context.get('return_preview'):
            rows.append([('Назад к просмотру', 'd:preview')])

        text = f'<b>{STEP_TITLES[state]}</b>\n{STEP_TEXTS[state]}'
        if state == 'add_photos' and d.get('photos'):
            text += f'\nУже загружено: {len(d["photos"])}'
        text += self._current_value_hint(session)
        self._send(session.chat_id, text, inline(rows) if rows else None)

    def _on_cover(self, session, photo, group_id):
        if not photo:
            return self._send(session.chat_id, 'Отправьте, пожалуйста, одно фото фасада объекта.')
        if group_id and group_id == session.context.get('last_group'):
            # Остальные фото из того же альбома считаем галереей.
            session.draft.setdefault('photos', []).append(photo)
            return None
        session.draft['cover'] = photo
        session.context['last_group'] = group_id
        self._send(session.chat_id, 'Обложка сохранена.')
        if session.context.get('return_preview'):
            session.context = {'last_group': group_id}
            session.state = STATE_PREVIEW
            return self._show_preview(session)
        session.state = 'add_photos'
        self._prompt(session)

    def _on_gallery_photo(self, session, photo, group_id):
        if not photo:
            return self._send(session.chat_id, 'Отправьте фото или нажмите «Далее».', inline([[('Далее', 'ph:next')]]))
        photos = session.draft.setdefault('photos', [])
        if len(photos) >= f.MAX_PHOTOS:
            return self._send(session.chat_id, f'Можно загрузить не больше {f.MAX_PHOTOS} фото. Нажмите «Далее».')
        photos.append(photo)
        if group_id:
            if group_id == session.context.get('last_group'):
                return None
            session.context['last_group'] = group_id
            text = 'Получаю фото… Когда все загрузятся, нажмите «Далее».'
        else:
            text = f'Фото добавлено. Всего: {len(photos)}. Отправьте ещё или нажмите «Далее».'
        self._send(session.chat_id, text, inline([[('Далее', 'ph:next')]]))

    def _on_step_text(self, session, state, text, raw_text):
        d = session.draft
        try:
            if state == STATE_PHOTOS_ORDER:
                photos = d.get('photos') or []
                order = f.parse_photo_order(text, len(photos))
                d['photos'] = [photos[i] for i in order]
                session.state = 'add_photos'
                self._send(session.chat_id, 'Порядок фото сохранён.')
                return self._prompt(session)
            if state == 'add_title':
                d['title'] = f.clean_line(text, f.MAX_TITLE_LEN, 'Название')
            elif state == 'add_district':
                d['district'] = f.clean_line(text, f.MAX_ADDRESS_LEN, 'Район')
            elif state == 'add_street':
                d['street'] = f.clean_line(text, f.MAX_ADDRESS_LEN, 'Адрес')
                if len(f.compose_address(d.get('district', ''), d['street'])) > f.MAX_ADDRESS_LEN:
                    raise f.FieldError('Адрес вместе с районом слишком длинный.')
            elif state == 'add_rooms':
                d['rooms'] = f.parse_rooms(text)
            elif state == 'add_area':
                d['area'] = f.parse_area(text)
            elif state == 'add_kind':
                return self._send(session.chat_id, 'Выберите тип объекта кнопкой ниже.')
            elif state == 'add_price':
                d['price_usd'] = f.parse_price_usd(text)
            elif state == 'add_realtor_name':
                d['realtor_name'] = f.clean_line(text, f.MAX_REALTOR_NAME_LEN, 'Имя риэлтора')
            elif state == 'add_realtor_phone':
                d['realtor_phone'] = f.normalize_phone(text)
            elif state == 'add_description':
                d['description'] = f.clean_description(raw_text)
        except f.FieldError as e:
            return self._send(session.chat_id, esc(e))
        self._advance(session, state)

    # ---------- предпросмотр ----------

    def _draft_summary(self, draft) -> str:
        def val(key, fmt=esc):
            v = draft.get(key)
            return fmt(v) if v not in (None, '') else '<i>не заполнено</i>'

        photos = draft.get('photos') or []
        lines = [
            '<b>Предварительный просмотр карточки</b>',
            '',
            f'<b>Название:</b> {val("title")}',
            f'<b>Район:</b> {val("district")}',
        ]
        if draft.get('street'):
            lines.append(f'<b>Адрес:</b> {esc(draft["street"])}')
        lines += [
            f'<b>Комнат:</b> {val("rooms")}',
            f'<b>Площадь:</b> {val("area", lambda v: f"{v} м²")}',
            f'<b>Тип:</b> {val("kind", lambda v: esc(f.KIND_CHOICES.get(v, v)))}',
            f'<b>Стоимость:</b> {val("price_usd", price_line)}',
            f'<b>Риэлтор:</b> {val("realtor_name")}, {val("realtor_phone")}',
            f'<b>Фото:</b> обложка — {"есть" if draft.get("cover") else "нет"}, остальных — {len(photos)}',
        ]
        missing = missing_draft_fields(draft)
        if missing:
            lines += ['', '<b>Не заполнено:</b> ' + esc(', '.join(missing))]
        return '\n'.join(lines)

    def _preview_keyboard(self):
        return inline([
            [('Опубликовать', 'd:pub')],
            [('Редактировать', 'd:edit')],
            [('Отменить загрузку', 'd:cancel')],
        ])

    def _show_preview(self, session):
        d = session.draft
        chat_id = session.chat_id
        if d.get('cover'):
            self._send_one_photo(chat_id, d['cover'], 'Обложка')
        if d.get('photos'):
            self._send_photos(chat_id, d['photos'])
        self._send(chat_id, self._draft_summary(d))
        description = d.get('description') or ''
        chunks = [esc(c) for c in f.split_text(description, 3500)] if description else ['<i>не заполнено</i>']
        for i, chunk in enumerate(chunks):
            text = ('<b>Описание:</b>\n' if i == 0 else '') + chunk
            self._send(chat_id, text, self._preview_keyboard() if i == len(chunks) - 1 else None)

    def _publish(self, session):
        if session.state != STATE_PREVIEW or not session.draft:
            return self._send(session.chat_id, 'Нет карточки для публикации.')
        missing = missing_draft_fields(session.draft)
        if missing:
            return self._send(
                session.chat_id,
                'Нельзя опубликовать: не заполнены поля — ' + esc(', '.join(missing)) + '.',
                inline([[('Редактировать', 'd:edit')]]),
            )
        self._send(session.chat_id, 'Публикую объект на сайте…')
        try:
            listing = publish_draft(self.client, session.employee, session.draft)
        except PublishError as e:
            return self._send(
                session.chat_id,
                f'Ошибка загрузки на сайт: {esc(e)}\n\n'
                'Введённые данные сохранены — можно повторить отправку без заполнения карточки заново.',
                inline([[('Повторить отправку', 'd:pub')], [('Редактировать', 'd:edit')]]),
            )
        emp = session.employee
        emp.default_realtor_name = listing.realtor_name
        emp.default_realtor_phone = listing.realtor_phone
        emp.save(update_fields=['default_realtor_name', 'default_realtor_phone'])
        session.draft = {}
        self._reset_state(session)
        url = listing_url(listing)
        self._send(
            session.chat_id,
            f'Объект успешно опубликован!\n{esc(url)}',
            inline([[('Открыть на сайте', f'url:{url}')]]),
        )
        self._send_main_menu(session, 'Что делаем дальше?')

    # ---------- callback-кнопки ----------

    def _on_callback(self, session: BotSession, data: str):
        action, _, arg = data.partition(':')
        state = session.state
        stale = 'Эта кнопка уже неактуальна. Нажмите /start, чтобы открыть меню.'

        if action == 'dr':
            if arg == 'new' or not session.draft:
                return self._start_new_draft(session)
            return self._resume_draft(session)

        if action == 'ph':
            if state != 'add_photos':
                return self._send(session.chat_id, stale)
            return self._on_photos_action(session, arg)

        if action == 'val' and state == 'add_rooms':
            return self._on_step_text(session, state, arg, arg)
        if action == 'skip' and state == 'add_street':
            session.draft['street'] = ''
            return self._advance(session, state)
        if action == 'kind' and state == 'add_kind':
            if arg not in f.KIND_CHOICES:
                return self._send(session.chat_id, 'Выберите тип из списка.')
            session.draft['kind'] = arg
            return self._advance(session, state)
        if action == 'rc' and state == 'add_realtor_name':
            emp = session.employee
            session.draft['realtor_name'] = emp.default_realtor_name
            session.draft['realtor_phone'] = emp.default_realtor_phone
            return self._advance(session, 'add_realtor_phone')

        if action == 'd':
            return self._on_draft_action(session, arg)
        if action == 'df':
            if not session.draft or arg not in DRAFT_EDIT_STATE:
                return self._send(session.chat_id, stale)
            session.context = {'return_preview': True}
            session.state = DRAFT_EDIT_STATE[arg]
            return self._prompt(session)

        if action == 'lst':
            mode, _, page = arg.partition(':')
            return self._show_listing_list(session, mode, int(page) if page.isdigit() else 0)
        if action == 'obj':
            mode, _, pk = arg.partition(':')
            return self._open_listing(session, mode, pk)
        if action == 'le':
            return self._show_listing_edit_menu(session, arg)
        if action == 'lf':
            pk, _, field = arg.partition(':')
            return self._start_listing_edit(session, pk, field)
        if action == 'cf':
            return self._on_edit_confirm(session, arg == 'yes')
        if action == 'ld':
            return self._ask_delete(session, arg)
        if action == 'ldy':
            return self._do_delete(session, arg)
        if action == 'ldn':
            return self._send(session.chat_id, 'Удаление отменено.')

        return self._send(session.chat_id, stale)

    def _on_photos_action(self, session, arg):
        photos = session.draft.get('photos') or []
        if arg == 'next':
            session.draft['photos_done'] = True
            session.context.pop('last_group', None)
            self._send(session.chat_id, f'Загружено дополнительных фото: {len(photos)}.')
            return self._advance(session, 'add_photos')
        if arg == 'order':
            if len(photos) < 2:
                return self._send(session.chat_id, 'Чтобы менять порядок, нужно минимум 2 фото.')
            self._send_photos(session.chat_id, photos, numbered=True)
            session.state = STATE_PHOTOS_ORDER
            return self._send(
                session.chat_id,
                'Введите новый порядок номеров через пробел, например: 3 1 2\n'
                'Можно указать только те фото, которые нужно поставить первыми.',
            )
        if arg == 'reset':
            session.draft['photos'] = []
            session.context.pop('last_group', None)
            self._send(session.chat_id, 'Загруженные фото удалены.')
            return self._prompt(session)
        return None

    def _on_draft_action(self, session, arg):
        if arg == 'pub':
            return self._publish(session)
        if not session.draft:
            return self._send(session.chat_id, 'Черновик не найден. Нажмите «Добавить объект».')
        if arg == 'preview':
            session.context = {}
            session.state = STATE_PREVIEW
            return self._show_preview(session)
        if arg == 'edit':
            session.context = {}
            session.state = STATE_PREVIEW
            buttons = [(label, f'df:{key}') for key, label, _ in DRAFT_EDIT_FIELDS]
            rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
            rows.append([('Назад к просмотру', 'd:preview')])
            return self._send(session.chat_id, 'Какое поле изменить?', inline(rows))
        if arg == 'cancel':
            return self._send(
                session.chat_id,
                'Отменить загрузку? Черновик карточки будет удалён.',
                inline([[('Да, удалить черновик', 'd:drop'), ('Нет', 'd:preview')]]),
            )
        if arg == 'drop':
            session.draft = {}
            self._reset_state(session)
            return self._send_main_menu(session, 'Загрузка отменена, черновик удалён.')
        return None

    # ---------- мои объекты ----------

    def _owned_listings(self, employee):
        qs = Listing.objects.all()
        if not employee.can_manage_all:
            qs = qs.filter(telegram_author=employee)
        return qs.order_by('-published_at')

    def _get_listing(self, session, pk) -> Listing | None:
        try:
            pk = int(pk)
        except (TypeError, ValueError):
            pk = None
        listing = self._owned_listings(session.employee).filter(pk=pk).first() if pk else None
        if listing is None:
            self._send(session.chat_id, 'Объект не найден или у вас нет к нему доступа.')
        return listing

    def _show_listing_list(self, session, mode, page):
        if mode not in ('l', 'e', 'x'):
            mode = 'l'
        qs = self._owned_listings(session.employee)
        total = qs.count()
        if not total:
            return self._send_main_menu(session, 'У вас пока нет загруженных объектов.')
        pages = (total + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE
        page = max(0, min(page, pages - 1))
        items = qs.only('pk', 'title', 'price')[page * LIST_PAGE_SIZE:(page + 1) * LIST_PAGE_SIZE]
        rows = [[(f'{item.title} — {item.price}'[:60], f'obj:{mode}:{item.pk}')] for item in items]
        nav = []
        if page > 0:
            nav.append(('← Назад', f'lst:{mode}:{page - 1}'))
        if page < pages - 1:
            nav.append(('Ещё →', f'lst:{mode}:{page + 1}'))
        if nav:
            rows.append(nav)
        title = {
            'l': 'Ваши объекты',
            'e': 'Выберите объект для редактирования',
            'x': 'Выберите объект для удаления',
        }[mode]
        suffix = f' (стр. {page + 1} из {pages})' if pages > 1 else ''
        self._send(session.chat_id, f'{title} — всего {total}{suffix}:', inline(rows))

    def _listing_caption(self, listing) -> str:
        updated = timezone.localtime(listing.published_at).strftime('%d.%m.%Y %H:%M')
        lines = [
            f'<b>{esc(listing.title)}</b>',
            esc(listing.address),
            f'{listing.rooms} комн. · {listing.area} м² · {esc(listing.object_kind_label)}',
            price_line(listing.price_usd, listing.price),
        ]
        if realtor_contact(listing):
            lines.append(f'Риэлтор: {esc(realtor_contact(listing))}')
        lines += [f'Опубликовано/обновлено: {updated}', esc(listing_url(listing))]
        return '\n'.join(lines)

    def _open_listing(self, session, mode, pk):
        if mode == 'e':
            return self._show_listing_edit_menu(session, pk)
        if mode == 'x':
            return self._ask_delete(session, pk)
        listing = self._get_listing(session, pk)
        if not listing:
            return None
        keyboard = inline([
            [('Редактировать', f'le:{listing.pk}'), ('Удалить', f'ld:{listing.pk}')],
            [('Открыть на сайте', f'url:{listing_url(listing)}')],
        ])
        self._send(session.chat_id, self._listing_caption(listing), keyboard)

    def _show_listing_edit_menu(self, session, pk):
        listing = self._get_listing(session, pk)
        if not listing:
            return None
        if session.state in EDIT_STATES:
            self._reset_state(session)
        rows = [[(label, f'lf:{listing.pk}:{key}')] for key, label in LISTING_EDIT_FIELDS]
        rows.append([('Назад', f'obj:l:{listing.pk}')])
        self._send(session.chat_id, f'Что изменить в объекте «{esc(listing.title)}»?', inline(rows))

    # ---------- редактирование опубликованного объекта ----------

    def _start_listing_edit(self, session, pk, field):
        if field not in LISTING_EDIT_KEYS:
            return self._send(session.chat_id, 'Это поле нельзя изменить.')
        listing = self._get_listing(session, pk)
        if not listing:
            return None
        session.state = STATE_EDIT_INPUT
        session.context = {'listing_id': listing.pk, 'field': field, 'step': 0}
        prompts = {
            'price': f'Текущая цена объекта — {esc(listing.price)}. Введите новую цену.',
            'area': f'Текущая площадь — {listing.area} м². Введите новую площадь (м²).',
            'title': f'Текущий заголовок: «{esc(listing.title)}».\nВведите новый заголовок.',
            'description': 'Отправьте новое полное описание объекта одним сообщением.',
            'cover': 'Отправьте новое фото для обложки объекта.',
            'realtor': (
                f'Текущий контакт риэлтора: {esc(realtor_contact(listing) or "—")}.\n'
                'Введите имя риэлтора.'
            ),
        }
        self._send(session.chat_id, prompts[field] + '\n\nДля отмены — /cancel')

    def _edit_question(self, listing, field, value) -> str:
        if field == 'price':
            return f'Вы хотите изменить стоимость с {esc(listing.price)} на {f.format_usd(value)}?'
        if field == 'area':
            return f'Вы хотите изменить площадь с {listing.area} м² на {value} м²?'
        if field == 'title':
            return f'Вы хотите изменить заголовок с «{esc(listing.title)}» на «{esc(value)}»?'
        if field == 'realtor':
            old = realtor_contact(listing) or '—'
            return f'Вы хотите изменить контакт риэлтора с «{esc(old)}» на «{esc(value[0])}, {esc(value[1])}»?'
        if field == 'cover':
            return 'Заменить обложку объекта на это фото?'
        snippet = value if len(value) <= 700 else value[:700] + '…'
        return f'Вы хотите заменить описание объекта на новое?\n\n{esc(snippet)}'

    def _on_edit_input(self, session, text, photo, raw_text):
        ctx = session.context
        field = ctx.get('field')
        listing = self._get_listing(session, ctx.get('listing_id'))
        if not listing:
            return self._reset_state(session)
        try:
            if field == 'cover':
                if not photo:
                    return self._send(session.chat_id, 'Отправьте, пожалуйста, фото.')
                ctx['value'] = photo
            elif not text:
                return self._send(session.chat_id, 'Пожалуйста, отправьте ответ текстом.')
            elif field == 'price':
                ctx['value'] = f.parse_price_usd(text)
            elif field == 'area':
                ctx['value'] = f.parse_area(text)
            elif field == 'title':
                ctx['value'] = f.clean_line(text, f.MAX_TITLE_LEN, 'Заголовок')
            elif field == 'description':
                ctx['value'] = f.clean_description(raw_text)
            elif field == 'realtor':
                if ctx.get('step', 0) == 0:
                    ctx['name'] = f.clean_line(text, f.MAX_REALTOR_NAME_LEN, 'Имя риэлтора')
                    ctx['step'] = 1
                    return self._send(session.chat_id, 'Введите номер телефона риэлтора.\nПример: 0509 349 199')
                ctx['value'] = [ctx['name'], f.normalize_phone(text)]
        except f.FieldError as e:
            return self._send(session.chat_id, esc(e))

        session.state = STATE_EDIT_CONFIRM
        keyboard = inline([[('Подтвердить', 'cf:yes'), ('Отменить', 'cf:no')]])
        question = self._edit_question(listing, field, ctx['value'])
        if field == 'cover':
            return self._send_one_photo(session.chat_id, ctx['value'], question, keyboard)
        self._send(session.chat_id, question, keyboard)

    def _on_edit_confirm(self, session, confirmed):
        if session.state != STATE_EDIT_CONFIRM:
            return self._send(session.chat_id, 'Нет изменения, ожидающего подтверждения.')
        ctx = session.context
        if not confirmed:
            self._reset_state(session)
            return self._send_main_menu(session, 'Изменение отменено.')
        listing = self._get_listing(session, ctx.get('listing_id'))
        if not listing:
            return self._reset_state(session)
        field, value = ctx['field'], ctx['value']
        try:
            update_listing_field(self.client, session.employee, listing, field, value)
        except PublishError as e:
            return self._send(
                session.chat_id,
                f'Ошибка: {esc(e)}\nМожно повторить попытку.',
                inline([[('Повторить', 'cf:yes'), ('Отменить', 'cf:no')]]),
            )
        self._reset_state(session)
        messages = {
            'price': f'Цена успешно изменена. Новая стоимость: {esc(listing.price)}.',
            'area': f'Площадь успешно изменена. Новая площадь: {listing.area} м².',
            'title': f'Заголовок успешно изменён: «{esc(listing.title)}».',
            'description': 'Описание успешно изменено.',
            'cover': 'Обложка успешно изменена.',
            'realtor': f'Контакт риэлтора успешно изменён: {esc(realtor_contact(listing))}.',
        }
        url = listing_url(listing)
        self._send(
            session.chat_id,
            f'{messages[field]}\n{esc(url)}',
            inline([[('Открыть на сайте', f'url:{url}')]]),
        )

    # ---------- удаление ----------

    def _ask_delete(self, session, pk):
        listing = self._get_listing(session, pk)
        if not listing:
            return None
        self._send(
            session.chat_id,
            f'Удалить объект «{esc(listing.title)}» с сайта?\n'
            'Объект и его фотографии будут удалены, он исчезнет из каталога и поиска. '
            'Это действие нельзя отменить.',
            inline([[('Да, удалить', f'ldy:{listing.pk}'), ('Отмена', 'ldn')]]),
        )

    def _do_delete(self, session, pk):
        listing = self._get_listing(session, pk)
        if not listing:
            return None
        try:
            delete_listing(session.employee, listing)
        except PublishError as e:
            return self._send(session.chat_id, f'Ошибка: {esc(e)}', inline([[('Повторить', f'ldy:{pk}')]]))
        self._reset_state(session)
        self._send_main_menu(session, 'Объект успешно удалён с сайта.')
