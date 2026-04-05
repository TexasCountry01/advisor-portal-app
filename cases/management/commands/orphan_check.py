from django.core.management.base import BaseCommand
from cases.models import Case, CaseDocument, CaseReport, CaseNote, CaseMessage
from core.models import AuditLog, StaffNotification
from messaging.models import Conversation, Message, MessageReadStatus
import os


class Command(BaseCommand):
    help = 'Check for orphaned records and files after case deletion'

    def handle(self, *args, **options):
        self.stdout.write('=== CURRENT COUNTS ===')
        self.stdout.write('Cases: %d' % Case.objects.count())
        self.stdout.write('CaseDocuments: %d' % CaseDocument.objects.count())
        self.stdout.write('CaseReports: %d' % CaseReport.objects.count())
        self.stdout.write('CaseNotes: %d' % CaseNote.objects.count())
        self.stdout.write('CaseMessages: %d' % CaseMessage.objects.count())
        self.stdout.write('AuditLog: %d' % AuditLog.objects.count())
        self.stdout.write('StaffNotifications: %d' % StaffNotification.objects.count())
        self.stdout.write('Conversations: %d' % Conversation.objects.count())
        self.stdout.write('Messages: %d' % Message.objects.count())
        self.stdout.write('MessageReadStatus: %d' % MessageReadStatus.objects.count())

        self.stdout.write('')
        self.stdout.write('=== ORPHAN CHECK: DB RECORDS ===')
        case_ids = set(Case.objects.values_list('id', flat=True))

        orphan_docs = CaseDocument.objects.exclude(case_id__in=case_ids)
        self.stdout.write('Orphaned CaseDocuments: %d' % orphan_docs.count())
        for d in orphan_docs[:5]:
            self.stdout.write('  doc_id=%s case_id=%s file=%s' % (d.id, d.case_id, d.file))

        orphan_reports = CaseReport.objects.exclude(case_id__in=case_ids)
        self.stdout.write('Orphaned CaseReports: %d' % orphan_reports.count())
        for r in orphan_reports[:5]:
            self.stdout.write('  report_id=%s case_id=%s file=%s' % (r.id, r.case_id, r.report_file))

        orphan_notes = CaseNote.objects.exclude(case_id__in=case_ids)
        self.stdout.write('Orphaned CaseNotes: %d' % orphan_notes.count())

        orphan_msgs = CaseMessage.objects.exclude(case_id__in=case_ids)
        self.stdout.write('Orphaned CaseMessages: %d' % orphan_msgs.count())

        orphan_notifs = StaffNotification.objects.exclude(case_id__in=case_ids).exclude(case_id__isnull=True)
        self.stdout.write('Orphaned StaffNotifications: %d' % orphan_notifs.count())

        orphan_audit = AuditLog.objects.filter(case_id__isnull=False).exclude(case_id__in=case_ids)
        self.stdout.write('Orphaned AuditLog entries: %d' % orphan_audit.count())

        self.stdout.write('')
        self.stdout.write('=== ORPHAN CHECK: FILES ON DISK ===')
        db_files = set()
        for d in CaseDocument.objects.all():
            if d.file:
                db_files.add(str(d.file))
        for r in CaseReport.objects.all():
            if r.report_file:
                db_files.add(str(r.report_file))

        orphan_files = []
        for root_dir in ['media', 'case_documents']:
            if os.path.exists(root_dir):
                for dp, dn, fns in os.walk(root_dir):
                    for f in fns:
                        if not f.startswith('.'):
                            rel = os.path.join(dp, f)
                            if rel not in db_files:
                                orphan_files.append(rel)

        self.stdout.write('Files on disk not in DB: %d' % len(orphan_files))
        for f in sorted(orphan_files)[:15]:
            self.stdout.write('  %s' % f)
        if len(orphan_files) > 15:
            self.stdout.write('  ... and %d more' % (len(orphan_files) - 15))

        self.stdout.write('')
        self.stdout.write('=== DB REFS TO MISSING FILES ===')
        missing = []
        for d in CaseDocument.objects.all():
            if d.file:
                try:
                    if not os.path.exists(d.file.path):
                        missing.append('CaseDoc id=%s case=%s %s' % (d.id, d.case_id, d.file.name))
                except Exception:
                    pass
        for r in CaseReport.objects.all():
            if r.report_file:
                try:
                    if not os.path.exists(r.report_file.path):
                        missing.append('CaseReport id=%s case=%s %s' % (r.id, r.case_id, r.report_file.name))
                except Exception:
                    pass

        self.stdout.write('DB records with missing files: %d' % len(missing))
        for m in missing[:10]:
            self.stdout.write('  %s' % m)

        self.stdout.write('')
        self.stdout.write('=== DONE ===')
