# Scheduled Release & Communication Implementation Plan - 01/11/2026

## Requirements

### 1. Notes Section (Communication Hub)
- ✅ Open for EVERYONE to read and write
- Members, Technicians, Admins, Managers all can add notes
- Use `is_internal=False` for notes visible to all
- All previous notes visible (threaded conversation)

### 2. Member Document Upload Controls
- ✅ Draft Mode: Can upload in Additional Documents
- ✅ Resubmit: Can upload after completed (supplementary)
- ❌ Submitted/Accepted: Cannot upload
- Logic already exists, just verify it works

### 3. Technician Report Access (CRITICAL)
- ✅ Members: Cannot see Reports or Additional Tech Documents until `actual_release_date` is set
- ✅ Tech/Admin/Manager: Can see ALL details at ANY time
- ❌ Template currently shows reports to all roles

### 4. Case Details Access
- ✅ Members: Limited by release status
- ✅ Tech/Admin/Manager: No restrictions

### 5. Cron Job Setup
- ✅ Document how to schedule daily execution
- ✅ Provide exact cron command
- ✅ Test dry-run mode

---

## Implementation Steps

### Step 1: Update CaseNote Model to Support Public Notes ✅
Add flag to differentiate internal vs public notes

### Step 2: Update add_case_note View ✅
Allow members to add notes with `is_internal=False`

### Step 3: Update Template - Notes Section ✅
Show all notes to all roles (filter by is_internal in view)

### Step 4: Update Template - Reports Section ❌ CRITICAL
Hide from members unless released

### Step 5: Update Template - Additional Documents ❌ CRITICAL
Hide from members unless released

### Step 6: Add "Pending Release" Message ✅
Show members when case is waiting for release

### Step 7: Cron Job Documentation ✅
Provide setup instructions

---

## Key Changes Needed

1. **View: add_case_note** - Allow members, change is_internal based on role
2. **Template: case_detail.html** - Lines 631-680 (notes section)
3. **Template: case_detail.html** - Lines 684-738 (reports + additional docs)
4. **Server Config** - Cron job setup

---

## Current Status

| Component | Status | Action |
|-----------|--------|--------|
| CaseNote model | ✅ Has is_internal | Keep as-is |
| add_case_note view | ❌ Techs only | Update to allow members |
| Notes template display | ❌ Techs only | Update to show all |
| Reports hiding | ❌ Shows to all | Hide from members unless released |
| Tech docs hiding | ❌ Shows to all | Hide from members unless released |
| Member upload controls | ✅ Working | Verify |
| Release logic | ✅ Working | Document cron setup |

