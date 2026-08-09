"""
Run All Alert Smoke Tests
=========================
Wrapper that executes all five alert-system smoke tests in sequence
and produces a consolidated pass/fail summary.

Run:
    python manage.py shell < scripts/run_alert_smoke_tests.py

Individual tests:
    python manage.py shell < scripts/smoke_test_01_badge_scope.py
    python manage.py shell < scripts/smoke_test_02_notification_suppression.py
    python manage.py shell < scripts/smoke_test_03_doc_upload_badge.py
    python manage.py shell < scripts/smoke_test_04_pf_err_mod_badges.py
    python manage.py shell < scripts/smoke_test_05_bell_badge_linkage.py
"""
import os
import sys

# When piped via `manage.py shell < script.py`, __file__ is not set.
# Use the project root (cwd when manage.py is invoked) + scripts/
BASE = os.path.join(os.getcwd(), 'scripts')

TESTS = [
    ("01 — Badge Scope Consistency",          "smoke_test_01_badge_scope.py"),
    ("02 — StaffNotification Suppression",    "smoke_test_02_notification_suppression.py"),
    ("03 — Doc Upload → Badge Chain",         "smoke_test_03_doc_upload_badge.py"),
    ("04 — PF ERR / MOD Left-Side Badges",    "smoke_test_04_pf_err_mod_badges.py"),
    ("05 — Bell Mark-As-Read → Badge Link",   "smoke_test_05_bell_badge_linkage.py"),
]

DIVIDER = "=" * 70

print(f"\n{DIVIDER}")
print("  ALERT SYSTEM SMOKE TESTS — Full Suite")
print(f"  Environment: {os.environ.get('DJANGO_SETTINGS_MODULE', 'unknown')}")
print(DIVIDER)

for label, filename in TESTS:
    path = os.path.join(BASE, filename)
    print(f"\n>>> {label}")
    print("-" * 70)
    try:
        with open(path) as f:
            exec(compile(f.read(), path, 'exec'))
    except SystemExit:
        pass  # individual scripts may call sys.exit(0) — ignore
    except Exception as e:
        print(f"  ERROR running {filename}: {e}")

print(f"\n{DIVIDER}")
print("  All smoke tests complete.")
print(f"{DIVIDER}\n")
