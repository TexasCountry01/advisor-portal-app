# TIMEZONE VERIFICATION REPORT - Central Time Zone (CST)

**Investigation Date:** January 31, 2026  
**Focus:** Timestamps for Messages, Notifications, and Audit Trail  
**Requirement:** All timestamps must use Central Time Zone (America/Chicago)

---

## CURRENT STATE ANALYSIS

### 1. ✅ Django Settings Configuration

**File:** `config/settings.py` (Lines 141, 145)

```python
TIME_ZONE = 'UTC'
USE_TZ = True
```

**Finding:**
- Django is configured with `TIME_ZONE = 'UTC'` and `USE_TZ = True`
- This means Django stores all datetimes in UTC in the database
- But converts to the configured TIME_ZONE when displaying

**Status:** ⚠️ **ISSUE IDENTIFIED**
- The TIME_ZONE should be set to 'America/Chicago' for Central Time
- Currently set to UTC, so Django won't automatically convert to CST

---

### 2. ✅ Timezone Service Exists

**File:** `cases/services/timezone_service.py`

```python
from django.utils import timezone
import pytz

# Central Standard Time timezone
CST = pytz.timezone('America/Chicago')

def get_cst_now():
    """Get current datetime in Central Standard Time"""
    return timezone.now().astimezone(CST)
```

**Finding:**
- A dedicated timezone service exists for CST conversions
- Uses `pytz.timezone('America/Chicago')` (correct)
- Has `get_cst_now()` function to get current time in CST

**Status:** ✅ **GOOD - Service exists**

---

### 3. 🔴 PROBLEM: Notifications Timestamps - NOT IN CST

**File:** `cases/views.py` - Line 4254 (get_member_notifications API)

```python
'created_at': notif.created_at.strftime('%b %d, %Y %I:%M %p'),
'read_at': notif.read_at.strftime('%b %d, %Y %I:%M %p') if notif.read_at else None
```

**Finding:**
- Timestamps are being formatted WITHOUT timezone conversion
- Uses `.strftime()` on the raw datetime
- Since Django TIME_ZONE is UTC, these timestamps will be in UTC, NOT CST
- Example: "Jan 31, 2026 01:26 PM" might be UTC time, not CST

**Screenshot Evidence:**
- User provided screenshot shows: "Jan 31, 2026 01:26 PM"
- This needs verification if it's CST or UTC

**Status:** 🔴 **ISSUE - Missing CST Conversion**

---

### 4. 🔴 PROBLEM: Message Timestamps - Not Guaranteed CST

**File:** `cases/views.py` - Line 3028 (get_case_messages API)

```python
'created_at': msg.created_at.isoformat(),
'updated_at': msg.updated_at.isoformat(),
```

**Finding:**
- Returns ISO format timestamp (UTC-based)
- Frontend converts using `new Date(msg.created_at).toLocaleString()`
- This will use user's BROWSER timezone, NOT Central Time
- **If member opens from different timezone, they see wrong time**

**File:** `cases/templates/cases/case_detail.html` - Line 1880

```html
<small class="text-muted d-block mt-1">${new Date(msg.created_at).toLocaleString()}</small>
```

**Status:** 🔴 **CRITICAL ISSUE - Browser Timezone Used, Not CST**

---

### 5. 🔴 PROBLEM: Case Timestamps - Various Issues

**File:** `cases/templates/cases/case_detail.html` - Line 273

```html
{{ case.created_at|date:"m/d/Y" }}
```

**Finding:**
- Uses Django template date filter
- Will use Django's configured TIME_ZONE (currently UTC)
- Not explicitly converted to CST

**Status:** 🔴 **ISSUE - Uses UTC, Not CST**

---

### 6. 🔴 PROBLEM: Audit Trail Timestamps - Not CST

**File:** `core/models.py` - Lines 73-77

```python
timestamp = models.DateTimeField(
    default=timezone.now,
    db_index=True,
    help_text='When the action occurred'
)
```

**Finding:**
- Uses Django's `timezone.now()` which respects TIME_ZONE setting
- Since TIME_ZONE is UTC, audit timestamps are in UTC
- Not explicitly converted to CST anywhere

**Status:** 🔴 **ISSUE - Audit timestamps in UTC, should be CST**

---

### 7. ✅ Email Timestamps - CST USED

**File:** `cases/services/timezone_service.py`
**File:** `cases/management/commands/send_scheduled_emails.py` - Line 73

```python
case.actual_email_sent_date = timezone.now()
```

**Finding:**
- Uses Django's timezone service
- Since email system uses CST calculations, timestamps are CST
- Verified in DELAYED_EMAIL_NOTIFICATION_IMPLEMENTATION.md

**Status:** ✅ **GOOD - Email timestamps in CST**

---

## ROOT CAUSE ANALYSIS

### Primary Issue:
**`TIME_ZONE` in Django settings is set to 'UTC' instead of 'America/Chicago'**

When `TIME_ZONE = 'UTC'`:
- Django stores everything in UTC
- Displays everything in UTC by default
- Template filters use UTC
- `timezone.now()` returns UTC

When it should be `TIME_ZONE = 'America/Chicago'`:
- Django stores in UTC (database)
- Displays in CST (frontend/API)
- Template filters use CST
- `timezone.now()` would return CST (internally UTC but converted)

### Secondary Issues:
1. Message API returns ISO format, frontend uses browser timezone
2. Notification timestamps not converted to CST before sending to API
3. Case timestamps using Django template filters without explicit CST conversion
4. Inconsistent timezone handling across different features

---

## VERIFICATION CHECKLIST

```
Current Implementation:
  ✅ Django has pytz installed (requirements.txt)
  ✅ timezone_service.py exists with CST support
  ✅ get_cst_now() function available
  ✅ Case scheduling uses CST calculations
  ✅ Email notifications use CST calculations
  
❌ MISSING IMPLEMENTATIONS:
  🔴 Django TIME_ZONE not set to America/Chicago
  🔴 Notification timestamps not converted to CST
  🔴 Message timestamps returned as ISO, converted by browser timezone
  🔴 Audit trail timestamps in UTC, not CST
  🔴 Case detail timestamps using UTC, not CST
  🔴 No consistent timezone conversion throughout system
```

---

## AFFECTED FEATURES

### 1. **Notifications (CRITICAL)**
- User sees: "Jan 31, 2026 01:26 PM"
- Currently: UTC time
- Should be: Central Time (CST/CDT)
- Location: `cases/views.py` line 4254

### 2. **Messages (CRITICAL)**
- User sees: `new Date(msg.created_at).toLocaleString()`
- Currently: Browser's local timezone
- Should be: Central Time (CST/CDT)
- Location: `cases/templates/cases/case_detail.html` line 1880

### 3. **Audit Trail (HIGH)**
- Admin sees: UTC timestamps
- Should see: Central Time timestamps
- Location: `core/models.py` (all timestamp fields)

### 4. **Case Timestamps (MEDIUM)**
- Shows creation date in UTC
- Should show in CST
- Location: Various templates using `|date` filter

---

## SOLUTION OPTIONS

### Option 1: Change Django TIME_ZONE (RECOMMENDED)
**File:** `config/settings.py`

```python
# Change from:
TIME_ZONE = 'UTC'

# Change to:
TIME_ZONE = 'America/Chicago'
```

**Pros:**
- Automatic for all templates
- All `timezone.now()` returns CST
- All date filters use CST
- Simple one-line change

**Cons:**
- May affect other parts of system
- Need to test thoroughly

### Option 2: Explicit Timezone Conversion (CURRENT WORKAROUND)
Keep TIME_ZONE as UTC, explicitly convert in each API/template:

```python
# For API responses:
from cases.services.timezone_service import get_cst_now
cst_time = notif.created_at.astimezone(CST)
'created_at': cst_time.strftime('%b %d, %Y %I:%M %p')

# For JavaScript:
# Send formatted CST string from backend instead of ISO
```

**Pros:**
- Minimal system-wide impact

**Cons:**
- Requires changes in many places
- Easy to forget in new code
- Inconsistent implementation

### Option 3: Hybrid Approach
1. Set `TIME_ZONE = 'America/Chicago'` in Django
2. Keep explicit CST conversions where needed for clarity
3. Use template filters for simple date display

---

## RECOMMENDED IMMEDIATE FIXES

### Fix 1: Update Django TIME_ZONE Setting

**File:** `config/settings.py` - Line 141

```python
# Current:
TIME_ZONE = 'UTC'

# Change to:
TIME_ZONE = 'America/Chicago'
```

**Impact:** 
- All timestamps will automatically use CST
- Fixes notification timestamps
- Fixes audit trail display timestamps

### Fix 2: Update Notification API Response

**File:** `cases/views.py` - Lines 4253-4254

```python
# Current:
'created_at': notif.created_at.strftime('%b %d, %Y %I:%M %p'),
'read_at': notif.read_at.strftime('%b %d, %Y %I:%M %p') if notif.read_at else None

# Change to:
from cases.services.timezone_service import CST
cst_tz = pytz.timezone('America/Chicago')
'created_at': notif.created_at.astimezone(cst_tz).strftime('%b %d, %Y %I:%M %p'),
'read_at': notif.read_at.astimezone(cst_tz).strftime('%b %d, %Y %I:%M %p') if notif.read_at else None
```

### Fix 3: Update Message API Response

**File:** `cases/views.py` - Lines 3027-3029

```python
# Current:
'created_at': msg.created_at.isoformat(),
'updated_at': msg.updated_at.isoformat(),

# Change to (send formatted CST time instead of ISO):
from cases.services.timezone_service import CST
import pytz
cst_tz = pytz.timezone('America/Chicago')
'created_at': msg.created_at.astimezone(cst_tz).strftime('%b %d, %Y %I:%M %p'),
'updated_at': msg.updated_at.astimezone(cst_tz).strftime('%b %d, %Y %I:%M %p'),
```

### Fix 4: Update Frontend Message Display

**File:** `cases/templates/cases/case_detail.html` - Line 1880

```html
<!-- Current: Uses browser timezone -->
<small class="text-muted d-block mt-1">${new Date(msg.created_at).toLocaleString()}</small>

<!-- Change to: Use CST string from backend -->
<small class="text-muted d-block mt-1">${msg.created_at}</small>
```

---

## TESTING VERIFICATION

After fixes, verify:

```
✓ Notification timestamps show CST time
✓ Message timestamps show CST time  
✓ Audit trail shows CST timestamps
✓ Case created date shows CST
✓ Tests pass with new timezone setting
✓ Screenshots match in screenshot (appears to be CST already?)
```

---

## SCREENSHOT ANALYSIS

**Screenshot shows:** "Jan 31, 2026 01:26 PM"

**Question:** Is this CST or UTC?
- If member is in CST timezone: Likely CST (correct)
- If member is in different timezone: Need to verify source

**Current code path:**
1. Notification created with `timezone.now()` → UTC stored in DB
2. API formats without conversion → Still UTC time
3. Frontend displays → Appears as UTC

**With fix:**
1. Notification created with `timezone.now()` → CST (after TIME_ZONE change)
2. API formats after CST conversion → CST time
3. Frontend displays → Always CST

---

## CONCLUSION

**Status:** 🔴 **CRITICAL - Timestamps NOT Consistently in CST**

**Issues Found:**
1. Django TIME_ZONE set to UTC instead of America/Chicago
2. Notification timestamps sent as UTC, not CST
3. Message timestamps use browser timezone, not CST
4. Audit trail timestamps in UTC, not CST
5. Case timestamps using UTC, not CST

**Severity:** HIGH
- Affects user-facing timestamps
- Violates requirement: "CENTRAL TIME ZONE, United States"
- Could cause confusion if members in different timezones

**Recommended Action:** 
- Apply all 4 fixes immediately
- Test thoroughly
- Deploy to TEST server
- Verify with user

