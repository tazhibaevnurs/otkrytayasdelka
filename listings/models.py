from django.db import models


class Listing(models.Model):
    """Объект недвижимости в каталоге."""
    TYPE_SALE = 'sale'
    TYPE_PURCHASE = 'purchase'
    TYPE_CHOICES = [
        (TYPE_SALE, 'Продажа'),
        (TYPE_PURCHASE, 'Покупка'),
    ]

    title = models.CharField('Название', max_length=255)
    address = models.CharField('Адрес', max_length=255)
    listing_type = models.CharField('Тип', max_length=20, choices=TYPE_CHOICES, default=TYPE_SALE)
    price = models.CharField('Цена', max_length=100, default='По запросу')  # "По запросу" или сумма
    rooms = models.PositiveSmallIntegerField('Комнат', default=1)
    area = models.PositiveIntegerField('Площадь, м²', default=0)
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Фото', upload_to='listings/', blank=True, null=True)
    image_url = models.URLField('Ссылка на фото (если не загружено)', blank=True)
    is_published = models.BooleanField('Опубликовано', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Объект'
        verbose_name_plural = 'Объекты каталога'

    def __str__(self):
        return self.title

    @property
    def image_display_url(self):
        """URL картинки: своя загрузка или image_url."""
        if self.image:
            return self.image.url
        return self.image_url or ''

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
