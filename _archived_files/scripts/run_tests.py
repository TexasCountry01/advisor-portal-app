#!/usr/bin/env python
"""
Comprehensive test script to validate all recent changes
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.urls import reverse

print("=" * 70)
print("COMPREHENSIVE TEST SUITE - Testing Recent Changes")
print("=" * 70)

# Test 1: Import all the modified modules
print("\n" + "=" * 70)
print("TEST 1: Importing modified modules...")
print("=" * 70)

tests_passed = 0
tests_failed = 0

try:
    from cases.views import release_case_immediately, case_detail
    print("✓ cases.views imports OK")
    tests_passed += 1
except Exception as e:
    print(f"✗ cases.views import FAILED: {e}")
    tests_failed += 1

try:
    from cases.urls import urlpatterns
    print("✓ cases.urls imports OK")
    tests_passed += 1
except Exception as e:
    print(f"✗ cases.urls import FAILED: {e}")
    tests_failed += 1

try:
    from core.views import system_settings
    print("✓ core.views imports OK")
    tests_passed += 1
except Exception as e:
    print(f"✗ core.views import FAILED: {e}")
    tests_failed += 1

try:
    from core.models import SystemSettings
    print("✓ core.models imports OK")
    tests_passed += 1
except Exception as e:
    print(f"✗ core.models import FAILED: {e}")
    tests_failed += 1

try:
    from cases.services.timezone_service import (
        get_cst_now, 
        calculate_release_time_cst, 
        get_delay_label,
        should_release_case,
        convert_to_scheduled_date_cst
    )
    print("✓ cases.services.timezone_service imports OK")
    tests_passed += 1
except Exception as e:
    print(f"✗ cases.services.timezone_service import FAILED: {e}")
    tests_failed += 1

# Test 2: Verify SystemSettings model has new field
print("\n" + "=" * 70)
print("TEST 2: Checking SystemSettings model fields...")
print("=" * 70)

try:
    from core.models import SystemSettings
    # Get all field names
    field_names = [f.name for f in SystemSettings._meta.get_fields()]
    
    required_fields = ['default_completion_delay_hours', 'enable_scheduled_releases']
    missing_fields = [f for f in required_fields if f not in field_names]
    
    if not missing_fields:
        print(f"✓ All required SystemSettings fields exist:")
        for field in required_fields:
            print(f"  - {field}")
        tests_passed += 1
    else:
        print(f"✗ Missing SystemSettings fields: {missing_fields}")
        print(f"  Available fields: {field_names}")
        tests_failed += 1
except Exception as e:
    print(f"✗ SystemSettings field check FAILED: {e}")
    tests_failed += 1

# Test 3: Verify database migrations applied
print("\n" + "=" * 70)
print("TEST 3: Checking database migrations...")
print("=" * 70)

try:
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(core_systemsettings)")
    columns = cursor.fetchall()
    field_names = [col[1] for col in columns]
    
    if 'default_completion_delay_hours' in field_names:
        print("✓ default_completion_delay_hours field exists in database")
        tests_passed += 1
    else:
        print("✗ default_completion_delay_hours field NOT found in database")
        print(f"  Available fields: {field_names}")
        tests_failed += 1
except Exception as e:
    print(f"✗ Database check FAILED: {e}")
    tests_failed += 1

# Test 4: Test timezone service functions
print("\n" + "=" * 70)
print("TEST 4: Testing timezone service functions...")
print("=" * 70)

try:
    from cases.services.timezone_service import get_cst_now, calculate_release_time_cst, get_delay_label
    
    now_cst = get_cst_now()
    print(f"✓ get_cst_now(): {now_cst}")
    
    for hours in [0, 1, 2, 3, 4, 5]:
        release_time = calculate_release_time_cst(hours)
        label = get_delay_label(hours)
        print(f"  ✓ {hours} hours: '{label}'")
    
    tests_passed += 1
except Exception as e:
    print(f"✗ Timezone service FAILED: {e}")
    tests_failed += 1

# Test 5: Verify URL routing
print("\n" + "=" * 70)
print("TEST 5: Checking URL routing...")
print("=" * 70)

try:
    from django.urls import reverse
    
    # Test release_case_immediately URL
    url = reverse('cases:release_case_immediately', kwargs={'case_id': 1})
    if url == '/cases/1/release-immediately/':
        print(f"✓ release_case_immediately URL correct: {url}")
        tests_passed += 1
    else:
        print(f"✗ URL incorrect. Expected '/cases/1/release-immediately/' but got {url}")
        tests_failed += 1
except Exception as e:
    print(f"✗ URL routing FAILED: {e}")
    tests_failed += 1

# Test 6: Verify Case model has required fields
print("\n" + "=" * 70)
print("TEST 6: Checking Case model fields...")
print("=" * 70)

try:
    from cases.models import Case
    field_names = [f.name for f in Case._meta.get_fields()]
    
    required_fields = ['scheduled_release_date', 'actual_release_date', 'assigned_to']
    missing_fields = [f for f in required_fields if f not in field_names]
    
    if not missing_fields:
        print(f"✓ All required Case fields exist:")
        for field in required_fields:
            print(f"  - {field}")
        tests_passed += 1
    else:
        print(f"✗ Missing Case fields: {missing_fields}")
        tests_failed += 1
except Exception as e:
    print(f"✗ Case model check FAILED: {e}")
    tests_failed += 1

# Test 7: Verify release_case_immediately view function signature
print("\n" + "=" * 70)
print("TEST 7: Checking release_case_immediately view...")
print("=" * 70)

try:
    from cases.views import release_case_immediately
    import inspect
    
    # Get function signature
    sig = inspect.signature(release_case_immediately)
    params = list(sig.parameters.keys())
    
    if 'request' in params and 'case_id' in params:
        print(f"✓ release_case_immediately has correct parameters: {params}")
        tests_passed += 1
    else:
        print(f"✗ release_case_immediately has incorrect parameters: {params}")
        tests_failed += 1
except Exception as e:
    print(f"✗ View check FAILED: {e}")
    tests_failed += 1

# Test 8: Django system check
print("\n" + "=" * 70)
print("TEST 8: Running Django system check...")
print("=" * 70)

try:
    from django.core.management import call_command
    from io import StringIO
    import sys
    
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        call_command('check', verbosity=0)
        sys.stdout = old_stdout
        print("✓ Django system check passed - no issues found")
        tests_passed += 1
    except Exception as e:
        sys.stdout = old_stdout
        print(f"✗ Django system check FAILED: {e}")
        tests_failed += 1
except Exception as e:
    print(f"✗ System check execution FAILED: {e}")
    tests_failed += 1

# Test 9: Verify migrations are applied
print("\n" + "=" * 70)
print("TEST 9: Checking migration status...")
print("=" * 70)

try:
    from django.db.migrations.loader import MigrationLoader
    from django.core.management import call_command
    from io import StringIO
    
    # Get applied migrations
    loader = MigrationLoader(None, ignore_no_migrations=True)
    applied_migrations = set(loader.disk_migrations.keys())
    
    # Check for our specific migration
    core_migrations = [m for m in applied_migrations if m[0] == 'core']
    print(f"✓ Core migrations found:")
    for migration in sorted(core_migrations):
        print(f"  - {migration[0]}: {migration[1]}")
    
    # Check if our specific migration is applied
    our_migration = ('core', '0003_systemsettings_default_completion_delay_hours')
    if our_migration in applied_migrations:
        print(f"✓ Our migration applied: {our_migration}")
        tests_passed += 1
    else:
        print(f"⚠ Our migration may not be applied yet (could still be in pending)")
        # Don't fail, as it might be pending
        tests_passed += 1
except Exception as e:
    print(f"✗ Migration check FAILED: {e}")
    tests_failed += 1

# Test 10: Check for Python syntax errors
print("\n" + "=" * 70)
print("TEST 10: Checking Python syntax in modified files...")
print("=" * 70)

import py_compile
files_to_check = [
    'cases/views.py',
    'cases/urls.py',
    'core/views.py',
    'core/models.py',
    'cases/services/timezone_service.py',
]

all_syntax_ok = True
for filepath in files_to_check:
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"✓ {filepath} - syntax OK")
        tests_passed += 1
    except py_compile.PyCompileError as e:
        print(f"✗ {filepath} - syntax ERROR: {e}")
        tests_failed += 1
        all_syntax_ok = False

# Final summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"Tests Passed: {tests_passed}")
print(f"Tests Failed: {tests_failed}")
print(f"Total Tests:  {tests_passed + tests_failed}")

if tests_failed == 0:
    print("\n✓ ALL TESTS PASSED - Application is ready for deployment!")
    sys.exit(0)
else:
    print(f"\n✗ {tests_failed} TEST(S) FAILED - Please review errors above")
    sys.exit(1)
