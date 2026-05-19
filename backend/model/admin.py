from django.contrib import admin
from django.utils.html import format_html
from backend.model.models import Category, Video


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'video_count')
    search_fields = ('name',)

    @admin.display(description='Videos')
    def video_count(self, obj):
        return obj.videos.count()


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'duration', 'views_count', 'thumb_preview', 'file_size', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('views_count', 'duration', 'thumb_preview_large', 'created_at', 'updated_at')

    @admin.display(description='Thumbnail')
    def thumb_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.thumbnail.url)
        return '—'

    @admin.display(description='Preview')
    def thumb_preview_large(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="max-height:200px;border-radius:8px;" />', obj.thumbnail.url)
        return 'No thumbnail uploaded'

    @admin.display(description='Size')
    def file_size(self, obj):
        mb = obj.file_size_mb
        return f'{mb} MB' if mb else '—'
