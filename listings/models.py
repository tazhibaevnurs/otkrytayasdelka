import uuid
from decimal import Decimal

from django.core.cache import cache
from django.db import models
from django.utils import timezone

USD_KGS_RATE_CACHE_KEY = 'listings:usd_kgs_rate'


class Listing(models.Model):
    """Объект недвижимости в каталоге."""
    TYPE_SALE = 'sale'
    TYPE_PURCHASE = 'purchase'
    TYPE_CHOICES = [
        (TYPE_SALE, 'Продажа'),
        (TYPE_PURCHASE, 'Покупка'),
    ]
    PROPERTY_RESIDENTIAL = 'residential'
    PROPERTY_COMMERCIAL = 'commercial'
    PROPERTY_CHOICES = [
        (PROPERTY_RESIDENTIAL, 'Жилое'),
        (PROPERTY_COMMERCIAL, 'Коммерческое помещение'),
    ]
    KIND_APARTMENT = 'apartment'
    KIND_HOUSE = 'house'
    KIND_COMMERCIAL = 'commercial'
    KIND_LAND = 'land'
    KIND_CHOICES = [
        (KIND_APARTMENT, 'Квартира'),
        (KIND_HOUSE, 'Дом'),
        (KIND_COMMERCIAL, 'Коммерческая недвижимость'),
        (KIND_LAND, 'Земельный участок'),
    ]

    public_uuid = models.UUIDField(
        'Публичный идентификатор',
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    title = models.CharField('Название', max_length=255)
    address = models.CharField('Адрес', max_length=255)
    listing_type = models.CharField('Тип', max_length=20, choices=TYPE_CHOICES, default=TYPE_SALE)
    property_category = models.CharField(
        'Категория',
        max_length=20,
        choices=PROPERTY_CHOICES,
        default=PROPERTY_RESIDENTIAL,
    )
    is_land_plot = models.BooleanField('Земельный участок', default=False)
    object_kind = models.CharField('Тип объекта', max_length=20, choices=KIND_CHOICES, blank=True)
    price = models.CharField('Цена', max_length=100, default='По запросу')  # "По запросу" или сумма
    price_usd = models.PositiveIntegerField(
        'Цена, USD',
        null=True,
        blank=True,
        help_text='Число в долларах для фильтра в каталоге. Строковое поле «Цена» — подпись на сайте.',
    )
    rooms = models.PositiveSmallIntegerField('Комнат', default=1)
    area = models.PositiveIntegerField('Площадь, м²', default=0)
    description = models.TextField('Описание', blank=True)
    realtor_name = models.CharField('Имя риэлтора', max_length=120, blank=True)
    realtor_phone = models.CharField('Телефон риэлтора', max_length=25, blank=True)
    image = models.ImageField('Фото', upload_to='listings/', blank=True, null=True)
    image_thumbnail = models.ImageField(
        'Превью для каталога',
        upload_to='listings/catalog/',
        blank=True,
        null=True,
        editable=False,
        help_text='Генерируется автоматически при сохранении основного фото.',
    )
    image_url = models.URLField('Ссылка на фото (если не загружено)', blank=True)
    is_published = models.BooleanField('Опубликовано', default=True)
    telegram_author = models.ForeignKey(
        'tgbot.TelegramEmployee',
        verbose_name='Загрузил (Telegram)',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listings',
    )
    published_at = models.DateTimeField(
        'Дата публикации',
        default=timezone.now,
        db_index=True,
        help_text='По ней сортируется каталог; обновляется при редактировании через Telegram-бота.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Объект'
        verbose_name_plural = 'Объекты каталога'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Числовая цена для фильтра: подставляем из текста «Цены», если не задана вручную
        if self.price_usd is None:
            from .price_infer import infer_price_usd_from_charfield

            inferred = infer_price_usd_from_charfield(self.price)
            if inferred is not None:
                self.price_usd = inferred

        update_fields = kwargs.get('update_fields')
        old_image_name = None
        if self.pk:
            ref = Listing.objects.filter(pk=self.pk).only('image').first()
            if ref and ref.image:
                old_image_name = ref.image.name

        super().save(*args, **kwargs)

        if update_fields is not None and 'image' not in update_fields:
            return

        if not self.image:
            if self.image_thumbnail:
                self.image_thumbnail.delete(save=False)
                self.image_thumbnail = None
                super().save(update_fields=['image_thumbnail'])
            return

        if old_image_name == self.image.name and self.image_thumbnail:
            return

        from .images import thumbnail_jpeg_from_image_field

        try:
            data = thumbnail_jpeg_from_image_field(self.image)
        except Exception:
            return

        base = self.image.name.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        thumb_name = f'{base}_card.jpg'
        if self.image_thumbnail:
            self.image_thumbnail.delete(save=False)
        self.image_thumbnail.save(thumb_name, data, save=False)
        super().save(update_fields=['image_thumbnail'])

    @property
    def image_display_url(self):
        """URL картинки: своя загрузка или image_url."""
        if self.image:
            return self.image.url
        return self.image_url or ''

    @property
    def object_kind_label(self):
        if self.object_kind:
            return self.get_object_kind_display()
        if self.is_land_plot:
            return 'Земельный участок'
        if self.property_category == self.PROPERTY_COMMERCIAL:
            return 'Коммерческое помещение'
        return 'Жилое'

    def media_file_names(self):
        """Имена файлов в хранилище, принадлежащих объекту (основное фото, превью, галерея)."""
        names = [f.name for f in (self.image, self.image_thumbnail) if f]
        names += [img.image.name for img in self.listingimage_set.all() if img.image]
        return names

    def get_gallery_images(self, request):
        """Список URL фото для галлереи: главное + доп. из ListingImage."""
        base = request.scheme + '://' + request.get_host()
        urls = []
        if self.image:
            urls.append(base + self.image.url)
        elif self.image_url:
            urls.append(self.image_url)
        for img in self.listingimage_set.order_by('order'):
            if img.image:
                urls.append(base + img.image.url)
            elif img.image_url:
                urls.append(img.image_url)
        return urls


class ListingImage(models.Model):
    """Дополнительное фото объекта для галлереи."""
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='listingimage_set')
    image = models.ImageField('Фото', upload_to='listings/gallery/', blank=True, null=True)
    image_url = models.URLField('Ссылка на фото', blank=True)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Фото в галлерее'
        verbose_name_plural = 'Фото в галлерее'


class CurrencyRate(models.Model):
    """Курс доллара к сому для показа цены в сомах (одна запись, правится в админке)."""
    usd_to_kgs = models.DecimalField('1 USD = … сом', max_digits=10, decimal_places=4)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Курс доллара'
        verbose_name_plural = 'Курс доллара'

    def __str__(self):
        return f'1 USD = {self.usd_to_kgs.normalize():f} сом'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(USD_KGS_RATE_CACHE_KEY)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        cache.delete(USD_KGS_RATE_CACHE_KEY)
        return result


def get_usd_kgs_rate() -> Decimal | None:
    """Актуальный курс USD→KGS или None, если курс не задан."""
    cached = cache.get(USD_KGS_RATE_CACHE_KEY)
    if cached is not None:
        return cached or None
    row = CurrencyRate.objects.order_by('-updated_at').first()
    rate = row.usd_to_kgs if row and row.usd_to_kgs > 0 else None
    # Пустая строка — маркер «курса нет», чтобы не ходить в БД на каждый запрос.
    cache.set(USD_KGS_RATE_CACHE_KEY, rate or '', 300)
    return rate


def usd_to_kgs(amount_usd: int | None, rate: Decimal | None = None) -> int | None:
    if not amount_usd:
        return None
    rate = rate if rate is not None else get_usd_kgs_rate()
    if not rate:
        return None
    return int((Decimal(amount_usd) * rate).quantize(Decimal('1')))
