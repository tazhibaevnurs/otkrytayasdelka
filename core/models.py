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
    image_url = models.URLField('Или ссылка на изображение', blank=True, help_text='Если не загружаете файл')
    label = models.CharField('Подпись в админке', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Изображение секции'
        verbose_name_plural = 'Изображения секций'

    def __str__(self):
        return self.label or self.get_key_display() or self.key

    def get_url(self, request=None):
        """Возвращает URL изображения: приоритет у ссылки (image_url), иначе загруженный файл."""
        if self.image_url and self.image_url.strip():
            return self.image_url.strip()
        if self.image:
            return request.build_absolute_uri(self.image.url) if request else self.image.url
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
    author_name = models.CharField('Имя / подпись', max_length=200, default='Отзыв клиента')
    text = models.TextField('Текст отзыва')
    image = models.ImageField('Фото автора', upload_to='reviews/', blank=True, null=True)
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Показывать', default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    def __str__(self):
        return self.author_name or f'Отзыв #{self.pk}'


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
