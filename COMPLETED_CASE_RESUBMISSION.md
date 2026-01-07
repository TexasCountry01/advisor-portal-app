# Completed Case Resubmission Feature

## Overview
This document outlines the feature that allows members (Financial Advisors) to upload additional documents to completed cases and resubmit them for further processing.

## Current State Analysis

### Completed Case Display
**Member Dashboard** ([cases/templates/cases/member_dashboard.html](cases/templates/cases/member_dashboard.html#L149-L165)):
- Cases marked with status `'completed'` show as "Completed" badge when `actual_release_date` is set
- Shows as "Working" badge if completed but not yet released (scheduled release date)
- Members can view completed cases by clicking "View" button

**Case Detail View** ([cases/views.py](cases/views.py#L597-L650)):
- Members can view their own completed cases
- Case permissions: Members can view and edit (`can_edit=True`) their own cases
- Current document model only supports viewing/downloading uploaded documents
- No upload capability for members on completed cases

### Current Case Model Fields
**Key fields** ([cases/models.py](cases/models.py#L35-L150)):
- `status`: 'draft', 'submitted', 'accepted', 'hold', 'pending_review', 'completed'
- `date_completed`: DateTimeField (set when status becomes completed)
- `actual_release_date`: DateTimeField (when released to member)
- `scheduled_release_date`: DateField (scheduled release date)
- `documents`: ForeignKey relationship to CaseDocument (many-to-many)

### Document Upload System
**CaseDocument Model** ([cases/models.py](cases/models.py#L293-L310)):
- Supports document types: 'fact_finder', 'supporting', 'report', 'other'
- Currently only technicians can upload via `upload_technician_document` view
- `uploaded_by` field tracks which user uploaded the document

## Feature Requirements

### 1. Member Document Upload to Completed Cases
**Scenario**: 
- Member views a completed case
- Can upload additional supporting documents
- Documents are tagged as "Member Supplement" type
- Documents are added to the case's document collection
- No case status change yet (waiting for resubmission action)

**Permissions**:
- Only the member who owns the case can upload
- Case must be in 'completed' status
- Unlimited documents can be uploaded

### 2. Case Resubmission
**Scenario**:
- After uploading additional documents, member clicks "Resubmit Case"
- Case status changes from 'completed' back to 'submitted'
- Technician sees case reappear in dashboard with visual indication
- System tracks resubmission history
- Case maintains previous completion history

**Permissions**:
- Only the member who owns the case can resubmit
- Case must be in 'completed' status
- At least one supplementary document must exist

### 3. Member Dashboard Updates
**Changes**:
- Completed cases show upload button (pencil icon or upload icon)
- Member can view all documents previously uploaded + newly added
- Visual indicator showing "pending resubmission review" or similar

### 4. Technician Dashboard Updates
**Changes**:
- Resubmitted cases show visual indicator (badge or highlight)
- Can filter by "resubmitted" status
- Can view supplementary documents and notes
- Can mark as completed again or take other actions

## Implementation Plan

### Step 1: Update Case Model
Add fields to track resubmission:
```python
class Case(models.Model):
    # Existing fields...
    
    # Resubmission tracking
    is_resubmitted = models.BooleanField(default=False)
    resubmission_count = models.PositiveIntegerField(default=0)
    previous_status = models.CharField(max_length=20, blank=True)
    resubmission_date = models.DateTimeField(null=True, blank=True)
    resubmission_notes = models.TextField(blank=True)
```

### Step 2: Create New Views

#### 2a. Member Document Upload for Completed Cases
```python
def upload_member_document_to_completed_case(request, case_id):
    """Allow members to upload documents to their completed cases"""
    # Validation:
    # - User is member who owns the case
    # - Case status is 'completed'
    # - Document file provided
    
    # Action:
    # - Create CaseDocument with type 'member_supplement'
    # - Tag document with timestamp and notes
    # - Don't change case status
```

#### 2b. Case Resubmission
```python
def resubmit_case(request, case_id):
    """Allow members to resubmit completed cases"""
    # Validation:
    # - User is member who owns the case
    # - Case status is 'completed'
    # - At least one supplementary document exists (optional requirement)
    
    # Action:
    # - Change status from 'completed' to 'submitted'
    # - Set resubmission_date to current time
    # - Increment resubmission_count
    # - Save previous_status as 'completed'
    # - Update is_resubmitted flag
    # - Log resubmission event
```

### Step 3: Update Templates

#### 3a. Case Detail Template
Add section for completed cases allowing members to:
1. Upload additional documents
2. View all uploaded documents (original + supplements)
3. Add resubmission notes
4. Click "Resubmit Case" button

Example structure:
```html
{% if case.status == 'completed' and user.role == 'member' %}
    <div class="card mb-4">
        <div class="card-header bg-info text-white">
            <h5 class="mb-0">Upload Additional Documents & Resubmit</h5>
        </div>
        <div class="card-body">
            <!-- Document upload form -->
            <!-- Resubmit button -->
        </div>
    </div>
{% endif %}
```

### Step 4: Update URLs
Add new routes in [cases/urls.py](cases/urls.py):
```python
path('upload-member-document/<int:case_id>/', 
     views.upload_member_document_to_completed_case, 
     name='upload_member_document_completed'),
path('resubmit-case/<int:case_id>/', 
     views.resubmit_case, 
     name='resubmit_case'),
```

### Step 5: Update Dashboards

#### Member Dashboard
- Add visual indicator for completed cases with pending supplements
- Show "Can resubmit" badge

#### Technician Dashboard
- Add filter for resubmitted cases
- Show resubmission badge on resubmitted cases
- Display supplementary documents separately for easy identification

## Database Migration
```python
# Migration content
class Migration(migrations.Migration):
    dependencies = [
        ('cases', '[previous_migration]'),
    ]
    
    operations = [
        migrations.AddField(
            model_name='case',
            name='is_resubmitted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='case',
            name='resubmission_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='case',
            name='previous_status',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='case',
            name='resubmission_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='case',
            name='resubmission_notes',
            field=models.TextField(blank=True),
        ),
    ]
```

## Workflow Summary

### Member Perspective
1. **View Completed Case**: Member clicks "View" on completed case in dashboard
2. **Review Case Data**: Member sees all original documents and case details
3. **Upload Supplements**: Member uploads additional documents in the case detail view
4. **Review Documents**: Member sees all documents (original + new) listed together
5. **Add Notes** (Optional): Member can add notes explaining the new documents
6. **Resubmit**: Member clicks "Resubmit Case" button
7. **Confirmation**: System shows confirmation dialog with summary
8. **Case Status Change**: Case transitions to 'submitted' status
9. **Dashboard Update**: Case reappears in "Submitted" section (if filtering) or shows new badge

### Technician Perspective
1. **Dashboard Alert**: Resubmitted case appears with visual badge/highlight
2. **View Case**: Technician opens case and sees:
   - Original documents (marked as original)
   - Supplementary documents (clearly labeled as supplements with dates)
   - Resubmission count and dates
   - Resubmission notes from member
3. **Process**: Technician can:
   - Review new documents
   - Add internal notes
   - Upload reports again if needed
   - Mark as completed
   - Or take other actions as needed

### Admin/Manager Perspective
1. Can see resubmitted cases with clear indicators
2. Can track resubmission history and statistics
3. Can filter/sort by resubmission count
4. Can monitor which cases are frequently resubmitted

## Status Flow Diagram

```
[Completed] 
    ↓
    (Member uploads documents)
    ↓
[Completed with Pending Supplements]
    ↓
    (Member clicks Resubmit)
    ↓
[Submitted] (is_resubmitted=True, resubmission_count=1)
    ↓
    (Technician processes again)
    ↓
[Accepted/Hold/Pending Review/Completed]
```

## Edge Cases & Considerations

1. **Multiple Resubmissions**: Should be allowed
   - Track resubmission_count
   - Show resubmission history timeline
   
2. **Technician Actions on Resubmitted Cases**:
   - Should they see different UI?
   - Should resubmission notes be visible?
   - Answer: YES - show banner with resubmission details
   
3. **Document Retention**:
   - Keep all original documents
   - Keep all supplementary documents
   - Show timestamps and upload order
   
4. **Permissions During Resubmission**:
   - Member cannot edit case details during resubmission
   - Can only upload documents and add notes
   
5. **Notifications**:
   - Consider notifying assigned technician when case is resubmitted
   - Consider notifying member when case is completed again

## Testing Checklist

### Member Functionality
- [ ] Member can view completed case
- [ ] Member can upload documents to completed case
- [ ] Multiple documents can be uploaded
- [ ] Document upload form shows clear feedback
- [ ] Member cannot upload to non-completed cases
- [ ] Member cannot upload to someone else's cases
- [ ] Member can add resubmission notes
- [ ] Member can resubmit case
- [ ] Case status changes to 'submitted' after resubmit
- [ ] Case appears in submitted section of dashboard
- [ ] Resubmission count increments
- [ ] Resubmission date is recorded

### Technician Functionality
- [ ] Technician can see resubmitted cases
- [ ] Resubmitted badge displays on resubmitted cases
- [ ] Technician can see original and supplementary documents
- [ ] Technician can see resubmission history
- [ ] Technician can add new reports
- [ ] Technician can mark case as completed again
- [ ] Resubmitted cases can be filtered

### Dashboard Updates
- [ ] Member dashboard shows completed cases with resubmit option
- [ ] Technician dashboard highlights resubmitted cases
- [ ] Admin dashboard shows resubmission history
- [ ] Case detail view shows all documents in upload order

## Future Enhancements

1. **Automated Notifications**: Notify technician when member resubmits
2. **Rejection Workflow**: Allow technician to request specific documents
3. **Document Requirements**: Specify which documents are required for resubmission
4. **Resubmission Deadline**: Set deadline for resubmission window
5. **Partial Resubmission**: Allow resubmitting specific report only
6. **Approval Workflow**: Require manager approval for resubmitted cases

---

## Files to Modify
1. [cases/models.py](cases/models.py) - Add resubmission fields
2. [cases/views.py](cases/views.py) - Add new view functions
3. [cases/templates/cases/case_detail.html](cases/templates/cases/case_detail.html) - Add upload/resubmit UI
4. [cases/urls.py](cases/urls.py) - Add new URL routes
5. [cases/templates/cases/member_dashboard.html](cases/templates/cases/member_dashboard.html) - Add resubmit indicators
6. [cases/templates/cases/technician_dashboard.html](cases/templates/cases/technician_dashboard.html) - Add resubmitted case indicators

## Migration Strategy
1. Add model fields with defaults (non-breaking)
2. Deploy code changes
3. Deploy template changes
4. Enable feature gradually (optional feature flag)
