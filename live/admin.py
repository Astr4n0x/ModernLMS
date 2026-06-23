from django.contrib import admin
from .models import LiveSession, LiveComment


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ['content_node', 'is_live', 'started_at', 'ended_at', 'viewer_count']
    list_filter = ['is_live']


@admin.register(LiveComment)
class LiveCommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'session', 'text', 'timestamp']
    list_filter = ['session']
