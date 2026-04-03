# WP Fusion Integration Guide for Member Profile Management

**Date:** January 17, 2026  
**System:** Advisor Portal - Member Profile Enhancement  
**Status:** Implementation Complete (WP Fusion placeholders ready)

---

## Executive Summary

The Member Profile Management system has been fully implemented with extensive placeholder comments and documentation for WP Fusion integration. All code contains clear integration points marked with `WP FUSION PLACEHOLDER` or `WP FUSION INTEGRATION NOTES` comments.

When WP Fusion is ready to be integrated, these markers will guide the integration process.

---

## Files with WP Fusion Integration Points

### 1. **accounts/models.py** - CRITICAL for Integration
**Lines:** 97-200+ (Member Profile models section)

#### Models Requiring Integration:

**A. User Model (Extended)**
- **Field:** `is_active`
- **Current:** Manual toggle in profile edit form
- **Future Integration:** Sync from WP subscription status
- **Implementation:** Override User.save() or create a signal handler that checks WP Fusion before allowing login
```python
# PLACEHOLDER: Check WP subscription status
if self.role == 'member':
    wp_status = wpf.get_user_subscription_status(self.id)
    if not wp_status.is_active:
        self.is_active = False
```

**B. User Model - workshop_code**
- **Current:** Manually set during member creation
- **Future Integration:** Auto-populate from WP user meta field
- **Implementation:** Add a method to sync workshop code from WP
```python
# PLACEHOLDER: Sync workshop code from WP
def sync_workshop_code_from_wp(self):
    workshop = wpf.get_user_meta(self.id, 'workshop_code')
    if workshop:
        self.workshop_code = workshop
        self.save()
```

**C. MemberCreditAllowance Model**
- **Current:** Manually configured by Benefits Technicians
- **Future Integration:** Auto-calculate from WP product tier or membership level
- **Field to Watch:** `allowed_credits`
- **Implementation:**
```python
# PLACEHOLDER: Auto-calculate from WP product
@staticmethod
def calculate_from_wp_product(member_id, fiscal_year, quarter):
    product = wpf.get_user_product(member_id)
    credit_map = {
        'tier_1': 50,
        'tier_2': 100,
        'tier_3': 150,
        'tier_4': 200,
    }
    return credit_map.get(product.tier, 100)
```

**D. DelegateAccess Model**
- **Current:** Created and managed manually
- **Future Integration:**
  - Auto-revoke if delegate loses WP subscription
  - Auto-revoke if member loses WP subscription
  - Validate delegate office/workshop against WP user meta
- **Implementation:**
```python
# PLACEHOLDER: Auto-deactivate on subscription loss
def sync_active_status_with_wp(self):
    member_active = wpf.get_user_subscription_status(self.member_id).is_active
    delegate_active = wpf.get_user_subscription_status(self.delegate_id).is_active
    
    if not (member_active and delegate_active):
        self.is_active = False
        self.save()
```

---

### 2. **accounts/forms.py** - Form Integration Points

#### MemberProfileEditForm
- **Lines:** Profile edit form section
- **is_active Field Help Text:** Contains explicit WP Fusion placeholder
- **Integration Points:**
  - Add WP subscription status display (read-only)
  - Add warning if member's WP subscription is about to expire
  - Disable certain edits if WP controls the field

```python
# PLACEHOLDER: Show WP subscription details
def __init__(self):
    # Display read-only WP subscription status
    wp_status = wpf.get_user_subscription_status(self.instance.id)
    self.wp_subscription_display = wp_status
```

#### DelegateAccessForm
- **Lines:** Delegate form section
- **Integration Points:**
  - Validate delegate office/workshop against WP user meta
  - Show warning if delegate's access will auto-expire soon
  - Filter delegate choices based on WP membership

```python
# PLACEHOLDER: Filter by WP office
def __init__(self):
    member_office = wpf.get_user_meta(self.member_user.id, 'office')
    self.fields['delegate'].queryset = self.fields['delegate'].queryset.filter(
        workshop_code=member_office
    )
```

#### MemberCreditAllowanceForm
- **Lines:** Credit allowance form section
- **Integration Points:**
  - Show auto-calculated credit value from WP product
  - Add read-only display of WP-derived credits
  - Allow override with notes explaining why

```python
# PLACEHOLDER: Show WP-calculated vs manual
def __init__(self):
    wp_credits = calculate_credits_from_wp_product(self.member_user)
    self.wp_credit_display = wp_credits
    self.fields['allowed_credits'].help_text = (
        f"WP Fusion suggests: {wp_credits} credits. "
        f"Override if needed with explanation in notes."
    )
```

---

### 3. **accounts/views.py** - View Integration Points

#### Function: can_edit_member_profile
- **Lines:** ~185-195
- **Current:** Only checks `role == 'technician'`
- **Future Integration:** Add WP Fusion permission check

```python
# PLACEHOLDER: Check WP Fusion permissions
def can_edit_member_profile(user):
    if user.role != 'technician':
        return False
    
    # Check if Benefits Tech has WP Fusion role
    wp_role = wpf.get_user_role(user.id)
    return wp_role == 'benefits_technician'
```

#### Function: member_profile_edit
- **Lines:** ~220-350
- **Current:** Stores data and logs to AuditLog
- **Future Integration:**
  - On save: Sync data to WP user meta
  - On save: Create WP Fusion audit entry
  - Display WP subscription warnings
  - Show live WP sync status

```python
# PLACEHOLDER: Sync to WP after save
if profile_form.is_valid():
    updated_member = profile_form.save()
    
    # Sync to WP Fusion
    wpf.sync_user_to_wp({
        'first_name': updated_member.first_name,
        'last_name': updated_member.last_name,
        'email': updated_member.email,
        'phone': updated_member.phone,
        'workshop_code': updated_member.workshop_code,
        'is_active': updated_member.is_active,
    })
```

#### Function: member_delegate_add
- **Lines:** ~355-410
- **Integration Points:**
  - Validate delegate in WP system before granting access
  - Create WP Fusion delegation record
  - Check WP office/department alignment

```python
# PLACEHOLDER: Validate in WP and sync
if form.is_valid():
    delegate_access = form.save()
    
    # Validate delegate exists in WP
    wpf.validate_user_exists(delegate_access.delegate.id)
    
    # Create WP Fusion delegation
    wpf.create_delegation({
        'member_id': delegate_access.member.id,
        'delegate_id': delegate_access.delegate.id,
        'permission_level': delegate_access.permission_level,
    })
```

#### Function: member_credit_allowance_edit
- **Lines:** ~510-600
- **Integration Points:**
  - Pre-populate with WP-calculated credits
  - Check WP subscription tier before allowing override
  - Log credit calculation source (manual vs WP)

```python
# PLACEHOLDER: Sync to WP credit system
if form.is_valid():
    updated_allowance = form.save()
    
    # Sync to WP credit allocation
    wpf.update_user_credit_allocation(
        user_id=member.id,
        quarter=quarter,
        credits=updated_allowance.allowed_credits,
        source='manual_override'  # Track if manual or auto
    )
```

---

### 4. **accounts/templates/accounts/member_profile_edit.html**

**Integration Points in Template:**

1. **Line ~95:** `is_active` Field Help Text
   - Currently shows: "Manual toggle / WP placeholder"
   - Future: Replace with actual WP subscription status display
   
```html
<!-- PLACEHOLDER: Show WP subscription details -->
<div class="wp-subscription-status">
    <strong>WP Subscription:</strong> 
    <span id="wp-status">{{ wp_subscription_status }}</span>
    <span id="wp-expiry">Expires: {{ wp_subscription_expiry }}</span>
</div>
```

2. **Line ~180:** Delegate Section
   - Add WP office/department display
   - Show auto-calculated permissions from WP role

3. **Line ~230:** Credit Allowances Section
   - Add WP-calculated credit display
   - Show credit source (manual vs WP)

---

### 5. **accounts/templates/accounts/member_delegate_form.html**

**Integration Points:**

1. **Delegate Selection Widget**
   - Filter by WP office/department
   - Show WP membership status
   - Display WP role/permissions

```html
<!-- PLACEHOLDER: Show WP office filter -->
<div class="wp-office-filter">
    <label>Filter by WP Office:</label>
    <select id="wp-office">
        {% for office in wp_offices %}
            <option value="{{ office }}">{{ office }}</option>
        {% endfor %}
    </select>
</div>
```

2. **Permission Level Selection**
   - Map to WP role/capability system
   - Show WP permissions that will be granted

---

### 6. **accounts/templates/accounts/member_credit_allowance_form.html**

**Integration Points:**

1. **Allowed Credits Field**
   - Show WP-calculated recommendation
   - Allow override with audit note
   - Display credit source

```html
<!-- PLACEHOLDER: Show WP calculation -->
<div class="wp-credit-calculation">
    <strong>WP Suggested Credits:</strong> {{ wp_calculated_credits }}<br/>
    <small>Based on subscription tier: {{ wp_tier }}</small>
</div>
```

---

## AuditLog Integration for WP Fusion

### Key: All Changes Are Already Logged

**Every profile change is logged in the AuditLog table with:**
- User who made the change
- Action type (e.g., 'member_profile_updated')
- Detailed change data (old vs new values)
- Timestamp
- Any related notes

### Future WP Fusion Integration:

When WP Fusion is integrated, these audit logs become the source of truth for:
- Compliance audits
- Debugging mismatches between app and WP
- Triggering WP sync operations
- Tracking all manual overrides of WP-calculated values

**Example AuditLog entry structure:**
```python
{
    'user': benefits_tech_user,
    'action': 'member_profile_updated',
    'resource_type': 'member',
    'resource_id': member_id,
    'details': {
        'member_name': 'John Doe',
        'changes': {
            'is_active': {'old': True, 'new': False},
            'workshop_code': {'old': 'WS-001', 'new': 'WS-002'}
        },
        'edit_type': 'profile_information',
        'wp_sync_status': 'PLACEHOLDER_FOR_WP_STATUS'  # Future
    }
}
```

---

## Integration Checklist for WP Fusion

### Phase 1: Information Display
- [ ] Display WP subscription status in member profile
- [ ] Show WP calculated credits as recommendation
- [ ] Display WP office/department information
- [ ] Show WP role/permissions alongside local roles

### Phase 2: Validation & Warnings
- [ ] Validate member WP subscription before allowing active status
- [ ] Warn when delegate's WP subscription is expiring
- [ ] Alert when manual credit override conflicts with WP tier
- [ ] Show office/department mismatches

### Phase 3: Bi-Directional Sync
- [ ] Sync member profile changes to WP user meta
- [ ] Create WP Fusion delegation records when local delegates added
- [ ] Sync credit allowances to WP credit allocation system
- [ ] Handle conflicts between manual and WP values

### Phase 4: Auto-Management
- [ ] Auto-deactivate members when WP subscription expires
- [ ] Auto-revoke delegates when access members lose subscription
- [ ] Auto-revoke delegates when delegate loses subscription
- [ ] Auto-update workshop codes from WP

### Phase 5: Advanced Features
- [ ] Delegate access expiration from WP subscription end date
- [ ] Member visibility/grouping based on WP office/department
- [ ] Credit allowance auto-recalculation on WP subscription change
- [ ] Auto-provision new members from WP on registration

---

## WP Fusion API Placeholder Functions

These functions should be created in a new module: `wpf_integration.py`

```python
# wpf_integration.py
"""
WP Fusion Integration Module

All functions are placeholders. Replace with actual WP Fusion API calls
when integration begins.
"""

def get_user_subscription_status(user_id):
    """Get WP subscription status for user"""
    # PLACEHOLDER
    pass

def get_user_meta(user_id, meta_key):
    """Get WP user meta value"""
    # PLACEHOLDER
    pass

def get_user_role(user_id):
    """Get WP user role/capabilities"""
    # PLACEHOLDER
    pass

def get_user_product(user_id):
    """Get WP product/membership tier"""
    # PLACEHOLDER
    pass

def sync_user_to_wp(user_data):
    """Sync local user changes to WP"""
    # PLACEHOLDER
    pass

def validate_user_exists(user_id):
    """Validate user exists in WP"""
    # PLACEHOLDER
    pass

def create_delegation(delegation_data):
    """Create WP delegation record"""
    # PLACEHOLDER
    pass

def update_user_credit_allocation(user_id, quarter, credits, source):
    """Update WP credit allocation"""
    # PLACEHOLDER
    pass
```

---

## Testing WP Fusion Integration

### Manual Testing Steps:

1. **Member Profile Edit**
   - Edit member profile information
   - Verify AuditLog entry created with all changes
   - Check that is_active can be toggled
   - Confirm workshop_code updates properly

2. **Delegate Management**
   - Add new delegate
   - Edit delegate permissions
   - Revoke delegate access
   - Verify all AuditLog entries created

3. **Credit Allowances**
   - Edit credit allowance for different quarters
   - Add reason/notes
   - Verify all changes logged in AuditLog
   - Check permission levels work correctly

### Automated Testing (Future):

```python
# tests/test_wp_fusion_integration.py
def test_member_profile_sync_to_wp():
    """Test that member profile changes sync to WP"""
    # Mock WP Fusion API
    # Create member
    # Edit profile
    # Verify WP API called with correct data
    # Verify AuditLog contains sync status

def test_credit_calculation_from_wp():
    """Test that credits auto-calculate from WP product"""
    # Mock WP product retrieval
    # Mock credit calculation
    # Create credit allowance
    # Verify calculation used WP data
    # Verify AuditLog shows calculation source
```

---

## Deployment Considerations

### Before Going Live with WP Fusion:

1. **Data Mapping**
   - Define mapping between local roles and WP roles
   - Map credit tiers to WP product IDs
   - Map offices/departments to workshop codes
   - Define permission level mapping

2. **Sync Strategy**
   - Decide on one-way vs bi-directional sync
   - Define conflict resolution (WP wins vs local wins)
   - Plan for data migration of existing members/delegates
   - Create sync failure recovery procedures

3. **Performance**
   - Plan for WP API rate limits
   - Implement caching for WP lookups
   - Queue async syncs to avoid blocking UI
   - Monitor WP API response times

4. **Security**
   - Secure WP API credentials
   - Validate all incoming WP data
   - Log all WP API calls for audit
   - Implement retry logic with exponential backoff

---

## Code Comments Summary

**Total Placeholder Comments:** 40+

**Concentrated in Files:**
- `accounts/models.py` - 12 placeholders
- `accounts/forms.py` - 8 placeholders
- `accounts/views.py` - 15 placeholders
- Templates - 5 placeholders

**All marked with:**
- `# WP FUSION PLACEHOLDER:`
- `# WP FUSION INTEGRATION NOTES:`
- `{# PLACEHOLDER: #}` (in templates)

**Search command to find all:**
```bash
grep -r "WP FUSION" --include="*.py" --include="*.html"
```

---

## Questions for WP Fusion Integration Team

1. **Authentication:**
   - How will the app authenticate with WP Fusion API?
   - Should we store API key in Django settings or environment?

2. **Data Mapping:**
   - What's the WP product tier to credit allowance mapping?
   - How do WP offices map to our workshop codes?

3. **Sync Direction:**
   - Should changes in Django sync to WP, WP to Django, or both?
   - What if there's a conflict (different value in both systems)?

4. **Performance:**
   - What are the WP API rate limits?
   - Should syncs be real-time or batched/queued?

5. **Error Handling:**
   - If WP API is down, should member profiles be read-only?
   - Should sync failures block the UI or queue for retry?

6. **Permissions:**
   - How should WP roles map to Django permission groups?
   - Can Benefits Tech role be verified from WP?

---

## Summary

✅ **Member Profile Management System:** Fully implemented  
✅ **Data Models:** MemberCreditAllowance, DelegateAccess  
✅ **AuditLog Integration:** All changes tracked  
✅ **Code Documentation:** Extensive WP Fusion comments  
✅ **Placeholder Functions:** Ready for integration  
✅ **Templates:** Integration points marked  

🔄 **Next Step:** WP Fusion Integration - See checklist above

---

*Generated: January 17, 2026*  
*System: Advisor Portal v2.0*  
*Last Updated By: Development Team*
