# Quality Review Functionality - Implementation Analysis
## Gap Analysis & Roadmap for advisor-portal-app

**Current Date:** January 17, 2026  
**Status:** COMPREHENSIVE GAP ANALYSIS  
**Priority Level:** HIGH - Core Business Feature

---

## Executive Summary

The Advisor Portal application has **30-40% of the required infrastructure** for quality review, but is **missing the critical workflow logic and UI components**. The database schema is mostly ready, but the review trigger, queue system, and decision logic need to be implemented.

### Current State
✅ **Already Implemented:**
- User model with 3 technician levels
- Case model with `reviewed_by` field and `requires_review` property
- `pending_review` status value
- Admin dashboard stats tracking

❌ **Missing/Incomplete (60-70%):**
- NO automatic trigger to set pending_review status when Level 1 completes
- NO review queue view/interface for Level 2/3 technicians
- NO approve/reject/correct action endpoints
- NO audit trail for review decisions
- NO case_review_history table/model
- NO email/notification system for review actions
- NO review metrics/reporting

---

## Part 1: Current Implementation Analysis

### 1.1 What's Working ✅

#### User Model - COMPLETE
**File:** [accounts/models.py](accounts/models.py#L7-L26)
```python
USER_LEVEL_CHOICES = [
    ('level_1', 'Level 1 - New Technician'),
    ('level_2', 'Level 2 - Technician'),
    ('level_3', 'Level 3 - Senior Technician'),
]

user_level = models.CharField(
    max_length=10, 
    choices=USER_LEVEL_CHOICES, 
    blank=True, 
    null=True,
    help_text='For technicians only: Experience level for quality review workflow'
)
```
✅ Status: Ready to use

#### Case Model - MOSTLY COMPLETE
**File:** [cases/models.py](cases/models.py#L35-40)
- ✅ `STATUS_CHOICES` includes `'pending_review'`
- ✅ `reviewed_by` FK field to Level 2/3 technicians
- ✅ `requires_review` property returns True if assigned_to.user_level == 'level_1'
- ✅ Rejection tracking fields (`rejection_reason`, `rejection_notes`, `rejected_by`)
- ✅ Reassignment history stored in JSON

**Missing fields in Case model:**
- ❌ `reviewed_at` (timestamp when review completed)
- ❌ `review_notes` (feedback from reviewer)
- ❌ `review_status` (approved/sent_back/corrected)

#### Dashboard Stats - PARTIAL
**File:** [cases/views.py](cases/views.py#L194)
```python
'pending_review': cases.filter(status='pending_review').count(),
```
✅ Stat calculated but cases never enter this status

---

### 1.2 What's Missing ❌

#### 1. No Review Trigger Logic
**File:** [cases/views.py](cases/views.py#L1277-1300) - `mark_case_completed()` function

**Current Code:**
```python
case.status = 'completed'  # ❌ DIRECTLY sets to completed
```

**Should Be:**
```python
# Check if Level 1 tech
if case.assigned_to and case.assigned_to.user_level == 'level_1':
    case.status = 'pending_review'  # ✅ Send to review queue instead
else:
    case.status = 'completed'
```

**Impact:** NO cases ever enter `pending_review` status

#### 2. No Review Queue View
**Missing:** View to show Level 2/3 technicians their review queue
- Where: Should be in `cases/views.py`
- What: Django view that filters `Case.objects.filter(status='pending_review')`
- Template: Need new template to display review queue

#### 3. No Review Action Endpoints
**Missing:** Three view functions:
```python
def approve_case_review(request, case_id):
    # Set reviewed_by, review_status='approved', status='completed'
    
def request_case_revisions(request, case_id):
    # Set reviewed_by, review_status='changes_requested', status='accepted'
    
def correct_case_review(request, case_id):
    # Set reviewed_by, review_status='corrected', status='completed'
```

#### 4. No Audit/History Table
**Missing Database Table:** `case_review_history`

Current schema has only fields on Case model, but need separate audit table:
```python
class CaseReviewHistory(models.Model):
    case = FK(Case)
    reviewed_by = FK(User - L2/L3)
    original_tech = FK(User - L1)
    review_action = 'approved' | 'sent_back' | 'corrected'
    review_notes = TextField
    reviewed_at = DateTimeField
```

**Impact:** No audit trail for compliance

#### 5. No Notifications
**Missing:** Email/SMS notifications for review decisions
- When: After review action taken
- To: Level 1 tech gets approval/rejection notification
- Also: Advisor notified when report ready (after approval)

#### 6. No Templates/UI
**Missing:**
- Review queue dashboard view
- Review card/modal for case details
- Approve/Reject/Correct buttons
- Review notes form

---

## Part 2: What Needs to Be Built

### Priority 1: CRITICAL (Foundation)

#### 1.1 Add Missing Model Fields

**File to Modify:** [cases/models.py](cases/models.py#L115-130)

Add these fields to Case model:
```python
reviewed_at = models.DateTimeField(
    null=True, 
    blank=True,
    help_text='When case was reviewed by Level 2/3 technician'
)

review_notes = models.TextField(
    blank=True,
    help_text='Quality review notes from senior technician'
)

review_status = models.CharField(
    max_length=20,
    choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
        ('corrected', 'Corrected'),
    ],
    null=True,
    blank=True,
    help_text='Status of quality review process'
)
```

**Migration Required:** Yes, new fields are optional (null=True, blank=True)

---

#### 1.2 Create CaseReviewHistory Model

**File:** Create `cases/models.py` - add new model

```python
class CaseReviewHistory(models.Model):
    """Audit trail for quality review decisions"""
    
    REVIEW_ACTION_CHOICES = [
        ('approved', 'Approved'),
        ('sent_back', 'Sent Back for Revisions'),
        ('corrected', 'Corrected by Reviewer'),
    ]
    
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='review_history'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cases_reviewed',
        limit_choices_to={'role': 'technician', 'user_level__in': ['level_2', 'level_3']}
    )
    original_tech = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cases_reviewed_by_seniors'
    )
    review_action = models.CharField(
        max_length=20,
        choices=REVIEW_ACTION_CHOICES
    )
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-reviewed_at']
        indexes = [
            models.Index(fields=['case']),
            models.Index(fields=['reviewed_by']),
            models.Index(fields=['reviewed_at']),
        ]
    
    def __str__(self):
        return f"Review of Case {self.case.external_case_id} by {self.reviewed_by.username}"
```

**Migration Required:** Yes, new table

---

#### 1.3 Modify mark_case_completed() to Trigger Review

**File:** [cases/views.py](cases/views.py#L1277-1360)

**Current Code (Line 1310):**
```python
case.status = 'completed'
```

**New Code:**
```python
# ✅ NEW LOGIC: Check if Level 1 technician
if case.assigned_to and case.assigned_to.user_level == 'level_1':
    # Send to review queue instead of completing immediately
    case.status = 'pending_review'
    case.review_status = 'pending'
else:
    # Level 2/3 techs complete directly (no review gate)
    case.status = 'completed'

# [Rest of existing code - release scheduling, etc]
```

**Impact:** This is THE CRITICAL CHANGE - activates entire review workflow

---

### Priority 2: HIGH (Review Queue & Actions)

#### 2.1 Create Review Queue View

**File:** Create new view in [cases/views.py](cases/views.py)

```python
@login_required
def review_queue(request):
    """Display review queue for Level 2/3 technicians"""
    user = request.user
    
    # Permission check
    if user.role != 'technician' or user.user_level not in ['level_2', 'level_3']:
        messages.error(request, 'Access denied. Level 2/3 technicians only.')
        return redirect('home')
    
    # Get all cases pending review
    pending_cases = Case.objects.filter(
        status='pending_review'
    ).select_related(
        'assigned_to',  # Level 1 tech
        'member',
        'reviewed_by'
    ).order_by('-date_submitted')
    
    # Add filtering, sorting, search
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', '-date_submitted')
    
    # [Add filtering logic]
    
    # Pagination
    paginator = Paginator(pending_cases, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'cases': page_obj.object_list,
        'total_cases': paginator.count,
    }
    
    return render(request, 'cases/review_queue.html', context)
```

**Template:** Create `cases/templates/cases/review_queue.html`
- Display list of cases pending review
- Show: Case ID, Level 1 tech name, submission date, complexity tier
- Show: "Review" button for each case
- Link to case detail/review modal

---

#### 2.2 Create Review Detail View

**File:** Add to [cases/views.py](cases/views.py)

```python
@login_required
def review_case_detail(request, case_id):
    """Display detailed review interface for Level 2/3 technician"""
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check
    if user.role != 'technician' or user.user_level not in ['level_2', 'level_3']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Case must be pending review
    if case.status != 'pending_review':
        return JsonResponse({'error': 'Case is not pending review'}, status=400)
    
    # Get case details
    documents = case.documents.all()
    reports = case.reports.all()
    level_1_notes = case.notes
    
    context = {
        'case': case,
        'documents': documents,
        'reports': reports,
        'level_1_notes': level_1_notes,
        'level_1_tech': case.assigned_to,
    }
    
    return render(request, 'cases/review_case_detail.html', context)
```

**Template:** Create `cases/templates/cases/review_case_detail.html`
- Full case information
- Level 1 tech investigation notes
- Uploaded reports
- Documents
- Three action buttons: Approve, Reject, Correct

---

#### 2.3 Create Approve Action

**File:** Add to [cases/views.py](cases/views.py)

```python
@login_required
def approve_case_review(request, case_id):
    """Level 2/3 tech approves case - sends to completed"""
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permissions
    if user.role != 'technician' or user.user_level not in ['level_2', 'level_3']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if case.status != 'pending_review':
        return JsonResponse({'error': 'Case not pending review'}, status=400)
    
    try:
        # Update case
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.review_status = 'approved'
        case.status = 'completed'
        case.save()
        
        # Create audit trail
        CaseReviewHistory.objects.create(
            case=case,
            reviewed_by=user,
            original_tech=case.assigned_to,
            review_action='approved',
            review_notes=request.POST.get('notes', '')
        )
        
        # Send notifications
        send_review_approval_notification(case, user)
        
        messages.success(request, f'Case {case.external_case_id} approved')
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

---

#### 2.4 Create Request Changes Action

**File:** Add to [cases/views.py](cases/views.py)

```python
@login_required
def request_case_revisions(request, case_id):
    """Level 2/3 tech requests changes - sends back to accepted"""
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permissions
    if user.role != 'technician' or user.user_level not in ['level_2', 'level_3']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if case.status != 'pending_review':
        return JsonResponse({'error': 'Case not pending review'}, status=400)
    
    try:
        feedback = request.POST.get('feedback', '')
        
        # Update case - goes back to assigned tech
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.review_status = 'changes_requested'
        case.review_notes = feedback
        case.status = 'accepted'  # Back to working status
        case.save()
        
        # Create audit trail
        CaseReviewHistory.objects.create(
            case=case,
            reviewed_by=user,
            original_tech=case.assigned_to,
            review_action='sent_back',
            review_notes=feedback
        )
        
        # Send notification to Level 1 tech
        send_revision_request_notification(case, user, feedback)
        
        messages.success(request, f'Case {case.external_case_id} sent back for revisions')
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

---

#### 2.5 Create Correct Action

**File:** Add to [cases/views.py](cases/views.py)

```python
@login_required
def correct_case_review(request, case_id):
    """Level 2/3 tech corrects issues - approves with edits"""
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permissions
    if user.role != 'technician' or user.user_level not in ['level_2', 'level_3']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if case.status != 'pending_review':
        return JsonResponse({'error': 'Case not pending review'}, status=400)
    
    try:
        correction_notes = request.POST.get('corrections', '')
        
        # Update case - approved with corrections
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.review_status = 'corrected'
        case.review_notes = correction_notes
        case.status = 'completed'
        case.save()
        
        # Create audit trail
        CaseReviewHistory.objects.create(
            case=case,
            reviewed_by=user,
            original_tech=case.assigned_to,
            review_action='corrected',
            review_notes=correction_notes
        )
        
        # Log what corrections were made
        log_audit_action(
            user=user,
            action='corrected_case_review',
            resource_type='case',
            resource_id=case.id,
            details={'corrections': correction_notes}
        )
        
        # Send notification
        send_correction_notification(case, user, correction_notes)
        
        messages.success(request, f'Case {case.external_case_id} corrected and approved')
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

---

### Priority 3: MEDIUM (UI & Notifications)

#### 3.1 Update Technician Dashboard

**File:** [cases/templates/cases/technician_dashboard.html](cases/templates/cases/technician_dashboard.html)

Add new section for Level 2/3 technicians:
```html
{% if user.user_level in 'level_2,level_3' %}
<div class="card mt-4">
    <div class="card-header bg-warning">
        <h5>Cases Pending Quality Review</h5>
    </div>
    <div class="card-body">
        <p>You have <strong>{{ pending_review_count }}</strong> cases awaiting review</p>
        <a href="{% url 'cases:review_queue' %}" class="btn btn-warning">
            Review Cases <i class="bi bi-arrow-right"></i>
        </a>
    </div>
</div>
{% endif %}
```

#### 3.2 Add Review Queue URL

**File:** [cases/urls.py](cases/urls.py)

```python
path('review-queue/', views.review_queue, name='review_queue'),
path('review/<int:case_id>/', views.review_case_detail, name='review_case_detail'),
path('review/<int:case_id>/approve/', views.approve_case_review, name='approve_case_review'),
path('review/<int:case_id>/request-revisions/', views.request_case_revisions, name='request_case_revisions'),
path('review/<int:case_id>/correct/', views.correct_case_review, name='correct_case_review'),
```

#### 3.3 Notification Functions

**File:** Create `cases/notifications.py`

```python
from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_review_approval_notification(case, reviewer):
    """Email Level 1 tech when case approved"""
    subject = f"Case {case.external_case_id} Approved by {reviewer.get_full_name()}"
    message = render_to_string('email/case_approved.html', {
        'case': case,
        'reviewer': reviewer,
    })
    send_mail(subject, message, from_email, [case.assigned_to.email])

def send_revision_request_notification(case, reviewer, feedback):
    """Email Level 1 tech when revisions requested"""
    subject = f"Case {case.external_case_id} Needs Revisions"
    message = render_to_string('email/revisions_needed.html', {
        'case': case,
        'reviewer': reviewer,
        'feedback': feedback,
    })
    send_mail(subject, message, from_email, [case.assigned_to.email])

def send_correction_notification(case, reviewer, corrections):
    """Email Level 1 tech when corrections made"""
    subject = f"Case {case.external_case_id} Corrected and Approved"
    message = render_to_string('email/case_corrected.html', {
        'case': case,
        'reviewer': reviewer,
        'corrections': corrections,
    })
    send_mail(subject, message, from_email, [case.assigned_to.email])
```

---

### Priority 4: LOW (Reporting & Analytics)

#### 4.1 Review Metrics Dashboard

**File:** Add to [core/views_reports.py](core/views_reports.py)

```python
def get_review_metrics(date_from=None, date_to=None):
    """Calculate quality review statistics"""
    
    from cases.models import CaseReviewHistory
    
    reviews = CaseReviewHistory.objects.all()
    if date_from:
        reviews = reviews.filter(reviewed_at__gte=date_from)
    if date_to:
        reviews = reviews.filter(reviewed_at__lte=date_to)
    
    total_reviews = reviews.count()
    approved = reviews.filter(review_action='approved').count()
    rejected = reviews.filter(review_action='sent_back').count()
    corrected = reviews.filter(review_action='corrected').count()
    
    approval_rate = (approved / total_reviews * 100) if total_reviews > 0 else 0
    
    # By reviewer
    by_reviewer = reviews.values(
        'reviewed_by__first_name',
        'reviewed_by__last_name'
    ).annotate(
        review_count=Count('id'),
        approval_pct=Case(
            When(review_action='approved', then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    )
    
    return {
        'total_reviews': total_reviews,
        'approved_count': approved,
        'rejected_count': rejected,
        'corrected_count': corrected,
        'approval_rate': approval_rate,
        'by_reviewer': list(by_reviewer),
    }
```

#### 4.2 Level 1 Tech "First-Time Approval Rate"

```python
def get_level_1_tech_quality_metrics():
    """Track quality of Level 1 technicians"""
    
    from accounts.models import User
    from cases.models import CaseReviewHistory
    
    level_1_techs = User.objects.filter(
        role='technician',
        user_level='level_1'
    )
    
    metrics = []
    for tech in level_1_techs:
        reviews = CaseReviewHistory.objects.filter(
            original_tech=tech
        )
        total = reviews.count()
        approved_first_time = reviews.filter(review_action='approved').count()
        
        rate = (approved_first_time / total * 100) if total > 0 else 0
        
        metrics.append({
            'tech_name': tech.get_full_name(),
            'total_reviewed': total,
            'approved_first_time': approved_first_time,
            'approval_rate': rate,
        })
    
    return metrics
```

---

## Part 3: Implementation Roadmap

### Phase 1: Database & Models (1-2 days)
1. ✅ Add missing fields to Case model (`reviewed_at`, `review_notes`, `review_status`)
2. ✅ Create `CaseReviewHistory` model
3. ✅ Run migrations
4. ✅ Test database changes

### Phase 2: Core Logic (2-3 days)
1. ✅ Modify `mark_case_completed()` to trigger review for Level 1
2. ✅ Create three review action endpoints (approve, reject, correct)
3. ✅ Add audit trail logging
4. ✅ Create notification functions
5. ✅ Unit tests

### Phase 3: UI & Dashboards (2-3 days)
1. ✅ Create review queue view
2. ✅ Create review detail template
3. ✅ Add review queue to dashboard
4. ✅ Create review action modals/forms
5. ✅ Create email templates

### Phase 4: Testing & Refinement (2-3 days)
1. ✅ Integration testing (Level 1 → Pending → Level 2 → Approved)
2. ✅ Test all three review actions
3. ✅ Test notifications
4. ✅ Verify audit trail
5. ✅ Performance testing

### Phase 5: Documentation & Deployment (1-2 days)
1. ✅ Update workflow documentation
2. ✅ Create admin guide
3. ✅ Update dashboard user guide
4. ✅ Deploy to staging/production

---

## Part 4: Testing Scenarios

### Test Case 1: Happy Path (Approval)
```
1. Level 1 tech completes case → status = 'pending_review'
2. Case appears in Level 2 tech's review queue
3. Level 2 tech clicks "Review"
4. Reviews case details and report
5. Clicks "APPROVE"
6. System:
   - Sets reviewed_by = Level 2 tech
   - Sets review_status = 'approved'
   - Sets status = 'completed'
   - Creates CaseReviewHistory entry
   - Sends notification to Level 1 tech
   - Releases case to member
7. Level 1 tech receives email: "Your case approved by Jane"
8. Member receives notification: "Report ready for download"
```

### Test Case 2: Revision Request
```
1. Level 1 tech completes case → status = 'pending_review'
2. Level 2 tech clicks "REQUEST CHANGES"
3. Adds notes: "Need more TSP analysis"
4. System:
   - Sets status = 'accepted' (back to working)
   - Creates CaseReviewHistory with action='sent_back'
   - Sends notification to Level 1 tech
5. Level 1 tech sees: "Case needs revisions: Need more TSP analysis"
6. Level 1 tech makes changes
7. Resubmits case → status = 'pending_review' again
8. Case goes back to Level 2/3 review queue
```

### Test Case 3: Correction by Reviewer
```
1. Level 1 tech completes case → status = 'pending_review'
2. Level 3 tech finds minor errors
3. Clicks "CORRECT & APPROVE"
4. Makes quick fixes to report
5. Adds notes: "Fixed TSP calculation, was..."
6. System:
   - Makes corrections
   - Sets status = 'completed'
   - Creates CaseReviewHistory with action='corrected'
   - Logs correction details to audit trail
7. Case immediately available to member
8. Both L1 tech and member notified of corrections
```

### Test Case 4: Permission Checks
```
- Level 1 tech cannot see review queue (403)
- Level 1 tech cannot approve cases (403)
- Level 2 tech cannot approve their own cases
- Admin can see all review queues
- Member cannot access review endpoints
```

---

## Part 5: Database Migration

### Required Migration

```python
# cases/migrations/XXXX_add_review_fields.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('cases', '0XXX_previous_migration'),
    ]

    operations = [
        # Add fields to Case
        migrations.AddField(
            model_name='case',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='case',
            name='review_notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='case',
            name='review_status',
            field=models.CharField(
                blank=True,
                choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('changes_requested', 'Changes Requested'), ('corrected', 'Corrected')],
                max_length=20,
                null=True,
            ),
        ),
        
        # Create CaseReviewHistory table
        migrations.CreateModel(
            name='CaseReviewHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('review_action', models.CharField(choices=[('approved', 'Approved'), ('sent_back', 'Sent Back for Revisions'), ('corrected', 'Corrected by Reviewer')], max_length=20)),
                ('review_notes', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(auto_now_add=True)),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_history', to='cases.case')),
                ('original_tech', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cases_reviewed_by_seniors', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cases_reviewed', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-reviewed_at'],
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='casereviewhistory',
            index=models.Index(fields=['case'], name='cases_case_r_case_id_idx'),
        ),
        migrations.AddIndex(
            model_name='casereviewhistory',
            index=models.Index(fields=['reviewed_by'], name='cases_case_r_reviewed_idx'),
        ),
        migrations.AddIndex(
            model_name='casereviewhistory',
            index=models.Index(fields=['reviewed_at'], name='cases_case_r_reviewed_at_idx'),
        ),
    ]
```

---

## Part 6: Risk Assessment

### High Risk Areas
1. **Trigger Logic:** Must be perfect - if Level 1 cases aren't set to pending_review, entire feature breaks
2. **Permissions:** Need strict checks - Level 1 techs must NOT be able to approve
3. **Notifications:** Email delivery must be reliable - don't want review decisions lost
4. **Rollback Plan:** If review feature causes issues, can disable by bypassing trigger

### Mitigation
- Thorough unit tests on trigger logic
- Integration tests simulating full workflow
- Test all permission combinations
- Comprehensive audit trail for debugging
- Feature flag to disable review (bypass to status='completed')

---

## Part 7: Effort Estimation

| Component | Effort | Priority | Dependencies |
|-----------|--------|----------|--------------|
| Models & Migration | 2 hrs | P1 | None |
| Review Trigger | 1 hr | P1 | Models |
| Review Actions (3x) | 6 hrs | P1 | Trigger |
| Review Queue View | 4 hrs | P2 | Models |
| Templates (4x) | 8 hrs | P2 | Views |
| Notifications | 4 hrs | P2 | Views |
| Testing | 8 hrs | P1 | All views |
| Documentation | 4 hrs | P4 | Complete |
| **TOTAL** | **37 hrs** | | |

**Timeline:** 1-2 weeks for full implementation (assuming ~6 hrs/day development)

---

## Summary Table: What Exists vs What's Needed

| Component | Current | Needed | Status |
|-----------|---------|--------|--------|
| User Levels | ✅ 3 levels | - | Ready |
| Case Model Fields | ✅ reviewed_by | ✅ reviewed_at, review_notes, review_status | 60% |
| Review Trigger | ❌ | ✅ modify mark_case_completed() | 0% |
| Review Queue View | ❌ | ✅ | 0% |
| Approve Action | ❌ | ✅ | 0% |
| Reject Action | ❌ | ✅ | 0% |
| Correct Action | ❌ | ✅ | 0% |
| Audit Table | ❌ | ✅ CaseReviewHistory | 0% |
| Notifications | ❌ | ✅ email/SMS | 0% |
| Dashboard UI | ❌ | ✅ review queue card | 0% |
| Templates | ❌ | ✅ 4 templates | 0% |
| Tests | ❌ | ✅ full coverage | 0% |
| Documentation | ❌ | ✅ update guides | 0% |

---

## Conclusion

The application has **the foundation** but is **missing 60-70% of the implementation**. The good news: the database schema is mostly ready, and the business logic is straightforward. The critical change is modifying `mark_case_completed()` to check technician level.

**Recommendation:** Prioritize Phase 1 & 2 (Models + Logic) first. Once the trigger is working, the UI and notifications can be added incrementally.

---

**End of Analysis Document**
