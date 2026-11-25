from django.db import models


class TelegramEmployee(models.Model):
    """Сотрудник агентства, которому разрешён доступ к Telegram-боту."""
    telegram_id = models.BigIntegerField('Telegram ID', unique=True)
    full_name = models.CharField('Имя сотрудника', max_length=150)
    username = models.CharField('Username в Telegram', max_length=64, blank=True)
    is_active = models.BooleanField('Доступ разрешён', default=True)
    can_manage_all = models.BooleanField(
        'Может управлять всеми объектами',
        default=False,
        help_text='Видит и редактирует объекты всех сотрудников, в том числе загруженные через админку.',
    )
    default_realtor_name = models.CharField('Имя риэлтора по умолчанию', max_length=120, blank=True)
    default_realtor_phone = models.CharField('Телефон риэлтора по умолчанию', max_length=25, blank=True)
    created_at = models.DateTimeField('Добавлен', auto_now_add=True)

    class Meta:
        verbose_name = 'Сотрудник (Telegram-бот)'
        verbose_name_plural = 'Сотрудники (Telegram-бот)'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.telegram_id})'


class BotSession(models.Model):
    """Состояние диалога и незавершённая карточка объекта сотрудника."""
    employee = models.OneToOneField(
        TelegramEmployee,
        on_delete=models.CASCADE,
        related_name='bot_session',
        verbose_name='Сотрудник',
    )
    chat_id = models.BigIntegerField('Chat ID')
    state = models.CharField('Шаг диалога', max_length=40, default='idle')
    draft = models.JSONField('Черновик карточки', default=dict, blank=True)
    context = models.JSONField('Контекст шага', default=dict, blank=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Сессия бота (черновик)'
        verbose_name_plural = 'Сессии бота (черновики)'

    def __str__(self):
        return f'{self.employee.full_name}: {self.state}'


class ListingChangeLog(models.Model):
    """Журнал действий с объектами через бота: кто и когда создал, изменил или удалил."""
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Создание'),
        (ACTION_UPDATE, 'Изменение'),
        (ACTION_DELETE, 'Удаление'),
    ]

    listing = models.ForeignKey(
        'listings.Listing',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_logs',
        verbose_name='Объект',
    )
    listing_public_uuid = models.UUIDField('UUID объекта')
    listing_title = models.CharField('Название объекта', max_length=255)
    employee = models.ForeignKey(
        TelegramEmployee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='change_logs',
        verbose_name='Сотрудник',
    )
    action = models.CharField('Действие', max_length=10, choices=ACTION_CHOICES)
    field = models.CharField('Поле', max_length=50, blank=True)
    old_value = models.TextField('Было', blank=True)
    new_value = models.TextField('Стало', blank=True)
    created_at = models.DateTimeField('Когда', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Изменение объекта'
        verbose_name_plural = 'Журнал изменений объектов'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()}: {self.listing_title}'
