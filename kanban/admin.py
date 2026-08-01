from django.contrib import admin
from .models import *

# Simple admin registrations so admin can manage data via Django admin UI
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_active']
    search_fields = ['email', 'username']
    list_filter = ['is_active', 'is_staff']

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']

@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ['title', 'workspace', 'created_by', 'is_archived']
    search_fields = ['title', 'description']
    list_filter = ['is_archived', 'created_at']

@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display = ['title', 'board', 'position']
    search_fields = ['title']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'column', 'priority', 'is_completed', 'assigned_to']
    search_fields = ['title', 'description']
    list_filter = ['priority', 'is_completed', 'is_archived', 'created_at']

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'created_at']
    search_fields = ['content']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['task_title', 'user', 'action', 'created_at']
    search_fields = ['task_title', 'details']
    list_filter = ['action', 'created_at']