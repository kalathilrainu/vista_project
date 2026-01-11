from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import DeskQueue, RoutingRule
from .services import route_visit, assign_visit_to_desk, transfer_visit, attend_visit
from visit_regn.models import Visit, Purpose, VisitLog
from accounts.models import Office, Desk, User

User = get_user_model()

class RoutingServiceTest(TestCase):
    def setUp(self):
        # Setup Office
        self.office = Office.objects.create(name="Test Office", code="TOFF")
        
        # Setup Desks
        self.desk1 = Desk.objects.create(name="Desk 1", office=self.office)
        self.desk2 = Desk.objects.create(name="Desk 2", office=self.office)
        self.vo_desk = Desk.objects.create(name="VO Desk", office=self.office)
        
        # Setup Purpose
        self.purpose = Purpose.objects.create(name="General Enquiry")
        
        # Setup User
        self.user = User.objects.create_user(username="teststaff", password="password")
        self.user.office = self.office
        self.user.desk = self.desk1
        self.user.save()
        
        # Helper to create visit
        self.visit = Visit.objects.create(
            office=self.office,
            token="TOFF-20231214-001",
            purpose=self.purpose,
            created_by=self.user,
            registration_mode="QUICK"
        )
        
    def test_auto_routing(self):
        # Create a rule
        RoutingRule.objects.create(office=self.office, purpose=self.purpose, default_desk=self.desk1)
        
        # Run routing
        result = route_visit(self.visit)
        
        # Check
        self.assertEqual(result[0], 'ROUTED')
        self.assertEqual(self.visit.current_desk, self.desk1)
        self.assertTrue(DeskQueue.objects.filter(visit=self.visit, desk=self.desk1, is_active=True).exists())
        self.assertEqual(self.visit.status, Visit.Status.ROUTED)
        
    def test_auto_routing_failure_fallback_to_vo_queue(self):
        # No rule exists
        
        # Run routing
        result = route_visit(self.visit)
        
        # Should populate a VO desk? But our find_vo_desk logic looks for 'Village Officer' or 'VO'.
        # Our desk is named "VO Desk". "VO" in "VO Desk" -> match? 
        # Logic: name__icontains='VO'. Yes.
        
        # Check
        self.assertEqual(self.visit.status, Visit.Status.ROUTED) # Because it was assigned to VO desk
        self.assertTrue(DeskQueue.objects.filter(visit=self.visit, desk__name__icontains="VO", is_active=True).exists())
        
    def test_attend_visit(self):
        assign_visit_to_desk(self.visit, self.desk1)
        
        attend_visit(self.visit, self.user)
        
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, Visit.Status.IN_PROGRESS)
        self.assertIsNotNone(self.visit.token_attend_time)
        
    def test_transfer_visit(self):
        assign_visit_to_desk(self.visit, self.desk1)
        attend_visit(self.visit, self.user)
        
        transfer_visit(self.visit, self.desk1, self.desk2, self.user, "Transferring")
        
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.current_desk, self.desk2)
        # Should not be active at Desk 1
        self.assertFalse(DeskQueue.objects.filter(visit=self.visit, desk=self.desk1, is_active=True).exists())
        # Should be active at Desk 2
        self.assertTrue(DeskQueue.objects.filter(visit=self.visit, desk=self.desk2, is_active=True).exists())
        
