from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'full_name', 'role', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'role']
    search_fields = ['username', 'email', 'full_name']
    ordering = ['-created_at']
