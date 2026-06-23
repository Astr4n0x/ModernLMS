from django.contrib import admin
from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'content_node', 'file_type', 'uploaded_at']
    list_filter = ['file_type', 'content_node__course']
