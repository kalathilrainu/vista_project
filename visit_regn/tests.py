from django.test import TestCase, Client
from django.utils import timezone
from .models import Visit, VisitLog, DailyTokenCounter, Purpose
from accounts.models import Office, User
from django.contrib.auth import get_user_model
from django.urls import reverse

class VisitModelTests(TestCase):
    def setUp(self):
        self.office = Office.objects.create(name="Test Office", code="999999")
        self.purpose = Purpose.objects.create(name="General")
        self.user = get_user_model().objects.create_user(username='testuser', password='password')

    def test_token_generation(self):
        token1 = Visit.generate_token(self.office)
        token2 = Visit.generate_token(self.office)
        
        today_str = timezone.localtime().date().strftime('%Y%m%d')
        
        self.assertTrue(token1.endswith('001'))
        self.assertTrue(token2.endswith('002'))
        self.assertIn(today_str, token1)

    def test_create_from_kiosk(self):
        data = {'name': 'John', 'mobile': '1234567890', 'purpose': self.purpose}
        visit = Visit.create_from_kiosk(data, self.office, user=self.user, mode='KIOSK')
        
        self.assertEqual(visit.status, Visit.Status.WAITING)
        self.assertTrue(VisitLog.objects.count() >= 1)
        self.assertEqual(VisitLog.objects.first().action, 'CREATED')

class VisitViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.office = Office.objects.create(name="Test Office", code="050317")
        self.purpose = Purpose.objects.create(name="General")
        self.visitor_user = get_user_model().objects.create(username='VISITOR')
        
    def test_kiosk_home(self):
        url = reverse('visit_regn:kiosk_home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_manual_registration(self):
        url = reverse('visit_regn:manual_register')
        data = {
            'name': 'Jane Doe',
            'mobile': '9876543210',
            'purpose': self.purpose.id
        }
        # Assuming middleware or logic sets current office, or passing param?
        # In views we rely on get_current_office which checks GET or first().
        # We have one office, so it should be picked.
        
        response = self.client.post(url, data)
        # Should redirect to token print
        self.assertEqual(response.status_code, 302)
        
        visit = Visit.objects.last()
        self.assertEqual(visit.name, 'Jane Doe')
        self.assertTrue(visit.token.startswith('050317'))

    def test_quick_register(self):
        url = reverse('visit_regn:quick_register')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        visit = Visit.objects.last()
        self.assertEqual(visit.registration_mode, 'QUICK')
