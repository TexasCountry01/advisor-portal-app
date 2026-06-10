"""
Document Export Readiness Audit
================================
Read-only diagnostic command that gathers everything needed to plan and
size the Training Document Package feature (Scenario Search + ZIP Download).

Checks:
  - Storage backend (DigitalOcean Spaces vs local disk)
  - Storage connectivity (can files actually be opened?)
  - Gunicorn / Nginx timeout configuration
  - Document counts, types, and total size
  - FederalFactFinder data completeness
  - Per-scenario case counts for all manager-requested criteria
  - "Unicorn" case count (all criteria in one person)
  - ZIP size and timing estimates

Usage:
  # Run locally
  python manage.py doc_export_audit

  # Run on PROD via SSH (use run_doc_export_audit.ps1 instead)
  ssh dev@104.248.126.74 "cd /var/www/advisor-portal && venv/bin/python manage.py doc_export_audit"
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from django.db.models import Q, Sum, Count
from django.conf import settings
from cases.models import Case, CaseDocument
from cases.models_fact_finder import FederalFactFinder
import subprocess
import os


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_bytes(num_bytes):
    """Human-readable file size."""
    if num_bytes is None:
        return 'unknown'
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(num_bytes) < 1024.0:
            return f'{num_bytes:.1f} {unit}'
        num_bytes /= 1024.0
    return f'{num_bytes:.1f} TB'


def _grep_file(path, keyword):
    """Safely grep a server config file. Returns matching lines or an error string."""
    try:
        result = subprocess.run(
            ['grep', '-i', keyword, path],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return lines if lines else ['(not found in file)']
    except FileNotFoundError:
        return [f'(file not found: {path})']
    except Exception as e:
        return [f'(error: {e})']


def _read_file_safe(path):
    """Read a config file, return lines or error string."""
    try:
        with open(path, 'r') as f:
            return [l.rstrip() for l in f.readlines()]
    except Exception as e:
        return [f'(cannot read: {e})']


def _test_storage_access(sample_size=5):
    """
    Try to open the first N CaseDocument files via Django's storage backend.
    Returns (accessible_count, total_tested, first_error).
    Works for both local disk and DigitalOcean Spaces.
    """
    docs = CaseDocument.objects.filter(file__isnull=False).exclude(file='').order_by('-uploaded_at')[:sample_size]
    accessible = 0
    first_error = None
    total_tested = 0

    for doc in docs:
        total_tested += 1
        try:
            f = doc.file.open('rb')
            f.read(256)   # Read first 256 bytes — enough to confirm the file is real
            f.close()
            accessible += 1
        except Exception as e:
            if first_error is None:
                first_error = f'{doc.original_filename}: {e}'

    return accessible, total_tested, first_error


# ──────────────────────────────────────────────────────────────────────────────
# Command
# ──────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Read-only audit to assess readiness for Training Document Package feature'

    def handle(self, *args, **options):
        now = timezone.now()
        W = self.stdout.write

        W('')
        W('=' * 72)
        W('  PROFEDS PORTAL — TRAINING DOCUMENT EXPORT READINESS AUDIT')
        W('  Generated: %s' % now.strftime('%B %d, %Y at %I:%M %p %Z'))
        W('=' * 72)

        # ── 1. STORAGE BACKEND ─────────────────────────────────────────────────
        W('')
        W('─' * 72)
        W('  1. STORAGE BACKEND')
        W('─' * 72)

        use_spaces = getattr(settings, 'USE_SPACES', False)
        storage_class = settings.DEFAULT_FILE_STORAGE if hasattr(settings, 'DEFAULT_FILE_STORAGE') else 'django.core.files.storage.FileSystemStorage'

        if use_spaces:
            W('Backend:          DigitalOcean Spaces (S3Boto3Storage)')
            W('USE_SPACES:       True')
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'not set')
            endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', 'not set')
            custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', '')
            location = getattr(settings, 'AWS_LOCATION', 'media')
            W('Bucket:           %s' % bucket)
            W('Endpoint:         %s' % endpoint)
            W('Custom Domain:    %s' % (custom_domain if custom_domain else '(none — using endpoint)'))
            W('Media Location:   %s/' % location)
            W('')
            W('  ⚠  FILES ARE IN SPACES — NOT ON LOCAL DISK.')
            W('     ZIP generation will fetch each file from Spaces over the network.')
            W('     Each file = one HTTP round-trip from the app server to Spaces.')
        else:
            W('Backend:          Local filesystem (FileSystemStorage)')
            W('USE_SPACES:       False')
            media_root = getattr(settings, 'MEDIA_ROOT', 'not configured')
            W('MEDIA_ROOT:       %s' % media_root)
            W('')
            if str(media_root) != 'not configured' and os.path.exists(str(media_root)):
                W('  ✓  MEDIA_ROOT exists on this server.')
            else:
                W('  ⚠  MEDIA_ROOT does not exist on this server — local storage not usable.')

        # ── 2. STORAGE CONNECTIVITY TEST ──────────────────────────────────────
        W('')
        W('─' * 72)
        W('  2. STORAGE CONNECTIVITY TEST  (read-only — opens first few bytes)')
        W('─' * 72)

        total_docs = CaseDocument.objects.filter(file__isnull=False).exclude(file='').count()
        W('Total documents with file path set:  %d' % total_docs)

        if total_docs == 0:
            W('  ⚠  No documents to test.')
        else:
            W('Testing access on 5 most-recently-uploaded files...')
            accessible, tested, first_error = _test_storage_access(sample_size=5)
            W('  Accessible:  %d / %d' % (accessible, tested))
            if first_error:
                W('  First error: %s' % first_error)
                W('  ⚠  SOME FILES ARE INACCESSIBLE. ZIP generation will skip them.')
            else:
                W('  ✓  All sampled files opened successfully.')

        # ── 3. SERVER TIMEOUT CONFIGURATION ───────────────────────────────────
        W('')
        W('─' * 72)
        W('  3. SERVER TIMEOUT CONFIGURATION')
        W('─' * 72)

        # Gunicorn systemd service
        gunicorn_path = '/etc/systemd/system/gunicorn.service'
        W('Gunicorn service file: %s' % gunicorn_path)
        timeout_lines = _grep_file(gunicorn_path, 'timeout')
        workers_lines = _grep_file(gunicorn_path, 'worker')
        for line in timeout_lines:
            W('  timeout setting:  %s' % line)
        for line in workers_lines:
            W('  worker setting:   %s' % line)

        # Nginx — look for proxy_read_timeout in site configs
        W('')
        nginx_sites = [
            '/etc/nginx/sites-available/advisor-portal',
            '/etc/nginx/sites-available/default',
            '/etc/nginx/nginx.conf',
        ]
        for nginx_path in nginx_sites:
            if os.path.exists(nginx_path):
                W('Nginx config: %s' % nginx_path)
                for kw in ['proxy_read_timeout', 'proxy_connect_timeout', 'keepalive_timeout', 'client_max_body']:
                    lines = _grep_file(nginx_path, kw)
                    for line in lines:
                        W('  %-30s %s' % (kw + ':', line))
                break
        else:
            W('Nginx config: (no standard config file found — checked %d paths)' % len(nginx_sites))

        W('')
        W('  INTERPRETATION:')
        W('  - Gunicorn timeout = max seconds a single request can run before being killed.')
        W('  - proxy_read_timeout = Nginx gives up waiting for Gunicorn after this many seconds.')
        W('  - ZIP generation streams incrementally, so Nginx timeout is less critical,')
        W('    but Gunicorn timeout is a hard ceiling on total ZIP build time.')

        # ── 4. DOCUMENT OVERVIEW ───────────────────────────────────────────────
        W('')
        W('─' * 72)
        W('  4. DOCUMENT OVERVIEW')
        W('─' * 72)

        total_all = CaseDocument.objects.count()
        W('Total CaseDocument records:     %d' % total_all)
        W('')

        type_summary = CaseDocument.objects.values('document_type').annotate(
            count=Count('id'),
            total_size=Sum('file_size')
        ).order_by('-count')

        W('  %-20s  %-10s  %s' % ('Type', 'Count', 'Total Size'))
        W('  ' + '-' * 50)
        grand_size = 0
        for row in type_summary:
            size = row['total_size'] or 0
            grand_size += size
            W('  %-20s  %-10d  %s' % (row['document_type'], row['count'], _fmt_bytes(size)))
        W('  ' + '-' * 50)
        W('  %-20s  %-10d  %s' % ('TOTAL', total_all, _fmt_bytes(grand_size)))

        # Member-submitted documents only (fact_finder + supporting)
        W('')
        member_docs = CaseDocument.objects.filter(
            document_type__in=['fact_finder', 'supporting']
        )
        member_count = member_docs.count()
        member_size_agg = member_docs.aggregate(total=Sum('file_size'))
        member_size = member_size_agg['total'] or 0
        avg_size = (member_size / member_count) if member_count > 0 else 0
        W('Member-submitted docs (fact_finder + supporting):')
        W('  Count:        %d' % member_count)
        W('  Total size:   %s' % _fmt_bytes(member_size))
        W('  Average size: %s per document' % _fmt_bytes(avg_size))

        # Cases with 0 documents
        cases_no_docs = Case.objects.exclude(
            id__in=CaseDocument.objects.values('case_id')
        ).exclude(status='draft').count()
        W('')
        W('Submitted cases with zero documents: %d' % cases_no_docs)
        if cases_no_docs > 0:
            W('  ⚠  These cases exist in the DB but have no files in storage.')

        # ── 5. FFF DATA COMPLETENESS ────────────────────────────────────────────
        W('')
        W('─' * 72)
        W('  5. FEDERAL FACT FINDER DATA COMPLETENESS')
        W('─' * 72)

        total_cases = Case.objects.exclude(status='draft').count()
        total_fff = FederalFactFinder.objects.count()
        fff_with_ret_system = FederalFactFinder.objects.exclude(retirement_system='').count()
        fff_with_emp_type = FederalFactFinder.objects.exclude(employee_type='').count()
        fff_with_tsp = FederalFactFinder.objects.filter(
            Q(tsp_roth_contribution__isnull=False) | Q(tsp_traditional_contribution__isnull=False)
        ).count()
        fff_with_fegli = FederalFactFinder.objects.filter(
            fegli_premium_line1__isnull=False, fegli_premium_line1__gt=0
        ).count()

        W('Submitted cases:                        %d' % total_cases)
        W('FFF records in DB:                      %d' % total_fff)
        pct = (total_fff / total_cases * 100) if total_cases else 0
        W('FFF coverage:                           %.0f%%' % pct)
        W('')
        W('  Of %d FFF records:' % total_fff)
        W('  %-42s %d (%.0f%%)' % ('Have retirement_system filled in:', fff_with_ret_system, (fff_with_ret_system/total_fff*100) if total_fff else 0))
        W('  %-42s %d (%.0f%%)' % ('Have employee_type filled in:', fff_with_emp_type, (fff_with_emp_type/total_fff*100) if total_fff else 0))
        W('  %-42s %d (%.0f%%)' % ('Have TSP contribution data:', fff_with_tsp, (fff_with_tsp/total_fff*100) if total_fff else 0))
        W('  %-42s %d (%.0f%%)' % ('Have FEGLI premium data:', fff_with_fegli, (fff_with_fegli/total_fff*100) if total_fff else 0))

        if pct < 50:
            W('')
            W('  ⚠  LESS THAN 50%% OF CASES HAVE FFF RECORDS.')
            W('     Scenario search results will be limited.')
            W('     Consider whether the ZIP-from-file-browser approach is more useful right now.')
        elif pct < 80:
            W('')
            W('  ↗  FFF coverage is partial. Search results will be useful but not complete.')
        else:
            W('')
            W('  ✓  Good FFF coverage. Scenario search should return meaningful results.')

        # ── 6. SCENARIO COVERAGE (per-criteria counts) ─────────────────────────
        W('')
        W('─' * 72)
        W('  6. SCENARIO COVERAGE  (matching FFF records for each criteria)')
        W('─' * 72)
        W('  Note: counts are FFF records, not total portal users.')
        W('')

        fff = FederalFactFinder.objects.all()

        scenarios = [
            # (label, queryset filter kwargs or Q object)
            ('── RETIREMENT SYSTEM ──────────────────────────────────────────────', None),
            ('FERS',                         fff.filter(retirement_system='FERS')),
            ('CSRS',                         fff.filter(retirement_system='CSRS')),
            ('CSRS Offset',                  fff.filter(retirement_system='CSRS_OFFSET')),
            ('FERS Transfer',                fff.filter(retirement_system='FERS_TRANSFER')),
            ('── EMPLOYEE TYPE ──────────────────────────────────────────────────', None),
            ('Regular',                      fff.filter(employee_type='REGULAR')),
            ('Law Enforcement (LEO)',         fff.filter(employee_type='LEO')),
            ('CBPO',                         fff.filter(employee_type='CBPO')),
            ('Postal',                       fff.filter(employee_type='POSTAL')),
            ('── MARITAL STATUS ─────────────────────────────────────────────────', None),
            ('Married (has spouse name)',     fff.exclude(spouse_name='').filter(spouse_name__isnull=False)),
            ('── FEGLI ──────────────────────────────────────────────────────────', None),
            ('Has FEGLI Basic (line 1 > 0)', fff.filter(fegli_premium_line1__gt=0)),
            ('Has FEGLI Option A (line 2)',   fff.filter(fegli_premium_line2__gt=0)),
            ('Has FEGLI Option B (line 3)',   fff.filter(fegli_premium_line3__gt=0)),
            ('Has FEGLI Option C (line 4)',   fff.filter(fegli_premium_line4__gt=0)),
            ('Has FEGLI Basic + A + B + C',  fff.filter(fegli_premium_line1__gt=0, fegli_premium_line2__gt=0, fegli_premium_line3__gt=0, fegli_premium_line4__gt=0)),
            ('── HEALTH BENEFITS ────────────────────────────────────────────────', None),
            ('Dental only premium',          fff.filter(fehb_dental_premium__gt=0)),
            ('Vision only premium',          fff.filter(fehb_vision_premium__gt=0)),
            ('Dental/Vision combo plan',     fff.filter(fehb_dental_vision_premium__gt=0)),
            ('── TSP ────────────────────────────────────────────────────────────', None),
            ('TSP Roth contributions',       fff.filter(tsp_roth_contribution__gt=0)),
            ('TSP Traditional contributions',fff.filter(tsp_traditional_contribution__gt=0)),
            ('TSP Roth AND Traditional',     fff.filter(tsp_roth_contribution__gt=0, tsp_traditional_contribution__gt=0)),
            ('TSP General Purpose Loan',     fff.filter(tsp_general_loan_balance__gt=0)),
            ('TSP Residential Loan',         fff.filter(tsp_residential_loan_balance__gt=0)),
            ('TSP Both Loans',               fff.filter(tsp_general_loan_balance__gt=0, tsp_residential_loan_balance__gt=0)),
            ('── LEAVE BALANCES ─────────────────────────────────────────────────', None),
            ('Annual Leave > 0 hours',       fff.filter(annual_leave_hours__gt=0)),
            ('Sick Leave > 0 hours',         fff.filter(sick_leave_hours__gt=0)),
            ('Both Annual AND Sick > 0',     fff.filter(annual_leave_hours__gt=0, sick_leave_hours__gt=0)),
        ]

        for label, qs in scenarios:
            if qs is None:
                # Section header
                W('')
                W('  %s' % label)
            else:
                count = qs.count()
                bar = '█' * min(count, 40)
                W('  %-40s  %3d  %s' % (label, count, bar))

        # TSP Catch-up (age 50+) — inferred from employee_dob
        W('')
        W('  ── CATCH-UP ELIGIBLE (age 50+, inferred from DOB) ─────────────────')
        try:
            from datetime import date
            cutoff_date = date(now.year - 50, now.month, now.day)
            catchup_count = FederalFactFinder.objects.filter(
                employee_dob__lte=cutoff_date
            ).count()
            no_dob_count = FederalFactFinder.objects.filter(employee_dob__isnull=True).count()
            W('  %-40s  %3d' % ('Age 50+ (catch-up eligible)', catchup_count))
            W('  %-40s  %3d  ← DOB unknown, cannot determine' % ('No DOB recorded', no_dob_count))
        except Exception as e:
            W('  (error computing age: %s)' % e)

        # ── 7. UNICORN CASE ─────────────────────────────────────────────────────
        W('')
        W('─' * 72)
        W('  7. "UNICORN" CASE  (one person matching ALL primary criteria)')
        W('─' * 72)
        W('  Criteria: FERS + Regular + Married + FEGLI Basic+A+B+C +')
        W('            Dental + Vision + TSP Roth + TSP Traditional +')
        W('            Annual Leave > 0 + Sick Leave > 0 +')
        W('            TSP Residential Loan + TSP General Loan')
        W('')

        try:
            unicorn_qs = FederalFactFinder.objects.filter(
                retirement_system='FERS',
                employee_type='REGULAR',
                fegli_premium_line1__gt=0,
                fegli_premium_line2__gt=0,
                fegli_premium_line3__gt=0,
                fegli_premium_line4__gt=0,
                fehb_dental_premium__gt=0,
                fehb_vision_premium__gt=0,
                tsp_roth_contribution__gt=0,
                tsp_traditional_contribution__gt=0,
                annual_leave_hours__gt=0,
                sick_leave_hours__gt=0,
                tsp_residential_loan_balance__gt=0,
                tsp_general_loan_balance__gt=0,
            ).exclude(spouse_name='').filter(spouse_name__isnull=False)

            unicorn_count = unicorn_qs.count()
            W('  Exact unicorn matches: %d' % unicorn_count)

            if unicorn_count == 0:
                W('')
                W('  No exact unicorn. Checking relaxed versions...')
                # Drop loans requirement
                relaxed_no_loans = FederalFactFinder.objects.filter(
                    retirement_system='FERS',
                    employee_type='REGULAR',
                    fegli_premium_line1__gt=0,
                    tsp_roth_contribution__gt=0,
                    tsp_traditional_contribution__gt=0,
                    annual_leave_hours__gt=0,
                    sick_leave_hours__gt=0,
                ).exclude(spouse_name='').filter(spouse_name__isnull=False)
                W('  FERS+Regular+Married+FEGLI+TSP+Leave (no loan req): %d' % relaxed_no_loans.count())

                # Drop FEGLI options requirement
                relaxed_no_fegli_opts = FederalFactFinder.objects.filter(
                    retirement_system='FERS',
                    employee_type='REGULAR',
                    fegli_premium_line1__gt=0,
                    tsp_roth_contribution__gt=0,
                    annual_leave_hours__gt=0,
                ).exclude(spouse_name='').filter(spouse_name__isnull=False)
                W('  FERS+Regular+Married+FEGLI Basic+TSP Roth+Leave:    %d' % relaxed_no_fegli_opts.count())

                # Just FERS + married
                relaxed_fers_married = FederalFactFinder.objects.filter(
                    retirement_system='FERS',
                ).exclude(spouse_name='').filter(spouse_name__isnull=False)
                W('  FERS + Married only:                                 %d' % relaxed_fers_married.count())
            else:
                W('')
                for fff_rec in unicorn_qs[:10]:
                    W('  → Case: %s  |  %s' % (
                        fff_rec.case.external_case_id,
                        fff_rec.employee_name or '(name not filled)'
                    ))
                if unicorn_count > 10:
                    W('  ... and %d more' % (unicorn_count - 10))
        except Exception as e:
            W('  (error running unicorn query: %s)' % e)

        # ── 8. ZIP SIZE & TIMING ESTIMATES ────────────────────────────────────
        W('')
        W('─' * 72)
        W('  8. ZIP SIZE & TIMING ESTIMATES')
        W('─' * 72)
        W('')
        W('  Based on member-submitted documents (fact_finder + supporting):')
        W('  Average document size: %s' % _fmt_bytes(avg_size))
        W('')

        scenarios_zip = [
            ('5 cases, avg 3 docs each',  15),
            ('10 cases, avg 3 docs each', 30),
            ('25 cases, avg 3 docs each', 75),
            ('10 cases, avg 6 docs each', 60),
            ('25 cases, avg 6 docs each', 150),
        ]

        W('  %-32s  %-14s  %s' % ('Scenario', 'Est. ZIP size', 'Est. build time (Spaces)'))
        W('  ' + '-' * 68)
        for desc, num_docs in scenarios_zip:
            est_size = num_docs * avg_size
            # Assume ~1.5 sec per file from Spaces + 0.5s overhead per case
            num_cases = num_docs // 3  # rough
            est_secs = (num_docs * 1.5)
            W('  %-32s  %-14s  ~%.0f seconds' % (desc, _fmt_bytes(est_size), est_secs))

        W('')
        W('  ⚑  Gunicorn will kill the request if it exceeds its timeout.')
        W('     See Section 3 above for current timeout settings.')
        W('     Recommendation: cap downloads at 25 cases or show estimated size first.')

        if use_spaces:
            W('')
            W('  SPACES TRANSFER NOTE:')
            W('  Each file requires a network round-trip from the app server to Spaces.')
            W('  If the app server and Spaces bucket are in the same datacenter (e.g., both')
            W('  NYC3), transfers are fast (~50–200ms each) and free of bandwidth charges.')
            W('  If in different datacenters, transfers will be slower and may incur cost.')
            dc_endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', '')
            W('  Current Spaces endpoint: %s' % (dc_endpoint or 'not configured'))

        # ── 9. SUMMARY & RECOMMENDATIONS ──────────────────────────────────────
        W('')
        W('─' * 72)
        W('  9. SUMMARY & RECOMMENDATIONS')
        W('─' * 72)
        W('')

        issues = []
        recommendations = []

        if not use_spaces and total_docs > 0:
            recommendations.append('Files are on local disk — ZIP generation is straightforward and fast.')
        if use_spaces:
            recommendations.append('Files are in Spaces — use StreamingHttpResponse to avoid Gunicorn memory pressure.')

        if pct < 50:
            issues.append('Low FFF coverage (%.0f%%) — scenario search may return sparse results.' % pct)
            recommendations.append('Consider auditing which advisors have incomplete FFF data.')
        
        if fff_with_ret_system < total_fff * 0.7:
            issues.append('Many FFF records missing retirement_system — key filter field.')

        if issues:
            W('  ISSUES:')
            for i in issues:
                W('    ⚠  %s' % i)
            W('')

        if recommendations:
            W('  NOTES:')
            for r in recommendations:
                W('    →  %s' % r)
            W('')

        W('  OPEN QUESTIONS TO RESOLVE BEFORE BUILDING:')
        W('    1. Access control: Manager-only, or also Administrators?')
        W('    2. ZIP scope: All doc types, or member-submitted only (fact_finder + supporting)?')
        W('    3. AND vs OR search logic (must match ALL checked criteria, or ANY)?')
        W('    4. Hard cap on cases per download — recommended: 25 cases / ~150 docs.')
        W('    5. Confirm Spaces datacenter matches app server datacenter (see Section 8).')

        W('')
        W('─' * 72)
        W('  Audit complete. This command made no changes to the database or storage.')
        W('─' * 72)
        W('')
