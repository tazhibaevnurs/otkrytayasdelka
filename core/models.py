import os
import re
from django.db import models


# Ключи для SectionImage (изображения секций, управляемые из админки)
SECTION_IMAGE_KEYS = [
    ('home_hero', 'Главная — Hero'),
    ('advantage_1', 'Преимущества — карточка 1'),
    ('advantage_2', 'Преимущества — карточка 2'),
    ('advantage_3', 'Преимущества — карточка 3'),
    ('advantage_4', 'Преимущества — карточка 4'),
    ('advantage_5', 'Преимущества — карточка 5'),
    ('advantage_6', 'Преимущества — карточка 6'),
    ('help_block', 'Блок «Чем мы можем вам помочь»'),
    ('cta_bg', 'Призыв к действию — фон (все страницы)'),
    ('about_image', 'Страница «О нас»'),
    ('purchase_hero', 'Страница «Покупка» — Hero'),
    ('sale_hero', 'Страница «Продажа» — Hero'),
]


class SectionImage(models.Model):
    """Изображение для секции сайта (Hero, преимущества, CTA и т.д.). Ключ уникален."""
    key = models.CharField('Ключ', max_length=50, unique=True, choices=SECTION_IMAGE_KEYS)
    image = models.ImageField('Изображение', upload_to='sections/', blank=True, null=True)
    image_optimized = models.ImageField(
        'Веб-версия (авто)',
        upload_to='sections/web/',
        blank=True,
        null=True,
        editable=False,
        help_text='Сжатая копия для быстрой загрузки (до 1920px). Создаётся при сохранении файла.',
    )
    image_url = models.URLField('Или ссылка на изображение', blank=True, help_text='Если не загружаете файл')
    label = models.CharField('Подпись в админке', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Изображение секции'
        verbose_name_plural = 'Изображения секций'

    def __str__(self):
        return self.label or self.get_key_display() or self.key

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        old_image_name = None
        if self.pk:
            ref = SectionImage.objects.filter(pk=self.pk).only('image').first()
            if ref and ref.image:
                old_image_name = ref.image.name

        super().save(*args, **kwargs)

        if update_fields is not None and 'image' not in update_fields:
            return

        if not self.image:
            if self.image_optimized:
                self.image_optimized.delete(save=False)
                self.image_optimized = None
                super().save(update_fields=['image_optimized'])
            return

        if old_image_name == self.image.name and self.image_optimized:
            return

        from .image_utils import downscale_field_to_jpeg

        try:
            data = downscale_field_to_jpeg(self.image, max_size=(1920, 1080), quality=85)
        except Exception:
            return

        base = self.image.name.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        opt_name = f'{base}_web.jpg'
        if self.image_optimized:
            self.image_optimized.delete(save=False)
        self.image_optimized.save(opt_name, data, save=False)
        super().save(update_fields=['image_optimized'])

    def get_url(self, request=None):
        """Сначала веб-копия (меньший вес), иначе оригинал; если файла нет на диске — image_url.
        Важно: чтобы фото менялось на проде, файл нужно загружать в админке на том же сервере."""
        if self.image_optimized:
            try:
                path = getattr(self.image_optimized, 'path', None)
                if path and os.path.isfile(path):
                    url = self.image_optimized.url or ''
                    if url and not url.startswith('/') and not url.startswith('http'):
                        url = '/' + url
                    out = request.build_absolute_uri(url) if request else (url or self.image_optimized.url)
                    if out:
                        return out
            except Exception:
                pass
        if self.image:
            try:
                path = getattr(self.image, 'path', None)
                if path and os.path.isfile(path):
                    url = self.image.url or ''
                    if url and not url.startswith('/') and not url.startswith('http'):
                        url = '/' + url
                    out = request.build_absolute_uri(url) if request else (url or self.image.url)
                    if out:
                        return out
                # файла нет на диске (загружен локально или удалён) — не отдаём битую ссылку
            except Exception:
                pass
            if self.image_url and self.image_url.strip():
                return self.image_url.strip()
        if self.image_url and self.image_url.strip():
            return self.image_url.strip()
        return ''


class ContactRequest(models.Model):
    """Заявка с формы контактов (имя, телефон, сообщение)."""
    STATUS_NEW = 'new'
    STATUS_READ = 'read'
    STATUS_CONTACTED = 'contacted'
    STATUS_CHOICES = [
        (STATUS_NEW, 'Новая'),
        (STATUS_READ, 'Просмотрена'),
        (STATUS_CONTACTED, 'Связались'),
    ]

    name = models.CharField('Имя', max_length=100)
    phone = models.CharField('Телефон', max_length=20)
    message = models.TextField('Сообщение', blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'

    def __str__(self):
        return f'{self.name} — {self.phone}'


class Review(models.Model):
    """Отзыв на главной странице."""
    author_name = models.CharField('ФИО', max_length=200, default='Отзыв клиента')
    text = models.TextField('Текст отзыва', blank=True)
    image = models.ImageField('Фото', upload_to='reviews/', blank=True, null=True)
    image_url = models.URLField('Ссылка на фото', blank=True)
    video = models.FileField('Видео', upload_to='reviews/videos/', blank=True, null=True)
    video_url = models.URLField('Ссылка на видео', blank=True)
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показывать', default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    def __str__(self):
        return self.author_name or f'Отзыв #{self.pk}'


class Employee(models.Model):
    """Сотрудник агентства — страница «Команда»."""
    full_name = models.CharField('ФИО', max_length=200)
    position = models.CharField('Должность', max_length=150, blank=True)
    photo = models.ImageField('Фото', upload_to='team/', blank=True, null=True)
    photo_url = models.URLField(
        'Ссылка на фото',
        blank=True,
        help_text='Если не загружаете файл с диска',
    )
    bio = models.TextField('О сотруднике', blank=True)
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показывать на сайте', default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

    def __str__(self):
        return self.full_name

    @property
    def photo_display_url(self):
        """Относительный URL фото: загрузка или внешняя ссылка."""
        if self.photo:
            return self.photo.url
        return (self.photo_url or '').strip()


class TeamPageSettings(models.Model):
    """Настройки страницы «Команда», редактируемые через админку."""
    section_badge = models.CharField(
        'Бейдж секции',
        max_length=80,
        default='[ КОМАНДА ]',
        help_text='Короткий верхний бейдж над заголовком.',
    )
    section_title = models.CharField(
        'Заголовок секции',
        max_length=255,
        default='Наши сотрудники',
    )
    section_description = models.TextField(
        'Описание секции',
        default='Профессионалы, которые сопровождают сделки с недвижимостью: подбор объектов, переговоры, юридическая проверка и поддержка на каждом этапе.',
    )
    profile_label = models.CharField(
        'Заголовок на обороте карточки',
        max_length=80,
        default='Профиль',
    )
    empty_bio_fallback = models.TextField(
        'Текст по умолчанию (если bio пустой)',
        default='Специалист агентства «Открытая Сделка». Поможет с подбором объекта, переговорами и сопровождением сделки.',
    )

    class Meta:
        verbose_name = 'Настройки страницы «Команда»'
        verbose_name_plural = 'Настройки страницы «Команда»'

    def __str__(self):
        return 'Настройки страницы «Команда»'


class FeaturedMedia(models.Model):
    """Блок на главной: видео YouTube или картинка (управляется из админки)."""
    MEDIA_YOUTUBE = 'youtube'
    MEDIA_IMAGE = 'image'
    MEDIA_CHOICES = [
        (MEDIA_YOUTUBE, 'YouTube видео'),
        (MEDIA_IMAGE, 'Изображение'),
    ]

    title = models.CharField('Заголовок', max_length=255, default='Знаем все нюансы продажи и покупки недвижимости')
    description = models.TextField('Описание', blank=True, default='Мы ведём YouTube-канал, на котором даём полезные советы и делаем обзоры недвижимости.')
    media_type = models.CharField('Тип', max_length=20, choices=MEDIA_CHOICES, default=MEDIA_YOUTUBE)
    youtube_url = models.URLField('Ссылка на YouTube (watch или youtu.be)', blank=True)
    image = models.ImageField('Изображение', upload_to='featured_media/', blank=True, null=True)
    image_url = models.URLField('Ссылка на картинку (если не загружено)', blank=True)
    link_label = models.CharField('Текст кнопки', max_length=100, blank=True, default='Подписаться на канал')
    link_url = models.URLField('Ссылка кнопки', blank=True, default='https://www.youtube.com')
    order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показывать на главной', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Медиа-блок (YouTube/картинка)'
        verbose_name_plural = 'Медиа-блоки на главной'

    def __str__(self):
        return self.title or f'Медиа #{self.pk}'

    def get_youtube_embed_url(self):
        """Из ссылки YouTube возвращает URL для iframe embed."""
        if not self.youtube_url:
            return ''
        # Поддержка: watch?v=ID, youtu.be/ID
        m = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', self.youtube_url)
        return f'https://www.youtube.com/embed/{m.group(1)}' if m else ''

    @property
    def image_display_url(self):
        """URL картинки: загрузка или image_url."""
        if self.image:
            return self.image.url
        return self.image_url or ''
