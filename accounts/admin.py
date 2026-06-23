from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['user_id', 'email', 'get_full_name', 'role', 'phone', 'class_level', 'is_active']
    list_filter = ['role', 'is_active']
    ordering = ['user_id']
    search_fields = ['user_id', 'first_name', 'last_name', 'email']
    fieldsets = UserAdmin.fieldsets + (
        ('LMS Profile', {'fields': ('role', 'phone', 'class_level')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('LMS Profile', {'fields': ('role', 'phone', 'class_level')}),
    )
