from rest_framework import serializers

from .catalog_images import listing_card_image_url

from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    image_display_url = serializers.SerializerMethodField()
    image_catalog_url = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'public_uuid',
            'title',
            'address',
            'listing_type',
            'property_category',
            'is_land_plot',
            'price',
            'rooms',
            'area',
            'description',
            'realtor_name',
            'realtor_phone',
            'image_display_url',
            'image_catalog_url',
            'created_at',
        ]

    def get_image_display_url(self, obj):
        url = obj.image_display_url
        if url and not url.startswith('http'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return url or None

    def get_image_catalog_url(self, obj):
        """Лёгкий URL для сеток (превью ≤720px при загрузке в медиа)."""
        path = listing_card_image_url(obj)
        if path.startswith('http'):
            return path
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(path)
        return path
