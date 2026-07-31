from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

# All ViewSets now have queryset attribute, so no basename needed
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='user')
router.register(r'workspaces', WorkspaceViewSet)
router.register(r'boards', BoardViewSet)
router.register(r'columns', ColumnViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'comments', TaskCommentViewSet)
router.register(r'activities', ActivityLogViewSet)
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('api/', include(router.urls)),
]