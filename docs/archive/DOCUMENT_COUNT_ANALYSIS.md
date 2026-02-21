# Document Count Verification Analysis - 01/11/2026

## Overview
This document analyzes the document counting logic across the application to verify that document counts are correct when documents are added both during initial case submission and during edit mode.

## Historical Context
Previously, the application had **two separate buckets** for documents:
1. **Federal Fact Finder** - The main form document
2. **Supporting Documents** - Additional files

This has been unified, but the counting logic needs verification.

## Current Document Type System

### Document Types (CaseDocument Model)
```python
DOCUMENT_TYPE_CHOICES = [
    ('fact_finder', 'Federal Fact Finder Form'),
    ('supporting', 'Supporting Document'),
    ('report', 'Generated Report'),
    ('other', 'Other'),
]
```

## Document Upload Flows

### 1. **Initial Case Submission** (`cases/views_submit_case.py`, lines 138-242)

**Location**: `submit_case()` view

**Upload Logic**:
```python
# All documents uploaded in submit form
if 'case_documents' in request.FILES:
    files = request.FILES.getlist('case_documents')
    for file in files:
        CaseDocument.objects.create(
            case=case,
            document_type='fact_finder',  # ← ALL stored as 'fact_finder'
            original_filename=filename_with_employee,
            file_size=file.size,
            uploaded_by=user,
            file=file,
        )

# Count verification (lines 176-179)
total_documents = case.documents.count()
ff_count = case.documents.filter(document_type='fact_finder').count()
support_count = case.documents.filter(document_type='supporting').count()
```

**ISSUE IDENTIFIED**:
- ✅ All documents uploaded initially are stored with `document_type='fact_finder'`
- ✅ Count is correct using `case.documents.count()`
- ✅ Breakdown shows all in FF, none in Supporting (accurate for initial submission)
- ✅ Message correctly displays counts

**Verification**: PASS

---

### 2. **Edit Draft Case - Document Upload** (`cases/views.py`, lines 1072-1130)

**Location**: `upload_technician_document()` view  
**Permission**: Members (draft cases), Technicians (any assigned), Admins

**Upload Logic**:
```python
# For members uploading to draft cases
doc_type = 'fact_finder' if user.role == 'member' else 'report'

CaseDocument.objects.create(
    case=case,
    document_type=doc_type,  # ← Either 'fact_finder' or 'report'
    original_filename=filename_with_employee,
    file_size=document_file.size,
    uploaded_by=user,
    file=document_file,
    notes=document_notes,
)
```

**Observations**:
- Members uploading to draft → stored as `'fact_finder'` ✅
- Technicians uploading to owned cases → stored as `'report'` (not `'supporting'`)
- No explicit count displayed, but upload success message shown
- Redirects to case_detail without showing document count

**Potential Issue**: 
- When technicians upload documents, they're stored as `'report'` type, not `'supporting'`
- This may skew the count if the system expects supporting documents

**Status**: NEEDS CLARIFICATION

---

### 3. **Member Document Upload to Completed Case** (`cases/views.py`, lines 1351-1400)

**Location**: `upload_member_document_to_completed_case()` view  
**Permission**: Members (their own cases, completed/accepted/pending_review/draft status)

**Upload Logic**:
```python
CaseDocument.objects.create(
    case=case,
    document_type='supporting',  # ← EXPLICITLY using 'supporting'
    original_filename=filename_with_employee,
    file_size=document_file.size,
    uploaded_by=user,
    file=document_file,
    notes=document_notes if document_notes else 'Member supplementary document',
)
```

**Observations**:
- ✅ Correctly stores as `'supporting'` type
- ✅ No count verification shown, but upload succeeds
- ✅ Message: "You can upload more documents before resubmitting"
- ✅ Total count would be accurate if previous uploads were all 'fact_finder'

**Verification**: PASS (for resubmission workflow)

---

## Count Verification Points

### A. Case.documents Relationship
```python
# In Case model (models.py)
class CaseDocument(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='documents')
```

**Query Method**: `case.documents.count()`
- ✅ Correctly returns total documents (all types)
- ✅ Filtered counts: `.filter(document_type='fact_finder').count()`

### B. Counting at Different Stages

| Stage | Count Method | Document Types Expected | Status |
|-------|-------------|------------------------|--------|
| **Initial Submit** | `case.documents.count()` | All as 'fact_finder' | ✅ Correct |
| **Member Edit (Draft)** | `.count()` not shown | New docs as 'fact_finder' | ⚠️ Not displayed |
| **Tech Upload (Owned)** | `.count()` not shown | New docs as 'report' | ⚠️ Not displayed |
| **Member Resubmit** | `.count()` not shown | Supplementary as 'supporting' | ⚠️ Not displayed |

---

## Potential Problems Identified

### Problem 1: Inconsistent Document Types
**Issue**: Different roles upload documents with different types
- Members → `'fact_finder'`
- Technicians → `'report'`
- Members (resubmit) → `'supporting'`

**Impact**: If counting specific types, totals might be misleading

**Current View Code** (submit_case.py:176-179):
```python
total_documents = case.documents.count()  # ✅ Correct (all types)
ff_count = case.documents.filter(document_type='fact_finder').count()
support_count = case.documents.filter(document_type='supporting').count()
# Missing: report count
report_count = case.documents.filter(document_type='report').count()  # NOT COUNTED!
```

**Impact**: If technician uploads document as 'report', it won't be shown in `ff_count` or `support_count`

---

### Problem 2: Edit Mode Doesn't Show Count
**Issue**: When documents are uploaded in edit mode (draft), no count confirmation shown
- Member uploads document → redirects to case_detail
- No message showing new document count
- User doesn't know if upload succeeded (only success message shown, not count)

**Affected Views**:
- `upload_technician_document()` - Line 1126
- Returns `messages.success()` but no count

---

### Problem 3: Dashboard Display May Be Wrong
**Issue**: Need to check how dashboards display document counts

---

## Recommendations

### 1. **Standardize Document Types During Upload**
All user-uploaded documents should use consistent types:
- **Option A**: All use `'supporting'` (most neutral)
- **Option B**: Track by role in separate field
- **Current**: Mixed usage causing confusion

### 2. **Include Full Count in All Upload Confirmations**
```python
# After any document upload:
total_count = case.documents.count()
type_counts = {
    'fact_finder': case.documents.filter(document_type='fact_finder').count(),
    'supporting': case.documents.filter(document_type='supporting').count(),
    'report': case.documents.filter(document_type='report').count(),
}

messages.success(
    request, 
    f'Document uploaded! Total: {total_count} '
    f'(Fact Finder: {type_counts["fact_finder"]}, '
    f'Supporting: {type_counts["supporting"]}, '
    f'Reports: {type_counts["report"]})'
)
```

### 3. **Create Helper Function for Count Verification**
```python
# In credit_service.py or new document_service.py
def get_document_counts(case):
    """Get all document counts for a case"""
    return {
        'total': case.documents.count(),
        'fact_finder': case.documents.filter(document_type='fact_finder').count(),
        'supporting': case.documents.filter(document_type='supporting').count(),
        'report': case.documents.filter(document_type='report').count(),
        'other': case.documents.filter(document_type='other').count(),
    }
```

### 4. **Verify Database State**
Need to run SQL query to check actual document type distribution:
```sql
SELECT 
    document_type, 
    COUNT(*) as count
FROM cases_casedocument
GROUP BY document_type;
```

---

## Summary of Findings

| Item | Status | Notes |
|------|--------|-------|
| Initial submission count | ✅ PASS | All documents correctly counted as 'fact_finder' |
| Edit mode uploads shown | ⚠️ PARTIAL | Uploads succeed but count not displayed |
| Document type consistency | ❌ FAIL | Different types used: fact_finder/report/supporting |
| Full count verification | ⚠️ PARTIAL | Only FF and Supporting counted, Reports ignored |
| Total count accuracy | ✅ PASS | `.count()` returns correct total |

---

## Next Steps

1. **Verify Database State**: Check actual document types in database
2. **Test Edit Workflow**: Upload document in draft mode and verify count
3. **Test Resubmit Workflow**: Upload supplementary documents and verify total
4. **Dashboard Verification**: Check if document counts display correctly on dashboards
5. **Implement Fix**: Standardize document types or update counting logic
