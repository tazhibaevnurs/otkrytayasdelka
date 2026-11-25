"""Сквозные сценарии бота из ТЗ с фейковым Telegram-клиентом."""
import io
import itertools
import shutil
import tempfile

from django.core.cache import cache
from django.test import TestCase, override_settings
from PIL import Image

from listings.models import Listing, ListingImage
from tgbot.handlers import MENU_ADD, MENU_MY, Bot
from tgbot.models import BotSession, ListingChangeLog, TelegramEmployee
from tgbot.telegram_api import TelegramAPIError

_ids = itertools.count(1)


def _jpeg_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (64, 48), (201, 168, 76)).save(buf, format='JPEG')
    return buf.getvalue()


class FakeClient:
    def __init__(self):
        self.sent = []
        self.downloads = []
        self.fail_downloads = False
        self._jpeg = _jpeg_bytes()

    def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append(('message', text, reply_markup))

    def send_photo(self, chat_id, file_id, caption='', reply_markup=None):
        self.sent.append(('photo', caption, reply_markup))

    def send_document(self, chat_id, file_id, caption=''):
        self.sent.append(('document', caption, None))

    def send_media_group(self, chat_id, media):
        self.sent.append(('media_group', [m['media'] for m in media], None))

    def answer_callback_query(self, callback_query_id, text=''):
        pass

    def download_file(self, file_id):
        if self.fail_downloads:
            raise TelegramAPIError('network down')
        self.downloads.append(file_id)
        return self._jpeg, f'photos/{file_id}.jpg'

    def texts(self):
        return [item[1] for item in self.sent if item[0] == 'message']

    def last_text(self):
        return self.texts()[-1]


def message(uid, text=None, photo=None, group=None):
    n = next(_ids)
    msg = {'message_id': n, 'from': {'id': uid}, 'chat': {'id': uid, 'type': 'private'}}
    if text is not None:
        msg['text'] = text
    if photo:
        msg['photo'] = [{'file_id': photo + '_small'}, {'file_id': photo}]
    if group:
        msg['media_group_id'] = group
    return {'update_id': n, 'message': msg}


def callback(uid, data):
    n = next(_ids)
    return {
        'update_id': n,
        'callback_query': {
            'id': str(n),
            'from': {'id': uid},
            'data': data,
            'message': {'message_id': n, 'chat': {'id': uid, 'type': 'private'}},
        },
    }


@override_settings(SITE_URL='https://example.kg')
class BotFlowTestCase(TestCase):
    UID = 1001

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.employee = TelegramEmployee.objects.create(telegram_id=self.UID, full_name='Наргиза')
        self.client_tg = FakeClient()
        self.bot = Bot(self.client_tg)

    def send(self, text=None, photo=None, group=None, uid=None):
        self.bot.handle_update(message(uid or self.UID, text=text, photo=photo, group=group))

    def press(self, data, uid=None):
        self.bot.handle_update(callback(uid or self.UID, data))

    def session(self):
        return BotSession.objects.get(employee=self.employee)

    def bot_listings(self):
        return Listing.objects.filter(telegram_author=self.employee)

    def fill_draft_to_preview(self):
        self.send(MENU_ADD)
        self.send(photo='cover')
        self.send(photo='p1')
        self.send(photo='p2')
        self.send(photo='p3')
        self.press('ph:order')
        self.send('3 1')
        self.press('ph:next')
        self.send('2-комнатная квартира ПСО')
        self.send('мкр. Асанбай')
        self.press('skip')
        self.press('val:2')
        self.send('67')
        self.press('kind:apartment')
        self.send('91 000')
        self.send('Наргиза')
        self.send('0509 349 199')
        self.send('Срочно! Продаю!\n\nДОМ Премиум Класса,\nОкна выходят на Север!')

    def make_listing(self, author=None, **kwargs):
        defaults = dict(
            title='2-комнатная квартира ПСО',
            address='мкр. Асанбай',
            price='91 000 $',
            price_usd=91000,
            rooms=2,
            area=67,
            description='Описание',
            realtor_name='Наргиза',
            realtor_phone='0509 349 199',
            telegram_author=author or self.employee,
        )
        defaults.update(kwargs)
        return Listing.objects.create(**defaults)


class AddListingFlowTests(BotFlowTestCase):
    def test_full_add_flow_publishes_listing(self):
        self.fill_draft_to_preview()
        self.assertEqual(self.session().state, 'preview')
        self.assertIn('Предварительный просмотр', '\n'.join(self.client_tg.texts()))

        self.press('d:pub')

        listing = self.bot_listings().get()
        self.assertEqual(listing.title, '2-комнатная квартира ПСО')
        self.assertEqual(listing.address, 'мкр. Асанбай')
        self.assertEqual((listing.rooms, listing.area, listing.price_usd), (2, 67, 91000))
        self.assertEqual(listing.price, '91 000 $')
        self.assertEqual(listing.object_kind, Listing.KIND_APARTMENT)
        self.assertEqual(listing.description, 'Срочно! Продаю!\n\nДОМ Премиум Класса,\nОкна выходят на Север!')
        self.assertEqual((listing.realtor_name, listing.realtor_phone), ('Наргиза', '0509 349 199'))
        self.assertEqual(listing.telegram_author, self.employee)
        self.assertTrue(listing.is_published)
        self.assertTrue(listing.image.name.startswith('listings/tg_'))
        # Обложка скачивается первой, галерея — в порядке после «3 1»: p3, p1, p2.
        self.assertEqual(self.client_tg.downloads, ['cover', 'p3', 'p1', 'p2'])
        self.assertEqual(list(ListingImage.objects.filter(listing=listing).values_list('order', flat=True)), [1, 2, 3])

        texts = '\n'.join(self.client_tg.texts())
        self.assertIn('Объект успешно опубликован!', texts)
        self.assertIn(f'https://example.kg/catalog/{listing.public_uuid}/', texts)
        session = self.session()
        self.assertEqual((session.state, session.draft), ('idle', {}))
        self.assertTrue(ListingChangeLog.objects.filter(listing=listing, action='create', employee=self.employee).exists())

    def test_publish_failure_keeps_draft_and_retry_works(self):
        self.fill_draft_to_preview()
        self.client_tg.fail_downloads = True
        self.press('d:pub')

        self.assertFalse(self.bot_listings().exists())
        self.assertIn('Повторить отправку', str(self.client_tg.sent[-1][2]))
        session = self.session()
        self.assertEqual(session.state, 'preview')
        self.assertEqual(session.draft['title'], '2-комнатная квартира ПСО')

        self.client_tg.fail_downloads = False
        self.press('d:pub')
        self.assertEqual(self.bot_listings().count(), 1)

    def test_cannot_publish_with_missing_fields(self):
        self.send(MENU_ADD)
        session = self.session()
        session.state = 'preview'
        session.draft = {'title': 'Без фото'}
        session.save()

        self.press('d:pub')
        self.assertFalse(self.bot_listings().exists())
        self.assertIn('Нельзя опубликовать', self.client_tg.last_text())
        self.assertIn('Обложка', self.client_tg.last_text())

    def test_invalid_input_keeps_step(self):
        self.fill_draft_to_preview()
        self.press('d:edit')
        self.press('df:price')
        self.send('бесплатно')
        self.assertEqual(self.session().state, 'add_price')
        self.send('95 000')
        session = self.session()
        self.assertEqual(session.state, 'preview')
        self.assertEqual(session.draft['price_usd'], 95000)
        self.assertEqual(session.draft['title'], '2-комнатная квартира ПСО')

    def test_unfinished_draft_is_resumed(self):
        self.send(MENU_ADD)
        self.send(photo='cover')
        self.press('ph:next')
        self.send('Дом в Ала-Арче')

        self.send('/cancel')
        self.assertEqual(self.session().state, 'idle')
        self.assertEqual(self.session().draft['title'], 'Дом в Ала-Арче')

        self.send(MENU_ADD)
        self.assertIn('незавершённая карточка', self.client_tg.last_text())
        self.press('dr:cont')
        self.assertEqual(self.session().state, 'add_district')

    def test_album_on_cover_step_splits_into_cover_and_gallery(self):
        self.send(MENU_ADD)
        self.send(photo='a1', group='g1')
        self.send(photo='a2', group='g1')
        self.send(photo='a3', group='g1')
        draft = self.session().draft
        self.assertEqual(draft['cover']['file_id'], 'a1')
        self.assertEqual([p['file_id'] for p in draft['photos']], ['a2', 'a3'])

    def test_cancel_upload_drops_draft(self):
        self.fill_draft_to_preview()
        self.press('d:cancel')
        self.press('d:drop')
        session = self.session()
        self.assertEqual((session.state, session.draft), ('idle', {}))
        self.assertFalse(self.bot_listings().exists())


class EditListingFlowTests(BotFlowTestCase):
    def test_price_edit_updates_existing_card_and_bumps_it(self):
        listing = self.make_listing()
        uuid_before, published_before = listing.public_uuid, listing.published_at

        self.press(f'lf:{listing.pk}:price')
        self.assertIn('Текущая цена объекта — 91 000 $', self.client_tg.last_text())
        self.send('87 000')
        self.assertIn('Вы хотите изменить стоимость с 91 000 $ на 87 000 $?', self.client_tg.last_text())
        self.press('cf:yes')

        listing.refresh_from_db()
        self.assertEqual(self.bot_listings().count(), 1)
        self.assertEqual(listing.public_uuid, uuid_before)
        self.assertEqual((listing.price, listing.price_usd), ('87 000 $', 87000))
        self.assertEqual(listing.description, 'Описание')
        self.assertGreater(listing.published_at, published_before)
        self.assertIn('Цена успешно изменена. Новая стоимость: 87 000 $.', self.client_tg.last_text())
        self.assertIn(str(listing.public_uuid), self.client_tg.last_text())

        log = ListingChangeLog.objects.get(action='update')
        self.assertEqual((log.field, log.old_value, log.new_value, log.employee), ('price', '91 000 $', '87 000 $', self.employee))

    def test_realtor_edit_is_two_steps(self):
        listing = self.make_listing()
        self.press(f'lf:{listing.pk}:realtor')
        self.send('Айгуль')
        self.send('0555 123 456')
        self.press('cf:yes')
        listing.refresh_from_db()
        self.assertEqual((listing.realtor_name, listing.realtor_phone), ('Айгуль', '0555 123 456'))

    def test_cover_edit_replaces_main_image(self):
        listing = self.make_listing()
        self.press(f'lf:{listing.pk}:cover')
        self.send(photo='newcover')
        self.press('cf:yes')
        listing.refresh_from_db()
        self.assertTrue(listing.image.name.startswith('listings/tg_'))
        self.assertEqual(self.client_tg.downloads, ['newcover'])

    def test_cancel_edit_keeps_value(self):
        listing = self.make_listing()
        self.press(f'lf:{listing.pk}:title')
        self.send('Новый заголовок')
        self.press('cf:no')
        listing.refresh_from_db()
        self.assertEqual(listing.title, '2-комнатная квартира ПСО')
        self.assertEqual(self.session().state, 'idle')

    def test_cannot_edit_foreign_listing(self):
        other = TelegramEmployee.objects.create(telegram_id=2002, full_name='Другой')
        listing = self.make_listing(author=other)
        self.press(f'lf:{listing.pk}:price')
        self.assertIn('не найден', self.client_tg.last_text())
        self.assertEqual(self.session().state, 'idle')

    def test_manager_sees_all_listings(self):
        other = TelegramEmployee.objects.create(telegram_id=2002, full_name='Другой')
        self.make_listing(author=other, title='Чужой объект')
        self.send(MENU_MY)
        self.assertIn('У вас пока нет', self.client_tg.last_text())

        self.employee.can_manage_all = True
        self.employee.save()
        self.send(MENU_MY)
        self.assertIn('Чужой объект', str(self.client_tg.sent[-1][2]))


class DeleteListingFlowTests(BotFlowTestCase):
    def test_delete_removes_listing_and_logs(self):
        listing = self.make_listing()
        uuid = listing.public_uuid
        self.press(f'ld:{listing.pk}')
        self.assertIn('Удалить объект', self.client_tg.last_text())
        self.assertTrue(self.bot_listings().exists())

        self.press(f'ldy:{listing.pk}')
        self.assertFalse(self.bot_listings().exists())
        self.assertIn('Объект успешно удалён с сайта.', self.client_tg.last_text())
        log = ListingChangeLog.objects.get(action='delete')
        self.assertEqual((log.listing, log.listing_public_uuid, log.employee), (None, uuid, self.employee))

        response = self.client.get(f'/catalog/{uuid}/')
        self.assertEqual(response.status_code, 404)


class AccessTests(BotFlowTestCase):
    def test_unknown_user_gets_id_and_no_session(self):
        self.send('/start', uid=999)
        self.assertIn('<code>999</code>', self.client_tg.last_text())
        self.assertFalse(BotSession.objects.filter(employee__telegram_id=999).exists())

    def test_inactive_employee_is_denied(self):
        self.employee.is_active = False
        self.employee.save()
        self.send(MENU_ADD)
        self.assertIn('Доступ к боту есть только у сотрудников', self.client_tg.last_text())

    def test_group_chats_are_ignored(self):
        update = message(self.UID, text='/start')
        update['message']['chat']['type'] = 'group'
        self.bot.handle_update(update)
        self.assertEqual(self.client_tg.sent, [])
