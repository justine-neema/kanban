from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from .views import *

# Router for REST API endpoints. Each ViewSet registers its routes here
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
    path('', RedirectView.as_view(url='/api/', permanent=False), name='api-root-redirect'),
    path('api/', include(router.urls)),
]