from django.core.management.base import BaseCommand
from accounts.models import User
from cases.models import Case
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))
        
        # Members (workshop representatives)
        members_data = [
            {'username': 'member1', 'email': 'member1@workshop.com', 'workshop_code': 'WS001', 'phone': '555-0101'},
            {'username': 'member2', 'email': 'member2@workshop.com', 'workshop_code': 'WS002', 'phone': '555-0102'},
            {'username': 'member3', 'email': 'member3@workshop.com', 'workshop_code': 'WS003', 'phone': '555-0103'},
        ]
        
        members = []
        for data in members_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'role': 'member',
                    'workshop_code': data['workshop_code'],
                    'phone': data['phone'],
                    'is_active': True,
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created member: {user.username}'))
            members.append(user)
        
        # Technicians
        technicians_data = [
            {'username': 'tech_level1_a', 'email': 'tech1a@advisor.com', 'user_level': 'level_1', 'phone': '555-0201'},
            {'username': 'tech_level1_b', 'email': 'tech1b@advisor.com', 'user_level': 'level_1', 'phone': '555-0202'},
            {'username': 'tech_level2_a', 'email': 'tech2a@advisor.com', 'user_level': 'level_2', 'phone': '555-0301'},
            {'username': 'tech_level2_b', 'email': 'tech2b@advisor.com', 'user_level': 'level_2', 'phone': '555-0302'},
            {'username': 'tech_level3', 'email': 'tech3@advisor.com', 'user_level': 'level_3', 'phone': '555-0401'},
        ]
        
        technicians = []
        for data in technicians_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'role': 'technician',
                    'user_level': data['user_level'],
                    'phone': data['phone'],
                    'is_active': True,
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created technician: {user.username} ({user.user_level})'))
            technicians.append(user)
        
        # Manager
        manager, created = User.objects.get_or_create(
            username='manager1',
            defaults={
                'email': 'manager@advisor.com',
                'role': 'manager',
                'phone': '555-0501',
                'is_active': True,
            }
        )
        if created:
            manager.set_password('password123')
            manager.save()
            self.stdout.write(self.style.SUCCESS(f'Created manager: {manager.username}'))
        
        # Admin
        admin, created = User.objects.get_or_create(
            username='admin1',
            defaults={
                'email': 'admin@advisor.com',
                'role': 'admin',
                'phone': '555-0601',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            admin.set_password('password123')
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin: {admin.username}'))
        
        # Create sample cases
        level1_techs = [t for t in technicians if t.user_level == 'level_1']
        level2_techs = [t for t in technicians if t.user_level == 'level_2']
        
        cases_data = [
            # Submitted (not assigned)
            {
                'external_case_id': 'WS001-2025-001',
                'member': members[0],
                'workshop_code': members[0].workshop_code,
                'employee_first_name': 'Robert',
                'employee_last_name': 'Anderson',
                'client_email': 'robert.anderson@agency.gov',
                'urgency': 'normal',
                'num_reports_requested': 1,
                'status': 'submitted',
                'tier': 'tier_1',
                'notes': 'Standard analysis needed.',
            },
            {
                'external_case_id': 'WS002-2025-001',
                'member': members[1],
                'workshop_code': members[1].workshop_code,
                'employee_first_name': 'Jennifer',
                'employee_last_name': 'Martinez',
                'client_email': 'jennifer.martinez@agency.gov',
                'urgency': 'rush',
                'num_reports_requested': 2,
                'status': 'submitted',
                'tier': 'tier_2',
                'notes': 'Rush request - client retiring next month.',
            },
            
            # Accepted (assigned to Level 1)
            {
                'external_case_id': 'WS001-2025-002',
                'member': members[0],
                'workshop_code': members[0].workshop_code,
                'employee_first_name': 'Michael',
                'employee_last_name': 'Davis',
                'client_email': 'michael.davis@agency.gov',
                'urgency': 'rush',
                'num_reports_requested': 1,
                'status': 'accepted',
                'assigned_to': level1_techs[0] if level1_techs else None,
                'tier': 'tier_1',
                'notes': 'LEO employee with military service.',
            },
            {
                'external_case_id': 'WS003-2025-001',
                'member': members[2],
                'workshop_code': members[2].workshop_code,
                'employee_first_name': 'Sarah',
                'employee_last_name': 'Wilson',
                'client_email': 'sarah.wilson@agency.gov',
                'urgency': 'normal',
                'num_reports_requested': 1,
                'status': 'accepted',
                'assigned_to': level1_techs[1] if len(level1_techs) > 1 else level1_techs[0] if level1_techs else None,
                'tier': 'tier_2',
                'notes': 'CSRS Offset case.',
            },
            
            # Pending review
            {
                'external_case_id': 'WS002-2025-002',
                'member': members[1],
                'workshop_code': members[1].workshop_code,
                'employee_first_name': 'David',
                'employee_last_name': 'Brown',
                'client_email': 'david.brown@agency.gov',
                'urgency': 'normal',
                'num_reports_requested': 1,
                'status': 'pending_review',
                'assigned_to': level1_techs[0] if level1_techs else None,
                'tier': 'tier_1',
                'notes': 'Level 1 analysis complete, awaiting quality review.',
            },
            
            # On hold
            {
                'external_case_id': 'WS001-2025-003',
                'member': members[0],
                'workshop_code': members[0].workshop_code,
                'employee_first_name': 'Emily',
                'employee_last_name': 'Taylor',
                'client_email': 'emily.taylor@agency.gov',
                'urgency': 'normal',
                'num_reports_requested': 1,
                'status': 'hold',
                'assigned_to': level1_techs[1] if len(level1_techs) > 1 else level1_techs[0] if level1_techs else None,
                'tier': 'tier_1',
                'notes': 'Waiting for additional documents.',
            },
            
            # Completed
            {
                'external_case_id': 'WS003-2025-002',
                'member': members[2],
                'workshop_code': members[2].workshop_code,
                'employee_first_name': 'James',
                'employee_last_name': 'Miller',
                'client_email': 'james.miller@agency.gov',
                'urgency': 'normal',
                'num_reports_requested': 1,
                'status': 'completed',
                'assigned_to': level1_techs[0] if level1_techs else None,
                'reviewed_by': level2_techs[0] if level2_techs else None,
                'tier': 'tier_1',
                'notes': 'Completed and delivered.',
            },
        ]
        
        for data in cases_data:
            # Set dates
            date_submitted = timezone.now() - timedelta(days=random.randint(1, 30))
            date_accepted = None
            date_completed = None
            
            if data['status'] in ['accepted', 'pending_review', 'hold', 'completed']:
                date_accepted = date_submitted + timedelta(hours=random.randint(1, 48))
            
            if data['status'] == 'completed':
                date_completed = date_accepted + timedelta(days=random.randint(1, 7))
            
            case, created = Case.objects.get_or_create(
                external_case_id=data['external_case_id'],
                defaults={
                    'member': data['member'],
                    'workshop_code': data['workshop_code'],
                    'employee_first_name': data['employee_first_name'],
                    'employee_last_name': data['employee_last_name'],
                    'client_email': data['client_email'],
                    'urgency': data['urgency'],
                    'num_reports_requested': data['num_reports_requested'],
                    'status': data['status'],
                    'assigned_to': data.get('assigned_to'),
                    'reviewed_by': data.get('reviewed_by'),
                    'tier': data.get('tier', ''),
                    'notes': data.get('notes', ''),
                    'date_accepted': date_accepted,
                    'date_completed': date_completed,
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created case: {case.external_case_id} ({case.get_status_display()})'))
        
        self.stdout.write(self.style.SUCCESS('\n=== Sample Data Complete ==='))
        self.stdout.write(self.style.SUCCESS(f'Members: {len(members)} | Technicians: {len(technicians)} | Cases: {len(cases_data)}'))
        self.stdout.write(self.style.SUCCESS('\n=== Login (password: password123) ==='))
        self.stdout.write(self.style.SUCCESS('Members: member1, member2, member3'))
        self.stdout.write(self.style.SUCCESS('Technicians: tech_level1_a, tech_level1_b, tech_level2_a, tech_level2_b, tech_level3'))
        self.stdout.write(self.style.SUCCESS('Manager: manager1 | Admin: admin1'))
