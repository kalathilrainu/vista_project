from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Office, Desk

User = get_user_model()

class SecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.office = Office.objects.create(name="Test Office", code="TO")
        
        # Create different user types
        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="password",
            role="ADMIN",
            office=self.office
        )
        self.staff_user = User.objects.create_user(
            username="staff_user",
            password="password",
            role="STAFF",
            office=self.office
        )
        self.kiosk_user = User.objects.create_user(
            username="VS_kiosk",
            password="password",
            role="KIOSK",
            office=self.office
        )

    def test_load_desks_security(self):
        """Test that load_desks requires login."""
        url = reverse('ajax_load_desks')
        
        # Unauthenticated access
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200) # Should likely be 302 redirect
        
        # Authenticated access
        self.client.force_login(self.staff_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_management_views_rbac(self):
        """Test that management views are restricted to Admins."""
        protected_urls = [
            reverse('user_list'),
            reverse('staff_list'),
            reverse('office_list'),
            reverse('desk_list'),
            # Add create/update URLs if needed, but list view is sufficient for basic RBAC check
        ]
        
        for url in protected_urls:
            # Test as Staff (Should be denied)
            self.client.force_login(self.staff_user)
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 200)
            # Depending on implementation, it might redirect or return 403
            
            # Test as Kiosk (Should be denied)
            self.client.force_login(self.kiosk_user)
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 200)

            # Test as Admin (Should be allowed)
            self.client.force_login(self.admin_user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
