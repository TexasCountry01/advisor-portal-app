from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from accounts.models import User, MemberDelegate
from cases.models import Case, CaseDocument, CaseReport
from core.models import SystemSettings, BetaFeedback, AuditLog, StaffNotification
from messaging.models import Conversation, Message
import os
import subprocess


class Command(BaseCommand):
    help = 'Comprehensive health check of the ProFeds Report Portal'

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write('  PROFEDS REPORT PORTAL — HEALTH CHECK')
        self.stdout.write('  Generated: %s' % now.strftime('%B %d, %Y at %I:%M %p %Z'))
        self.stdout.write('=' * 70)

        # --- Git Info ---
        self.stdout.write('')
        self.stdout.write('--- DEPLOYMENT ---')
        try:
            commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip()
            commit_msg = subprocess.check_output(['git', 'log', '-1', '--pretty=%s'], text=True).strip()
            commit_date = subprocess.check_output(['git', 'log', '-1', '--pretty=%ci'], text=True).strip()
            self.stdout.write('Commit:       %s' % commit)
            self.stdout.write('Message:      %s' % commit_msg)
            self.stdout.write('Committed:    %s' % commit_date)
        except Exception:
            self.stdout.write('Git info:     unavailable')

        # --- Database ---
        self.stdout.write('')
        self.stdout.write('--- DATABASE ---')
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_engine = connection.settings_dict.get('ENGINE', 'unknown')
            db_name = connection.settings_dict.get('NAME', 'unknown')
            self.stdout.write('Status:       OK')
            self.stdout.write('Engine:       %s' % db_engine.split('.')[-1])
            self.stdout.write('Database:     %s' % db_name)
        except Exception as e:
            self.stdout.write('Status:       ERROR — %s' % e)

        # --- Migrations ---
        self.stdout.write('')
        self.stdout.write('--- MIGRATIONS ---')
        try:
            from django.core.management import call_command
            from io import StringIO
            out = StringIO()
            call_command('showmigrations', '--list', stdout=out)
            output = out.getvalue()
            unapplied = [line.strip() for line in output.splitlines() if '[ ]' in line]
            if unapplied:
                self.stdout.write('Status:       WARNING — %d unapplied' % len(unapplied))
                for m in unapplied[:5]:
                    self.stdout.write('  %s' % m)
            else:
                self.stdout.write('Status:       OK — all migrations applied')
        except Exception as e:
            self.stdout.write('Status:       ERROR — %s' % e)

        # --- Users ---
        self.stdout.write('')
        self.stdout.write('--- USERS ---')
        total_users = User.objects.filter(is_active=True).count()
        members = User.objects.filter(role='member', is_active=True)
        technicians = User.objects.filter(role='technician', is_active=True)
        admins = User.objects.filter(role='administrator', is_active=True)
        managers = User.objects.filter(role='manager', is_active=True)
        self.stdout.write('Total Active:     %d' % total_users)
        self.stdout.write('Members:          %d' % members.count())
        self.stdout.write('Technicians:      %d' % technicians.count())
        self.stdout.write('Managers:         %d' % managers.count())
        self.stdout.write('Administrators:   %d' % admins.count())

        # Workshop codes
        workshop_codes = members.values_list('workshop_code', flat=True).distinct()
        workshop_codes = sorted([w for w in workshop_codes if w])
        self.stdout.write('Workshop Codes:   %d (%s)' % (len(workshop_codes), ', '.join(workshop_codes[:20])))

        # --- Delegates ---
        self.stdout.write('')
        self.stdout.write('--- DELEGATES ---')
        total_assignments = MemberDelegate.objects.count()
        unique_delegates = MemberDelegate.objects.values('delegate').distinct().count()
        members_with_delegates = MemberDelegate.objects.values('member').distinct().count()
        email_enabled = MemberDelegate.objects.filter(email_notifications=True).count()
        portal_enabled = MemberDelegate.objects.filter(portal_notifications=True).count()
        self.stdout.write('Total Assignments:        %d' % total_assignments)
        self.stdout.write('Unique Delegates:         %d' % unique_delegates)
        self.stdout.write('Members with Delegates:   %d' % members_with_delegates)
        self.stdout.write('Email Alerts Enabled:     %d' % email_enabled)
        self.stdout.write('Portal Alerts Enabled:    %d' % portal_enabled)

        # --- Cases ---
        self.stdout.write('')
        self.stdout.write('--- CASES ---')
        all_cases = Case.objects.all()
        non_draft = all_cases.exclude(status='draft')
        self.stdout.write('Total Cases:      %d (excl. drafts: %d)' % (all_cases.count(), non_draft.count()))
        for status in ['draft', 'submitted', 'accepted', 'hold', 'pending_review', 'completed', 'cancelled']:
            count = all_cases.filter(status=status).count()
            if count > 0:
                self.stdout.write('  %-18s %d' % (status.title() + ':', count))
        self.stdout.write('Rush Cases:       %d' % all_cases.filter(urgency='rush').count())
        self.stdout.write('Unassigned:       %d' % non_draft.filter(assigned_to__isnull=True).count())

        # Documents & Reports
        self.stdout.write('')
        self.stdout.write('--- DOCUMENTS & REPORTS ---')
        self.stdout.write('Case Documents:   %d' % CaseDocument.objects.count())
        self.stdout.write('Case Reports:     %d' % CaseReport.objects.count())

        # --- System Settings ---
        self.stdout.write('')
        self.stdout.write('--- SYSTEM SETTINGS ---')
        settings = SystemSettings.get_settings()
        self.stdout.write('Email Notifications:  %s' % ('ON' if settings.email_notifications_enabled else 'OFF'))
        self.stdout.write('Scheduled Releases:   %s' % ('ON' if settings.enable_scheduled_releases else 'OFF'))
        self.stdout.write('Batch Release:        %s' % ('ON' if settings.batch_release_enabled else 'OFF'))
        self.stdout.write('API Integration:      %s' % ('ON' if settings.benefits_software_api_enabled else 'OFF'))
        fb1 = '%s (%s)' % (settings.feedback_email_1, 'ON' if settings.feedback_email_1_enabled else 'OFF') if settings.feedback_email_1 else 'Not set'
        fb2 = '%s (%s)' % (settings.feedback_email_2, 'ON' if settings.feedback_email_2_enabled else 'OFF') if settings.feedback_email_2 else 'Not set'
        self.stdout.write('Feedback Email 1:     %s' % fb1)
        self.stdout.write('Feedback Email 2:     %s' % fb2)
        self.stdout.write('Last Updated:         %s' % (settings.updated_at.strftime('%B %d, %Y') if settings.updated_at else 'Never'))

        # --- Notifications & Messaging ---
        self.stdout.write('')
        self.stdout.write('--- NOTIFICATIONS & MESSAGING ---')
        self.stdout.write('Staff Notifications:  %d (unread: %d)' % (
            StaffNotification.objects.count(),
            StaffNotification.objects.filter(is_read=False).count()
        ))
        self.stdout.write('Conversations:        %d' % Conversation.objects.count())
        self.stdout.write('Messages:             %d' % Message.objects.count())

        # --- Feedback ---
        self.stdout.write('')
        self.stdout.write('--- PORTAL FEEDBACK ---')
        total_feedback = BetaFeedback.objects.count()
        self.stdout.write('Total Submissions:    %d' % total_feedback)
        if total_feedback > 0:
            latest = BetaFeedback.objects.order_by('-created_at').first()
            self.stdout.write('Latest:               %s by %s' % (
                latest.created_at.strftime('%B %d, %Y'),
                latest.user.get_full_name() if latest.user else 'Unknown'
            ))

        # --- Audit Trail ---
        self.stdout.write('')
        self.stdout.write('--- AUDIT TRAIL ---')
        self.stdout.write('Total Log Entries:    %d' % AuditLog.objects.count())
        last_24h = AuditLog.objects.filter(timestamp__gte=now - timezone.timedelta(hours=24)).count()
        self.stdout.write('Last 24 Hours:        %d' % last_24h)

        # --- Disk (Media Files) ---
        self.stdout.write('')
        self.stdout.write('--- STORAGE ---')
        if os.path.exists('media'):
            file_count = 0
            total_size = 0
            for dp, dn, fns in os.walk('media'):
                for f in fns:
                    fp = os.path.join(dp, f)
                    file_count += 1
                    total_size += os.path.getsize(fp)
            size_mb = total_size / (1024 * 1024)
            self.stdout.write('Media Files:      %d files (%.1f MB)' % (file_count, size_mb))

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write('  HEALTH CHECK COMPLETE')
        self.stdout.write('=' * 70)
        self.stdout.write('')
