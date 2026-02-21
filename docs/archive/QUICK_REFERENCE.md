# Completed Case Resubmission Feature - Quick Reference Guide

## What Was Built

A complete feature allowing members to:
1. Upload additional documents to completed cases
2. Resubmit cases back to "Submitted" status for technician review
3. Track resubmission history and count

---

## Quick Start for Testing

### For Members

1. **View a Completed Case**
   - Go to Member Dashboard → Find a completed case → Click "View"
   - Look for the new "Upload Additional Documents & Resubmit" card

2. **Upload Documents**
   - Click "Select File" in the upload form
   - Add optional description
   - Click "Upload Document"
   - Repeat as needed

3. **Resubmit Case**
   - Scroll down and click the **"Resubmit Case"** button
   - Review confirmation page with all details
   - Add optional notes explaining why resubmitting
   - Click **"Confirm Resubmission"**
   - Case status changes to "Submitted"

4. **View in Dashboard**
   - Case appears in Submitted section (if filtering by status)
   - Shows resubmission badge: "Resubmitted #1"

---

## Files Modified/Created

### Model Changes
- **[cases/models.py](cases/models.py)** - Added 5 new fields to Case model

### Views
- **[cases/views.py](cases/views.py)** - Added 2 new functions:
  - `upload_member_document_to_completed_case()`
  - `resubmit_case()`

### URLs
- **[cases/urls.py](cases/urls.py)** - Added 2 new routes

### Templates
- **[cases/templates/cases/case_detail.html](cases/templates/cases/case_detail.html)** - Added upload/resubmit UI
- **[cases/templates/cases/confirm_resubmit_case.html](cases/templates/cases/confirm_resubmit_case.html)** - NEW confirmation page
- **[cases/templates/cases/member_dashboard.html](cases/templates/cases/member_dashboard.html)** - Added resubmission badge

### Documentation
- **[COMPLETED_CASE_RESUBMISSION.md](COMPLETED_CASE_RESUBMISSION.md)** - Feature design document
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Complete implementation guide
- **[MIGRATION_INSTRUCTIONS.md](MIGRATION_INSTRUCTIONS.md)** - Database migration code

---

## Next Steps: Database Migration

Before the feature is active, you must run the database migration:

```bash
# Create migration
python manage.py makemigrations cases

# Apply migration
python manage.py migrate cases
```

This adds 5 new columns to the `cases_case` table:
- `is_resubmitted` (boolean, default=False)
- `resubmission_count` (integer, default=0)
- `previous_status` (varchar, blank=True)
- `resubmission_date` (datetime, nullable)
- `resubmission_notes` (text, blank=True)

---

## Key Features

### For Members
✅ Upload documents to completed cases  
✅ Add descriptions to documents  
✅ Resubmit with optional notes  
✅ See upload history  
✅ Track resubmission count  

### For Technicians
✅ See resubmitted cases in dashboard  
✅ View member's resubmission notes  
✅ See all supplementary documents  
✅ Track resubmission history  
✅ Process resubmitted cases normally  

### For Admins/Managers
✅ Full visibility of resubmission data  
✅ Track resubmission trends  
✅ See complete case history  

---

## Data Stored

### New Case Fields

| Field | Type | Example |
|-------|------|---------|
| `is_resubmitted` | Boolean | True |
| `resubmission_count` | Integer | 1 |
| `previous_status` | CharField | 'completed' |
| `resubmission_date` | DateTime | 2026-01-06 16:45:00 |
| `resubmission_notes` | TextField | "Added missing tax documents" |

### Supplementary Documents

Uploaded as CaseDocument objects with:
- `document_type` = 'supporting'
- `uploaded_by` = member user
- `notes` = optional description
- `uploaded_at` = auto timestamp
- `file` = actual document file

---

## User Experience Flow

```
Member Dashboard
    ↓
Completed Case Listed
    ↓
Click "View"
    ↓
Case Detail Page (Completed)
    ↓
"Upload Additional Documents & Resubmit" Card
    ↓
Upload documents (1 or more)
    ↓
Click "Resubmit Case"
    ↓
Confirmation Page
    ↓
Click "Confirm Resubmission"
    ↓
Status Changes: Completed → Submitted
    ↓
Dashboard shows "Resubmitted #1" badge
    ↓
Technician sees in dashboard
```

---

## Testing Scenarios

### Scenario 1: Basic Upload & Resubmit
1. Find a completed case
2. Upload 1 document
3. Click Resubmit
4. Confirm
5. Verify status changed to Submitted

### Scenario 2: Multiple Documents
1. Find a completed case
2. Upload 3 documents (different formats)
3. Each should upload successfully
4. All should appear in the list
5. Resubmit with all documents

### Scenario 3: With Notes
1. Find a completed case
2. Upload document with description
3. Add resubmission notes
4. Confirm resubmission
5. Verify notes saved

### Scenario 4: Permission Check
1. Try to upload to someone else's case → Should fail
2. Try to upload to submitted case → Should fail
3. Try to upload while not logged in → Should redirect
4. Verify permission errors clear

---

## Known Limitations & Future Work

### Current Limitations
- File size max 50MB (can be increased)
- No email notifications (could add)
- No automatic approvals (manual process)
- No resubmission deadline (could add)

### Future Enhancements
1. Email notifications to technician on resubmission
2. Advanced filtering in dashboards
3. Resubmission limits/deadlines
4. Document requirements/checklist
5. Partial resubmission (specific reports only)
6. Analytics/reporting on resubmission rates

---

## Troubleshooting

### Issue: "Resubmit Case" button not visible
**Solution:** 
- Verify case status is "Completed"
- Verify you're logged in as the case member
- Case must have `actual_release_date` OR `scheduled_release_date`

### Issue: File upload fails
**Solution:**
- Check file size (max 50MB)
- Verify file format is supported
- Check browser console for errors

### Issue: Case status doesn't change after resubmit
**Solution:**
- Refresh the page (browser cache)
- Check database directly: `select status, is_resubmitted from cases_case where external_case_id='XXX';`
- Check error logs

### Issue: Documents don't appear after upload
**Solution:**
- Refresh page
- Check `MEDIA_ROOT` directory exists and is writable
- Check `CaseDocument` table for records

---

## For Developers

### Key Code Locations

**Model Definition:**
```python
# cases/models.py, lines 200-230
class Case(models.Model):
    is_resubmitted = ...
    resubmission_count = ...
    previous_status = ...
    resubmission_date = ...
    resubmission_notes = ...
```

**View Functions:**
```python
# cases/views.py, lines 1240-1320
def upload_member_document_to_completed_case(request, case_id):
    ...

def resubmit_case(request, case_id):
    ...
```

**Routes:**
```python
# cases/urls.py, lines 29-31
path('<int:case_id>/upload-member-document/', ...),
path('<int:case_id>/resubmit/', ...),
```

**Template Sections:**
- Member upload UI: [case_detail.html, ~lines 405-475](cases/templates/cases/case_detail.html#L405)
- Confirmation page: [confirm_resubmit_case.html](cases/templates/cases/confirm_resubmit_case.html) (NEW)
- Dashboard badge: [member_dashboard.html, ~line 191](cases/templates/cases/member_dashboard.html#L191)

---

## API Examples

### Upload Document via Form
```html
<form method="post" action="/cases/5/upload-member-document/" enctype="multipart/form-data">
    {% csrf_token %}
    <input type="file" name="document_file" required>
    <textarea name="document_notes"></textarea>
    <button type="submit">Upload</button>
</form>
```

### Resubmit Case via Link
```html
<a href="/cases/5/resubmit/" class="btn btn-warning">
    <i class="bi bi-arrow-repeat"></i> Resubmit Case
</a>
```

### Direct URL Access
- **Upload:** `POST /cases/5/upload-member-document/`
- **Resubmit (confirm):** `GET /cases/5/resubmit/`
- **Resubmit (process):** `POST /cases/5/resubmit/`

---

## Performance Considerations

- ✅ Database indexes on `status` and `member` fields speed queries
- ✅ Prefetch related documents in case_detail view
- ✅ No N+1 query issues
- ✅ File storage is S3-compatible if needed
- ⚠️ Large file uploads may timeout (depends on server config)

---

## Security Notes

- ✅ CSRF protection on all forms
- ✅ User ownership verification before document upload
- ✅ Case member verification before resubmit
- ✅ File type validation could be enhanced
- ✅ Rate limiting recommended for uploads
- ✅ File scan for viruses recommended

---

## Documentation Files

Quick links to full documentation:

1. **[COMPLETED_CASE_RESUBMISSION.md](COMPLETED_CASE_RESUBMISSION.md)**  
   Complete feature design, requirements, workflows

2. **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**  
   Full implementation details, testing, deployment

3. **[MIGRATION_INSTRUCTIONS.md](MIGRATION_INSTRUCTIONS.md)**  
   Database migration code and instructions

4. **This file: Quick reference** for rapid lookup

---

**Last Updated:** January 6, 2026  
**Feature Status:** ✅ Implementation Complete  
**Next Action:** Run database migration, then test
