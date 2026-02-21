# Dashboard Column Visibility Analysis & Implementation Plan

## Overview
Analysis of all dashboard views to identify columns that can be hidden/made optional for improved usability and screen real estate management.

---

## Current Dashboard Analysis

### 1. Member Dashboard (member_dashboard.html)
**Current Columns (5 total):**
1. **Case ID** (Workshop Code)
2. **Member Name** 
3. **Submitted Date**
4. **Accepted Date**
5. **Status/Actions** (Download, View, Resubmit buttons)

**Candidate for Hiding:**
- ✅ **Accepted Date** - LOW PRIORITY (some members may not care about this)
- ❌ All other columns are essential for member workflow

**Note:** Member dashboard is already minimal and focused. Low need for column hiding.

---

### 2. Technician Dashboard (technician_dashboard.html)
**Current Columns (14-15 visible, was 18):**
1. ✅ Workshop Code (essential)
2. Member Name (essential)
3. Employee Name (essential)
4. Submitted Date (essential)
5. Due Date (essential)
6. Urgency (essential - critical filter)
7. **Status** (essential)
8. **Release Date** (OPTIONAL - only for completed cases)
9. **Reports** (OPTIONAL - not all cases have reports)
10. Assigned To (essential)
11. Date Scheduled (OPTIONAL - only for scheduled cases)
12. Tier (OPTIONAL - administrative info)
13. **Reviewed By** (OPTIONAL - not always relevant)
14. **Notes** (OPTIONAL - can be viewed in detail page)
15. Actions (essential)

**Candidates for Hiding:**
- ✅ **Reviewed By** - Can be seen in case details
- ✅ **Notes** - Summary available in detail page
- ✅ **Date Scheduled** - Only relevant for scheduled cases
- ✅ **Tier** - Administrative, not critical for day-to-day work
- ✅ **Reports** - Can be accessed from case detail

**Columns to KEEP Visible by Default:**
- ✅ Code, Member, Employee, Submitted, Due, Urgency, Status, Release Date, Assigned To, Actions

---

### 3. Manager Dashboard (manager_dashboard.html)
**Current Columns (14-15 visible, same as Tech):**
1. Workshop Code (essential)
2. Member Name (essential)
3. Employee Name (essential)
4. Submitted Date (essential)
5. Due Date (essential)
6. Urgency (essential)
7. Status (essential)
8. Release Date (OPTIONAL)
9. Reports (OPTIONAL)
10. Assigned To (essential)
11. Date Scheduled (OPTIONAL)
12. Tier (OPTIONAL)
13. Reviewed By (OPTIONAL)
14. Notes (OPTIONAL)
15. Actions (essential)

**Candidates for Hiding:** Same as Technician Dashboard
- ✅ **Reviewed By** 
- ✅ **Notes**
- ✅ **Date Scheduled**
- ✅ **Tier**
- ✅ **Reports**

---

### 4. Admin Dashboard (admin_dashboard.html)
**Current Columns:** Same as Manager (14-15)

**Additional Admin Needs:**
- May want additional columns like member email for contact purposes
- User assignment is crucial

**Candidates for Hiding:** Same as above + potentially member email if it's displayed

---

### 5. Advisor Dashboard (advisor_dashboard.html)
**Current Columns:** Similar structure, likely 10-12 columns

---

## Proposed Solution

### Option A: Column Visibility Toggle (RECOMMENDED)
**Implementation:**
1. Add "Columns" button in filter bar (near Search/Filter buttons)
2. Dropdown menu with checkboxes for each optional column
3. Save user preference to `UserPreference` model with key like `dashboard_visible_columns_<role>`
4. Use JavaScript to show/hide columns via CSS classes
5. Persist across sessions

**Advantages:**
- ✅ Most flexible - users choose what they want
- ✅ No data loss - just visibility preference
- ✅ Works for all dashboard types
- ✅ Future-proof for new columns

**Disadvantages:**
- ❌ Requires more JavaScript for show/hide logic
- ❌ Slightly more complex implementation

---

## Implementation Strategy

### Phase 1: Column Visibility Toggle
**Steps:**
1. Create column configuration in backend (views.py)
2. Add "Columns" button with dropdown menu in each dashboard
3. Implement JavaScript to toggle column visibility
4. Save/load preferences via AJAX endpoint
5. Apply CSS to hide columns dynamically

### Phase 2: Smart Defaults
**Set Default Visibility:**
- **Technician/Manager:** Hide "Reviewed By", "Notes", "Tier" by default
- **Admin:** Show all columns by default
- **Member:** Show all (only 5 columns anyway)
- **Advisor:** Hide "Tier", "Reviewed By" by default

### Phase 3: Column Grouping (Future)
Could group columns into categories:
- Core Info (Code, Member, Employee)
- Dates (Submitted, Due, Scheduled, Release)
- Status (Status, Urgency, Assigned To)
- Admin (Tier, Reviewed By, Notes)

---

## Recommended Columns to Hide by Default

### Technician & Manager Dashboards:
**Hide by default (show in menu):**
1. ✅ `reviewed_by` - "Reviewed By"
2. ✅ `notes` - "Notes" 
3. ✅ `tier` - "Tier"
4. ✅ `date_scheduled` - "Date Scheduled"
5. ✅ `reports` - "Reports"

**Show by default (always visible unless hidden):**
1. Code
2. Member Name
3. Employee Name
4. Submitted Date
5. Due Date
6. Urgency
7. Status
8. Release Date
9. Assigned To
10. Actions

**Total Visible by Default:** 10 columns (vs 15 currently)
**Space Savings:** ~33% table width reduction

---

## Implementation Details

### Backend Changes (cases/views.py):
```python
# Define column options for each role
COLUMN_OPTIONS = {
    'technician': {
        'visible_by_default': ['code', 'member', 'employee', 'submitted', 'due', 'urgency', 'status', 'release_date', 'assigned_to', 'actions'],
        'available': ['code', 'member', 'employee', 'submitted', 'due', 'urgency', 'status', 'release_date', 'reports', 'assigned_to', 'date_scheduled', 'tier', 'reviewed_by', 'notes', 'actions'],
    },
    'manager': { ... same as technician ... },
    'admin': { ... all visible by default ... },
    'member': { ... all visible (only 5) ... },
}

# In view function:
def technician_dashboard(request):
    ...
    # Get user's column preferences or use defaults
    visible_columns = get_user_column_preferences(request.user, 'technician_dashboard')
    context['visible_columns'] = visible_columns
    context['available_columns'] = COLUMN_OPTIONS['technician']['available']
    ...
```

### Template Changes:
```html
<!-- Add Column Visibility Button -->
<button type="button" class="btn btn-sm btn-outline-secondary" data-bs-toggle="dropdown">
    <i class="bi bi-columns"></i> Columns
    <span class="badge bg-info" id="hidden-count"></span>
</button>
<div class="dropdown-menu">
    {% for col in available_columns %}
    <div class="form-check dropdown-item">
        <input class="form-check-input column-toggle" type="checkbox" 
               data-column="{{ col.id }}" 
               id="col_{{ col.id }}"
               {% if col.id in visible_columns %}checked{% endif %}>
        <label class="form-check-label" for="col_{{ col.id }}">
            {{ col.label }}
        </label>
    </div>
    {% endfor %}
</div>

<!-- In table header/body: -->
<th class="column-{{ col.id }}" {% if col.id not in visible_columns %}style="display:none;"{% endif %}>
    {{ col.label }}
</th>
```

### JavaScript for Toggling:
```javascript
document.querySelectorAll('.column-toggle').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const colId = this.dataset.column;
        const isVisible = this.checked;
        
        // Toggle visibility
        document.querySelectorAll('.column-' + colId).forEach(el => {
            el.style.display = isVisible ? '' : 'none';
        });
        
        // Save preference
        saveColumnPreference(colId, isVisible);
        
        // Update hidden count badge
        updateHiddenCount();
    });
});

function saveColumnPreference(colId, isVisible) {
    fetch('/api/column-preference/save/', {
        method: 'POST',
        headers: {'X-CSRFToken': getCsrfToken()},
        body: JSON.stringify({
            dashboard: 'technician_dashboard',  // or manager, admin, etc
            column: colId,
            visible: isVisible
        })
    });
}
```

---

## API Endpoint Needed

### Save Column Preference
**Endpoint:** `/api/column-preference/save/`
**Method:** POST
**Body:**
```json
{
    "dashboard": "technician_dashboard",
    "column": "reviewed_by",
    "visible": false
}
```
**Stores in:** `UserPreference` with key like `dashboard_columns_technician_dashboard`

---

## Rollout Plan

1. **Week 1:** Implement for Technician Dashboard (highest priority - most columns)
2. **Week 2:** Implement for Manager Dashboard
3. **Week 3:** Implement for Admin Dashboard  
4. **Week 4:** Optional for Member & Advisor dashboards

---

## Benefits Summary

✅ **For Users:**
- Reduced visual clutter
- Faster scanning of relevant data
- Personalized view per user
- Can show hidden columns when needed

✅ **For System:**
- Improved UX without major restructuring
- Data still available, just hidden
- Easy to add new columns in future
- Preferences saved per user

✅ **Screen Space:**
- ~33% reduction in table width
- Better mobile responsiveness
- Reduced horizontal scrolling

---

## Success Metrics

1. Users regularly hide "Reviewed By", "Notes", "Tier" columns
2. Page load time improved (less rendering)
3. User satisfaction increases
4. Fewer support requests about "too many columns"

