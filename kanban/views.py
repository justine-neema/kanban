from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken
from django.db.models import Count, Q
from django.utils import timezone
from .models import *
from .serializers import *
from .permissions import *


def log_activity(task, user, action, details):
    """Create an activity log entry."""
    if task:
        ActivityLog.objects.create(
            workspace=task.column.board.workspace,
            task=task,
            task_title=task.title,
            user=user,
            action=action,
            details=details,
        )


def create_default_columns(board):
    """Create standard Kanban columns for a new board."""
    default_columns = ['To Do', 'In Progress', 'Done']
    for idx, title in enumerate(default_columns):
        Column.objects.get_or_create(
            board=board,
            title=title,
            defaults={'position': idx},
        )


# API view classes: each ViewSet groups related endpoints (auth, workspaces,
# boards, columns, tasks, comments, activities, dashboard).

class AuthViewSet(viewsets.GenericViewSet):
    # Handles registration, login, logout and token refresh
    permission_classes = [AllowAny]

    def _auth_response(self, user):
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new user"""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return self._auth_response(user)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """Login user and return JWT tokens"""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            return self._auth_response(user)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Logout user by blacklisting refresh token"""
        access_token = request.data.get('access')
        refresh_token = request.data.get('refresh')
        if not access_token:
            return Response({'error': 'access token required'}, status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def refresh(self, request):
        """Refresh access token"""
        refresh_token = request.data.get('access')
        if not refresh_token:
            return Response({'error': 'access token required'}, status=400)
        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                'access': str(refresh.access_token),
                'message': 'Token refreshed successfully'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)


# User views
class UserViewSet(viewsets.GenericViewSet):
    # Endpoints for the authenticated user's profile and password
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """Get or update current user profile"""
        if request.method == 'GET':
            return Response(UserProfileSerializer(request.user).data)
        
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=400)


# Workspace views
class WorkspaceViewSet(viewsets.ModelViewSet):
    # Manage workspaces: owner-only operations are guarded by permissions
    queryset = Workspace.objects.all()  # Added this
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceOwnerOrMember]

    def get_queryset(self):
        return Workspace.objects.filter(
            Q(owner=self.request.user) | Q(members=self.request.user)
        ).distinct()

    def get_permissions(self):
        if self.action in ['destroy']:
            return [IsAuthenticated(), IsWorkspaceOwner()]
        elif self.action in ['update', 'add_member', 'remove_member']:
            return [IsAuthenticated(), IsWorkspaceOwnerOrAdmin()]
        return [IsAuthenticated(), IsWorkspaceOwnerOrMember()]

    def perform_create(self, serializer):
        workspace = serializer.save(owner=self.request.user)
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.request.user,
            role='admin',
        )

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a member to the workspace"""
        workspace = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'member')

        if role not in ('member', 'admin'):
            return Response({'error': 'Invalid role. Use member or admin.'}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        if user == workspace.owner:
            return Response({'error': 'User is already workspace owner'}, status=400)

        member, created = WorkspaceMember.objects.get_or_create(
            workspace=workspace,
            user=user,
            defaults={'role': role},
        )

        if not created:
            member.role = role
            member.save()
            return Response({'message': 'Member role updated successfully'})

        return Response({'message': 'Member added successfully'})

    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Remove a member from the workspace"""
        workspace = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        if user == workspace.owner:
            return Response({'error': 'Cannot remove workspace owner'}, status=400)

        deleted, _ = WorkspaceMember.objects.filter(workspace=workspace, user=user).delete()
        if deleted:
            return Response({'message': 'Member removed successfully'})
        return Response({'error': 'User is not a member of this workspace'}, status=400)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List all workspace members"""
        workspace = self.get_object()
        members = WorkspaceMember.objects.filter(workspace=workspace)
        serializer = WorkspaceMemberSerializer(members, many=True)
        return Response(serializer.data)


# Board views
class BoardViewSet(viewsets.ModelViewSet):
    # Boards live inside workspaces and can be archived/unarchived
    queryset = Board.objects.all()  
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceOwnerOrMember]

    def get_queryset(self):
        qs = Board.objects.filter(
            workspace__in=Workspace.objects.filter(
                Q(owner=self.request.user) | Q(members=self.request.user)
            )
        )
        workspace_id = self.request.query_params.get('workspace')
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        if self.request.query_params.get('include_archived') != 'true':
            qs = qs.filter(is_archived=False)
        return qs

    def get_permissions(self):
        if self.action in ['destroy']:
            return [IsAuthenticated(), IsWorkspaceOwner()]
        elif self.action in ['update', 'archive', 'unarchive']:
            return [IsAuthenticated(), IsWorkspaceOwnerOrAdmin()]
        return [IsAuthenticated(), IsWorkspaceOwnerOrMember()]

    def perform_create(self, serializer):
        board = serializer.save(created_by=self.request.user)
        create_default_columns(board)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a board"""
        board = self.get_object()
        board.is_archived = True
        board.save()
        Task.objects.filter(column__board=board).update(is_archived=True)
        return Response({'message': 'Board archived successfully'})

    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive a board"""
        board = self.get_object()
        board.is_archived = False
        board.save()
        Task.objects.filter(column__board=board).update(is_archived=False)
        return Response({'message': 'Board unarchived successfully'})


# column views
class ColumnViewSet(viewsets.ModelViewSet):
    # Columns are ordered lanes within a board
    queryset = Column.objects.all()  
    serializer_class = ColumnSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceOwnerOrMember]

    def get_queryset(self):
        queryset = Column.objects.all()
        board_id = self.request.query_params.get('board')
        if board_id:
            queryset = queryset.filter(board_id=board_id)
        return queryset

    def get_permissions(self):
        if self.action in ['destroy']:
            return [IsAuthenticated(), IsWorkspaceOwner()]
        elif self.action in ['update', 'reorder']:
            return [IsAuthenticated(), IsWorkspaceOwnerOrAdmin()]
        return [IsAuthenticated(), IsWorkspaceOwnerOrMember()]

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Reorder a column"""
        column = self.get_object()
        new_position = request.data.get('position')

        if new_position is None:
            return Response({'error': 'position required'}, status=400)

        column.position = new_position
        column.save()
        return Response(ColumnSerializer(column).data)


# Task views
class TaskViewSet(viewsets.ModelViewSet):
    # Tasks support moving, bulk moves, assignment, completion, and search
    queryset = Task.objects.all()  
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceOwnerOrMember]

    def get_queryset(self):
        queryset = Task.objects.filter(
            column__board__workspace__in=Workspace.objects.filter(
                Q(owner=self.request.user) | Q(members=self.request.user)
            )
        )

        if self.request.query_params.get('include_archived') != 'true':
            queryset = queryset.filter(is_archived=False)

        board_id = self.request.query_params.get('board')
        if board_id:
            queryset = queryset.filter(column__board_id=board_id)

        column_id = self.request.query_params.get('column')
        if column_id:
            queryset = queryset.filter(column_id=column_id)

        workspace_id = self.request.query_params.get('workspace')
        if workspace_id:
            queryset = queryset.filter(column__board__workspace_id=workspace_id)

        task_status = self.request.query_params.get('status')
        if task_status == 'completed':
            queryset = queryset.filter(is_completed=True)
        elif task_status == 'pending':
            queryset = queryset.filter(is_completed=False)

        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        due_date = self.request.query_params.get('due_date')
        if due_date == 'overdue':
            queryset = queryset.filter(
                due_date__lt=timezone.now().date(), is_completed=False
            )
        elif due_date == 'today':
            queryset = queryset.filter(due_date=timezone.now().date())

        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsWorkspaceOwnerOrAdmin()]
        elif self.action in ['move', 'bulk_move', 'reorder']:
            return [IsAuthenticated(), CanMoveTask()]
        elif self.action == 'assign':
            return [IsAuthenticated(), CanAssignTask()]
        elif self.action in ['complete', 'uncomplete']:
            return [IsAuthenticated(), IsWorkspaceOwnerOrMember()]
        return [IsAuthenticated(), IsWorkspaceOwnerOrMember()]

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)
        log_activity(task, self.request.user, 'created', f'Created task: {task.title}')

    def perform_update(self, serializer):
        task = serializer.save()
        log_activity(task, self.request.user, 'updated', f'Updated task: {task.title}')

    def perform_destroy(self, instance):
        log_activity(instance, self.request.user, 'deleted', f'Deleted task: {instance.title}')
        instance.delete()

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Move task to another column"""
        task = self.get_object()
        target_column_id = request.data.get('column_id')
        position = request.data.get('position')

        if not target_column_id:
            return Response({'error': 'column_id required'}, status=400)

        try:
            target_column = Column.objects.get(id=target_column_id)
        except Column.DoesNotExist:
            return Response({'error': 'Column not found'}, status=404)

        if target_column.board.workspace_id != task.column.board.workspace_id:
            return Response(
                {'error': 'Cannot move task to a column in a different workspace'},
                status=400,
            )

        old_column = task.column
        task.column = target_column
        if position is not None:
            task.position = position
        task.save()

        log_activity(
            task, request.user, 'moved',
            f'Moved from "{old_column.title}" to "{target_column.title}"',
        )
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Reorder a task"""
        task = self.get_object()
        position = request.data.get('position')

        if position is None:
            return Response({'error': 'position required'}, status=400)

        task.position = position
        task.save()
        log_activity(task, request.user, 'reordered', f'Reordered to position {position}')
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign task to a user"""
        task = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        workspace = task.column.board.workspace
        if not is_workspace_member(user, workspace):
            return Response({'error': 'User is not a member of this workspace'}, status=400)

        task.assigned_to = user
        task.save()
        log_activity(task, request.user, 'assigned', f'Assigned to {user.email}')
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark task as completed"""
        task = self.get_object()
        task.is_completed = True
        task.completed_at = timezone.now()
        task.save()
        log_activity(task, request.user, 'completed', f'Marked as completed: {task.title}')
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def uncomplete(self, request, pk=None):
        """Mark task as incomplete"""
        task = self.get_object()
        task.is_completed = False
        task.completed_at = None
        task.save()
        log_activity(task, request.user, 'uncompleted', f'Marked as incomplete: {task.title}')
        return Response(TaskSerializer(task).data)

    @action(detail=False, methods=['post'])
    def bulk_move(self, request):
        """Move multiple tasks at once"""
        task_ids = request.data.get('task_ids', [])
        target_column_id = request.data.get('column_id')

        if not task_ids or not target_column_id:
            return Response({'error': 'task_ids and column_id required'}, status=400)

        try:
            target_column = Column.objects.get(id=target_column_id)
        except Column.DoesNotExist:
            return Response({'error': 'Column not found'}, status=404)

        target_workspace = target_column.board.workspace
        if not is_workspace_member(request.user, target_workspace):
            return Response({'error': 'You are not a member of the target workspace'}, status=403)

        tasks = self.get_queryset().filter(id__in=task_ids)
        moved_ids = list(tasks.values_list('id', flat=True))
        count = tasks.update(column=target_column)

        for task_id in moved_ids:
            try:
                task = Task.objects.get(id=task_id)
                log_activity(
                    task, request.user, 'bulk_moved',
                    f'Moved to "{target_column.title}"',
                )
            except Task.DoesNotExist:
                pass

        skipped = len(task_ids) - count
        message = f'{count} tasks moved successfully'
        if skipped:
            message += f'; {skipped} task(s) skipped (not found or not accessible)'
        return Response({'message': message})

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search tasks by title or description"""
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'search query required'}, status=400)

        tasks = self.get_queryset().filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = TaskSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)


# Task comment views
class TaskCommentViewSet(viewsets.ModelViewSet):
    # Comments on tasks; admins can remove offensive comments
    queryset = TaskComment.objects.all()  
    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated, IsCommentOwnerOrAdmin]

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        if task_id:
            return TaskComment.objects.filter(task_id=task_id)
        return TaskComment.objects.none()

    def perform_create(self, serializer):
        comment = serializer.save(user=self.request.user)
        log_activity(
            comment.task, self.request.user, 'commented',
            f'Added comment: {comment.content[:50]}...',
        )

    @action(detail=False, methods=['post'])
    def admin_delete_offensive(self, request):
        """Admin endpoint to delete offensive comments"""
        comment_id = request.data.get('comment_id')
        reason = request.data.get('reason', 'Offensive content')

        if not comment_id:
            return Response({'error': 'comment_id required'}, status=400)

        try:
            comment = TaskComment.objects.get(id=comment_id)
        except TaskComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=404)

        workspace = get_workspace(comment)
        if not is_workspace_admin(request.user, workspace):
            return Response(
                {'error': 'You must be an admin of this comment\'s workspace to do that'},
                status=403,
            )

        log_activity(
            comment.task, request.user, 'admin_deleted_offensive_comment',
            f'Admin deleted offensive comment by {comment.user.email}. Reason: {reason}',
        )
        comment.delete()
        return Response({'message': 'Offensive comment deleted successfully'})


# ========== ACTIVITY LOG VIEWS ==========

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    # Read-only access to activity logs for user's workspaces
    queryset = ActivityLog.objects.all()  
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceOwnerOrMember]

    def get_queryset(self):
        user_workspaces = Workspace.objects.filter(
            Q(owner=self.request.user) | Q(members=self.request.user)
        )
        qs = ActivityLog.objects.filter(workspace__in=user_workspaces)

        workspace_id = self.request.query_params.get('workspace')
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)

        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)

        board_id = self.request.query_params.get('board')
        if board_id:
            qs = qs.filter(task__column__board_id=board_id)

        action_filter = self.request.query_params.get('action')
        if action_filter:
            qs = qs.filter(action=action_filter)

        return qs


# Dashboard view

class DashboardViewSet(viewsets.GenericViewSet):
    # Dashboard endpoints for statistics and simple analytics
    permission_classes = [IsAuthenticated, IsWorkspaceOwnerOrMember]

    def _user_workspaces(self, request):
        return Workspace.objects.filter(
            Q(owner=request.user) | Q(members=request.user)
        )

    def _filter_tasks(self, request):
        tasks = Task.objects.filter(
            column__board__workspace__in=self._user_workspaces(request)
        )
        workspace_id = request.query_params.get('workspace')
        if workspace_id:
            tasks = tasks.filter(column__board__workspace_id=workspace_id)
        board_id = request.query_params.get('board')
        if board_id:
            tasks = tasks.filter(column__board_id=board_id)
        return tasks

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics"""
        tasks = self._filter_tasks(request)
        total = tasks.count()
        completed = tasks.filter(is_completed=True).count()
        overdue = tasks.filter(
            due_date__lt=timezone.now().date(), is_completed=False
        ).count()

        priority_breakdown = dict(
            tasks.values('priority').annotate(count=Count('id')).values_list('priority', 'count')
        )

        status_breakdown = {
            'completed': completed,
            'pending': total - completed,
            'overdue': overdue,
        }

        return Response({
            'total_tasks': total,
            'completed_tasks': completed,
            'pending_tasks': total - completed,
            'overdue_tasks': overdue,
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 2),
            'priority_breakdown': priority_breakdown,
            'status_breakdown': status_breakdown,
        })

    @action(detail=False, methods=['get'])
    def activities(self, request):
        """Get recent activities"""
        user_workspaces = self._user_workspaces(request)
        activities = ActivityLog.objects.filter(workspace__in=user_workspaces)

        workspace_id = request.query_params.get('workspace')
        if workspace_id:
            activities = activities.filter(workspace_id=workspace_id)

        activities = activities.order_by('-created_at')[:20]
        serializer = ActivityLogSerializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Task analytics: tasks by column and by assignee"""
        tasks = self._filter_tasks(request)

        by_column = list(
            tasks.values('column__title', 'column__id')
            .annotate(count=Count('id'))
            .order_by('column__id')
        )

        by_assignee = list(
            tasks.filter(assigned_to__isnull=False)
            .values('assigned_to__email', 'assigned_to__id')
            .annotate(count=Count('id'))
        )

        unassigned = tasks.filter(assigned_to__isnull=True).count()

        return Response({
            'tasks_by_column': by_column,
            'tasks_by_assignee': by_assignee,
            'unassigned_tasks': unassigned,
        })