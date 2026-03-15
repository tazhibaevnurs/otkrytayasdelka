from rest_framework import serializers
from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    image_display_url = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id',
            'title',
            'address',
            'listing_type',
            'price',
            'rooms',
            'area',
            'description',
            'image_display_url',
            'created_at',
        ]

    def get_image_display_url(self, obj):
        url = obj.image_display_url
        if url and not url.startswith('http'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return url or None
