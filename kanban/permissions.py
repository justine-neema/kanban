from rest_framework import permissions
from .models import WorkspaceMember, ActivityLog


def get_workspace(obj):
    """Resolve the Workspace associated with a given model instance.
    Returns None when it can't be determined.
    """
    if obj is None:
        return None
    
    if isinstance(obj, ActivityLog):
        return obj.workspace
    if hasattr(obj, 'owner') and hasattr(obj, 'members'):
        return obj  # obj is a Workspace
    if hasattr(obj, 'workspace'):
        return obj.workspace  # Board
    if hasattr(obj, 'board'):
        return obj.board.workspace  # Column
    if hasattr(obj, 'column'):
        return obj.column.board.workspace  # Task
    if hasattr(obj, 'task'):
        return obj.task.column.board.workspace  # TaskComment
    return None


def is_workspace_member(user, workspace):
    """Check if user is workspace owner or explicit member.
    Also requires an authenticated user.
    """
    if workspace is None or user is None or not user.is_authenticated:
        return False
    return (user == workspace.owner or
            workspace.members.filter(id=user.id).exists())


def is_workspace_owner(user, workspace):
    """Check if user is workspace owner."""
    if workspace is None or user is None or not user.is_authenticated:
        return False
    return user == workspace.owner


def is_workspace_admin(user, workspace):
    """Check if user is workspace owner or has admin role.
    Admin role is represented in the WorkspaceMember table.
    """
    if workspace is None or user is None or not user.is_authenticated:
        return False
    if user == workspace.owner:
        return True
    return WorkspaceMember.objects.filter(
        workspace=workspace, user=user, role='admin'
    ).exists()


class IsWorkspaceOwnerOrMember(permissions.BasePermission):
    """Allows access if user is workspace owner or member."""
    def has_object_permission(self, request, view, obj):
        workspace = get_workspace(obj)
        return is_workspace_member(request.user, workspace)


class IsWorkspaceOwner(permissions.BasePermission):
    """Allows access only if user is workspace owner."""
    def has_object_permission(self, request, view, obj):
        workspace = get_workspace(obj)
        return is_workspace_owner(request.user, workspace)


class IsWorkspaceOwnerOrAdmin(permissions.BasePermission):
    """Allows access if user is workspace owner or admin."""
    def has_object_permission(self, request, view, obj):
        workspace = get_workspace(obj)
        return is_workspace_admin(request.user, workspace)


class IsCommentOwnerOrAdmin(permissions.BasePermission):
    """Allows access if user is comment owner OR workspace admin/owner."""
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'user'):
            return False
        if obj.user == request.user:
            return True
        workspace = get_workspace(obj)
        return is_workspace_admin(request.user, workspace)


class CanAssignTask(permissions.BasePermission):
    """Allows task assignment only if user is workspace member."""
    def has_object_permission(self, request, view, obj):
        workspace = get_workspace(obj)
        return is_workspace_member(request.user, workspace)


class CanMoveTask(permissions.BasePermission):
    """Allows moving task only if user is workspace member."""
    def has_object_permission(self, request, view, obj):
        workspace = get_workspace(obj)
        return is_workspace_member(request.user, workspace)