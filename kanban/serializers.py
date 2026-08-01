from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import *
from .permissions import is_workspace_member


# Auth and main app objects

class UserSerializer(serializers.ModelSerializer):
    # Basic public-facing user data
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'bio', 'avatar']


class UserProfileSerializer(serializers.ModelSerializer):
    # Serializer for a user's own profile (read/write only)
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'bio', 'avatar']
        read_only_fields = ['id', 'email']


class RegisterSerializer(serializers.ModelSerializer):
    # Handles user registration and password confirmation
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'password2', 'first_name', 'last_name']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    # Simple email/password login that returns a user on success
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid email or password')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            return user
        
        raise serializers.ValidationError('Must include "email" and "password"')


class ChangePasswordSerializer(serializers.Serializer):
    # Change password endpoint validation
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect')
        return value


# Workspace validation

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    # Represents a user's membership info inside a workspace
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = WorkspaceMember
        fields = ['id', 'workspace', 'user', 'role', 'joined_at']
        read_only_fields = ['joined_at']


class WorkspaceSerializer(serializers.ModelSerializer):
    # Workspace with member list and a small computed member_count
    members = WorkspaceMemberSerializer(source='workspacemember_set', many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'owner', 'members', 'member_count', 'created_at', 'updated_at']
        read_only_fields = ['owner', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        return obj.members.count()


class BoardSerializer(serializers.ModelSerializer):
    # Board serializer ensures workspace belongs to requester on create
    class Meta:
        model = Board
        fields = ['id', 'workspace', 'title', 'description', 'is_archived', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        request = self.context.get('request')
        workspace = attrs.get('workspace') or getattr(self.instance, 'workspace', None)
        if request and workspace is not None and not is_workspace_member(request.user, workspace):
            raise serializers.ValidationError({'workspace': 'You are not a member of this workspace'})
        return attrs


class ColumnSerializer(serializers.ModelSerializer):
    # Column serializer includes a task_count helper for UI
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Column
        fields = ['id', 'board', 'title', 'position', 'task_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_task_count(self, obj):
        return obj.tasks.filter(is_archived=False).count()
    
    def validate(self, attrs):
        request = self.context.get('request')
        board = attrs.get('board') or getattr(self.instance, 'board', None)
        if request and board is not None and not is_workspace_member(request.user, board.workspace):
            raise serializers.ValidationError({'board': 'You are not a member of this board\'s workspace'})
        return attrs


class TaskSerializer(serializers.ModelSerializer):
    # Task serializer exposes some helpful email fields and count
    created_by_email = serializers.SerializerMethodField()
    assigned_to_email = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['id', 'column', 'title', 'description', 'priority', 'due_date',
                  'position', 'is_completed', 'is_archived', 'completed_at',
                  'created_by', 'created_by_email', 'assigned_to', 'assigned_to_email',
                  'comment_count', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'completed_at', 'created_at', 'updated_at']
    
    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None
    
    def get_assigned_to_email(self, obj):
        return obj.assigned_to.email if obj.assigned_to else None
    
    def get_comment_count(self, obj):
        return obj.comments.count()
    
    def validate(self, attrs):
        request = self.context.get('request')
        column = attrs.get('column') or getattr(self.instance, 'column', None)
        workspace = column.board.workspace if column else None
        
        if request and workspace is not None and not is_workspace_member(request.user, workspace):
            raise serializers.ValidationError({'column': 'You are not a member of this column\'s workspace'})
        
        assigned_to = attrs.get('assigned_to')
        if assigned_to is not None and workspace is not None and not is_workspace_member(assigned_to, workspace):
            raise serializers.ValidationError({'assigned_to': 'User is not a member of this workspace'})
        
        return attrs


class TaskCommentSerializer(serializers.ModelSerializer):
    # Comments carry their author and are checked against workspace membership
    user = UserSerializer(read_only=True)
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'user', 'user_email', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']
    
    def get_user_email(self, obj):
        return obj.user.email
    
    def validate(self, attrs):
        request = self.context.get('request')
        task = attrs.get('task') or getattr(self.instance, 'task', None)
        workspace = task.column.board.workspace if task else None
        if request and workspace is not None and not is_workspace_member(request.user, workspace):
            raise serializers.ValidationError({'task': 'You are not a member of this task\'s workspace'})
        return attrs


class ActivityLogSerializer(serializers.ModelSerializer):
    # Lightweight activity serializer used for feeds and dashboard
    user = UserSerializer(read_only=True)
    user_email = serializers.SerializerMethodField()
    task_title = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'workspace', 'task', 'task_title', 'user', 'user_email', 'action', 'details', 'created_at']
        read_only_fields = ['created_at']
    
    def get_user_email(self, obj):
        return obj.user.email
    
    def get_task_title(self, obj):
        return obj.task.title if obj.task else obj.task_title