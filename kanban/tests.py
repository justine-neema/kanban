from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import *

User = get_user_model()


class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'Test123!',
            'password2': 'Test123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_register(self):
        response = self.client.post('/api/auth/register/', self.user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_login(self):
        # Register first
        self.client.post('/api/auth/register/', self.user_data)
        
        # Then login
        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'Test123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)