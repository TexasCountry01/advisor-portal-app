# Member Profile Management Architecture Analysis

## Executive Summary
This document analyzes the request to add editable member profiles with delegate authority, credit management, and linked advisor pools. This is a significant feature requiring thoughtful database and UI design.

---

## Current State Analysis

### Problem Statement
- Member profiles are **write-once** after creation
- Cannot update: email, workshop code, active/inactive status
- Credits cannot be managed per quarter
- No delegate access system exists
- No advisor linking/pooling mechanism

### What Works Today
- Members created during case submission
- User model has `is_active` field (used globally)
- Basic role-based access control exists
- Benefits Techs have elevated permissions

---

## Proposed Solution Architecture

### 1. MEMBER PROFILE EDITABILITY

**Model Changes Required:**

```python
class User (Member extends AbstractUser):
    # EXISTING
    username, email, first_name, last_name
    role = 'member'
    workshop_code
    is_active
    created_at
    
    # ADD NEW
    # Profile Information
    profile_active_status = BooleanField(default=True)  # Member-specific active flag (not is_active)
    profile_updated_by = ForeignKey(User, null=True)    # Which tech updated
    profile_updated_at = DateTimeField(null=True)       # When updated
    
    # Advisor Pool (new)
    advisor_pool = ForeignKey(AdvisorPool, null=True)   # Links to shared pool
```

**New Model: AdvisorPool**
```python
class AdvisorPool(models.Model):
    """Shared credit pool for multiple advisors working together"""
    name = CharField(max_length=200)  # "Tech Team A", "Regional Benefits"
    members = ManyToMany(User, related_name='advisor_pools')
    created_at = DateTimeField(auto_now_add=True)
    created_by = ForeignKey(User, on_delete=models.SET_NULL)
    
    def get_total_available_credits(self, quarter):
        """Sum all advisors' credits for quarter"""
        return sum(m.get_credits_for_quarter(quarter) for m in self.members.all())
```

**New Model: MemberCredit**
```python
class MemberCredit(models.Model):
    """Quarterly credit allocation per member"""
    member = ForeignKey(User, on_delete=models.CASCADE, related_name='credits')
    quarter = CharField(choices=[
        ('Q1', 'Q1 (Jan-Mar)'),
        ('Q2', 'Q2 (Apr-Jun)'),
        ('Q3', 'Q3 (Jul-Sep)'),
        ('Q4', 'Q4 (Oct-Dec)'),
    ])
    year = IntegerField()  # 2026, 2027, etc
    credit_value = DecimalField(max_digits=10, decimal_places=2)
    allocated_by = ForeignKey(User, on_delete=models.SET_NULL, null=True)
    allocated_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('member', 'quarter', 'year')
```

**Permissions:**
- Only Benefits Techs can edit member profiles
- Only Managers/Admins can create/manage advisor pools
- Editable fields: workshop_code, profile_active_status, credits, delegates

---

### 2. DELEGATE AUTHORITY ARCHITECTURE

**New Model: DelegateAccess**
```python
class DelegateAccess(models.Model):
    """Maps member to delegates who can act on their behalf"""
    member = ForeignKey(User, on_delete=models.CASCADE, related_name='delegates')
    delegate = ForeignKey(User, on_delete=models.CASCADE, related_name='delegating_to_members')
    permission_level = CharField(choices=[
        ('view_only', 'View Only - Read reports/documents'),
        ('submit_cases', 'Submit Cases - Create new cases'),
        ('manage_credits', 'Manage Credits - Modify quarterly credits'),
        ('full_access', 'Full Access - All member actions'),
    ])
    created_at = DateTimeField(auto_now_add=True)
    created_by = ForeignKey(User, on_delete=models.SET_NULL, null=True)  # Tech who set it up
    
    class Meta:
        unique_together = ('member', 'delegate')
```

**⚠️ CRITICAL DESIGN DECISION: Delegate Authority Location**

#### Option A: Set in Member Profile (RECOMMENDED)
```
Flow:
Tech → Member Profile → Delegates Tab → Add New Delegate
     → Select from dropdown: "Alice Johnson", "Bob Smith"
     → Select permission: "Submit Cases"
     → Save
     
Result:
- Member profile shows: [Alice (Submit Cases), Bob (View Only)]
- Delegate view shows reverse: [Members where I'm delegated]
```

**Advantages:**
- Single source of truth (member profile)
- Tech sees all member's delegates in one place
- Easier to revoke/edit
- Audit trail clear

**Disadvantages:**
- Need to search member to grant delegate access
- Delegate can't initiate their own access request

#### Option B: Set in Delegate Profile (NOT RECOMMENDED)
- Confusing for tech (split view)
- Harder to audit
- Risk of duplicate entries
- More complex sync logic

#### Option C: Bidirectional (COMPLEX BUT POWERFUL)
```
Tech can set in either:
1. Member Profile: "Grant Alice access to this member"
2. Delegate Profile: "This person can act for [Member List]"

Both create same DelegateAccess record
Dashboard shows both perspectives
```

**Recommendation: OPTION A + Reverse View**
- Set in Member Profile (primary)
- Delegate Dashboard shows "Members delegating to me"
- Can see all members I have access to
- Tech fully controls through member management

---

### 3. SHARED ADVISOR POOL ARCHITECTURE

**Problem**: Multiple advisors share credit pool
- Tech A & Tech B work together
- Combined monthly budget: $10,000
- Each has $5,000 individually allocated
- Need to see shared pool status

**Solution: AdvisorPool Model**

```python
class AdvisorPool(models.Model):
    name = "Regional Benefits Team"
    description = "Tech A and Tech B shared workspace"
    members = [Tech A, Tech B]  # ManyToMany
    
    Q1_2026_credits = 10,000
    Q1_2026_used = 3,500
    Q1_2026_remaining = 6,500
```

**Dashboard View:**
```
┌─ Advisor Pool: Regional Benefits ─────────┐
│ Members: Alice (Tech), Bob (Tech)          │
│ Q1 2026: $10,000 pool                      │
│   - Alice's members: $3,200 used           │
│   - Bob's members: $2,100 used             │
│   - Pool remaining: $4,700                 │
│                                             │
│ ⚠️ Alert: 47% of pool used (High)         │
└─────────────────────────────────────────────┘
```

**Data Model:**
```python
# Tech creates pool and adds members
pool = AdvisorPool.objects.create(
    name="Regional Benefits",
    created_by=admin_user
)
pool.members.add(tech_a, tech_b)

# Members linked to pool
member1.advisor_pool = pool
member1.save()

# Credits now aggregate across pool
pool.get_total_available_credits(quarter='Q1', year=2026)
# Returns: 10,000 (sum of all members' Q1 2026 credits)
```

---

### 4. MEMBER PROFILE UI MOCKUP

```
┌─────────────────────────────────────────────────────────┐
│ MEMBER PROFILE - Jane Doe                   [Edit] [Save]│
├─────────────────────────────────────────────────────────┤
│                                                          │
│ BASIC INFORMATION                                       │
│ ├─ Name: Jane Doe                                       │
│ ├─ Email: jane.doe@company.com         [✏️ editable]   │
│ ├─ Username: jane.doe                   [read-only]    │
│ └─ Created: Jan 15, 2026               [read-only]    │
│                                                          │
│ MEMBER STATUS                                           │
│ ├─ Active Status: ● Active  ○ Inactive  [✏️ editable] │
│ │  (Controls case submission ability)                  │
│ └─ Last Updated: Jan 16, 2026 by Alice  [read-only]   │
│                                                          │
│ WORKSHOP CONFIGURATION                                  │
│ ├─ Workshop Code: WS-2026-001         [✏️ editable]   │
│ ├─ Advisor Pool: Regional Benefits     [✏️ editable]   │
│ └─ (Multi-select or dropdown)                          │
│                                                          │
│ QUARTERLY CREDITS                                       │
│ ├─ Q1 2026: $5,000                    [✏️ editable]   │
│ ├─ Q2 2026: $5,000                    [✏️ editable]   │
│ ├─ Q3 2026: $5,000                    [✏️ editable]   │
│ └─ Q4 2026: $5,000                    [✏️ editable]   │
│                                                          │
│ DELEGATE ACCESS                                         │
│ ├─ Alice Johnson      (Submit Cases)    [🗑️ remove]   │
│ ├─ Bob Smith          (Full Access)     [🗑️ remove]   │
│ ├─ [+ Add Delegate]                                     │
│ │  ├─ Select: [Dropdown of all users]                 │
│ │  ├─ Permission: [Submit Cases ▼]                    │
│ │  └─ [Add]                                            │
│ └─                                                      │
│                                                          │
│ [Update Profile]  [Cancel]  [Deactivate Account]       │
└─────────────────────────────────────────────────────────┘
```

---

### 5. WORKFLOW: TECH UPDATING MEMBER PROFILE

```
Tech (Benefits Technician) Workflow:

START: Admin Dashboard
  │
  ▼
Member Management
  │
  ├─ Search: "Jane Doe"
  │
  ▼
Member Profile Card
  │
  ├─ Click [Edit]
  │
  ▼
Edit Member Form
  │
  ├─ Email: jane.doe@company.com → jane.newemail@company.com
  ├─ Workshop: WS-2026-001 → WS-2026-002
  ├─ Q1 Credits: $5,000 → $6,000
  ├─ Status: Active → [stays same]
  ├─ Delegates: [Add Bob Smith - Submit Cases permission]
  │
  ▼
[Update Profile]
  │
  ▼
Validation:
  ├─ Email: Valid? ✓
  ├─ Credits: Positive? ✓
  ├─ Delegates: Exist? ✓
  │
  ▼
Save to DB:
  ├─ Update User fields (email, workshop_code)
  ├─ Create/update MemberCredit records (Q1-Q4 2026)
  ├─ Create DelegateAccess records
  ├─ Log audit trail: "Tech Alice modified Jane's profile"
  │
  ▼
Success Message:
"Jane Doe's profile updated"
"Notification sent to Jane about changes"
  │
  ▼
END
```

---

### 6. DELEGATE AUTHORITY WORKFLOW

**Scenario: Bob Smith acting as delegate for Jane Doe**

```
Bob's Dashboard:
├─ My Cases: 5
├─ Members I Manage (Delegates): 2
│  ├─ Jane Doe (Submit Cases, View Reports)
│  └─ Sarah Johnson (Full Access)
│
When Bob clicks "Jane Doe":
├─ Can: Submit cases as if Jane
├─ Can: View Jane's reports
├─ Cannot: Modify Jane's profile (tech-only)
├─ Cannot: Change delegate access (tech-only)
│
Audit Trail:
├─ Case submitted: "Case 1234 submitted by Bob Smith (delegate for Jane Doe)"
├─ All actions tagged with delegate relationship
└─ Tech/Admin can review: "All actions Bob took for Jane"
```

---

### 7. SHARED POOL WORKFLOW

**Scenario: Regional Benefits Team manages $10,000 Q1 budget**

```
Admin Setup:
├─ Create: AdvisorPool "Regional Benefits"
├─ Add Members: Tech Alice, Tech Bob
├─ Set Q1 Credits: $10,000

Each Tech's Members:
├─ Alice's members:
│  ├─ Member A: $3,000 Q1 allocation
│  └─ Member B: $2,000 Q1 allocation  → Total: $5,000
│
├─ Bob's members:
│  ├─ Member C: $3,500 Q1 allocation
│  └─ Member D: $1,500 Q1 allocation  → Total: $5,000

Pool Dashboard:
├─ Pool: Regional Benefits
├─ Total: $10,000
├─ Used: $5,000 (Alice: $5,000 + Bob: $5,000)
│         Wait, this exceeds pool!
├─ ⚠️ ALERT: Over allocation! $10,000 pool / $10,000 used
└─ Recommendation: Increase pool or reduce individual allocations

Auto-enforcement options:
├─ Option 1: Reject case if credits exceeded
├─ Option 2: Warn but allow (review later)
├─ Option 3: Pull from other techs' unallocated
```

---

## Implementation Roadmap

### Phase 1: Core Member Profile Editing (Week 1)
- [ ] Create MemberCredit model
- [ ] Create profile edit form (Tech permission)
- [ ] Update views: member_detail, edit_member
- [ ] Add UI: email, workshop_code, active_status editors
- [ ] Add audit logging

### Phase 2: Quarterly Credits (Week 2)
- [ ] Quarterly credit allocation UI
- [ ] Q1-Q4 input fields in profile
- [ ] Credit balance calculations
- [ ] Dashboard displays available vs used

### Phase 3: Delegate Authority (Week 3)
- [ ] Create DelegateAccess model
- [ ] Delegate dropdown selection
- [ ] Permission level choices
- [ ] Add/remove delegate buttons
- [ ] Member profile shows delegates list

### Phase 4: Advisor Pools (Week 4)
- [ ] Create AdvisorPool model
- [ ] Admin pool creation/management
- [ ] Member → Pool assignment
- [ ] Pool dashboard with aggregated credits
- [ ] Over-allocation warnings

### Phase 5: Delegate Dashboard (Week 5)
- [ ] Delegate sees "Members delegating to me"
- [ ] Permission-based view filtering
- [ ] Delegate can submit cases as member
- [ ] Audit trail integration

---

## Security & Audit Considerations

### Permission Model
```python
# Only Benefits Tech can edit:
- Email
- Workshop code
- Active/inactive status
- Credits
- Delegates

# Only Admin can:
- Delete members (→ soft delete/deactivate)
- Manage advisor pools
- Modify delegate permissions (future)

# WP Fusion controls:
- Password
- 2FA
- SSO/LDAP sync
```

### Audit Trail
```python
class AuditLog(models.Model):
    action = "member_profile_updated"
    member = jane_doe
    actor = tech_alice
    changes = {
        'email': ('old@', 'new@'),
        'workshop_code': ('WS-001', 'WS-002'),
        'credits_q1': (5000, 6000),
        'delegates_added': ['bob_smith'],
    }
    timestamp = now
    reason = "Quarterly adjustment"
```

---

## WP Fusion Integration (Future)

### Current State (Workaround - Jan 2026)
This system will operate independently until WP Fusion integration is available. All functionality below will be handled in our system with placeholders for future WP Fusion sync.

### Fields Awaiting WP Fusion Integration

| Field | Current (System) | Future (WP Fusion) | Transition |
|---|---|---|---|
| **Password** | System controlled | WP Fusion SSO | System → WP Fusion (one-time sync) |
| **Email** | System editable | WP Fusion source | WP Fusion push to system |
| **Active/Inactive** | System flag `profile_active_status` | WP Fusion user status | System now, sync with WP later |
| **2FA/MFA** | Not implemented | WP Fusion controls | Later: read from WP Fusion |
| **LDAP/Directory** | Not implemented | WP Fusion syncs | Later: auto-sync from WP Fusion |

### WP Fusion Integration Architecture

**Current Placeholder Locations:**

```python
# In accounts/models.py
class User(AbstractUser):
    # WORKAROUND: System manages active status for now
    # TODO-WPFUSION: Remove is_active sync when WP Fusion integration ready
    # WP Fusion integration hook: wpfusion_sync_status()
    
    # System-of-truth for now (until WP Fusion ready)
    profile_active_status = BooleanField(default=True, help_text="TEMPORARY: Will sync with WP Fusion")
    
    # TODO-WPFUSION: Add field for WP Fusion user ID mapping
    wpfusion_user_id = CharField(max_length=255, null=True, blank=True, help_text="External WP Fusion ID")
    
    # TODO-WPFUSION: Add flag for sync status
    wpfusion_synced = BooleanField(default=False, help_text="Last synced with WP Fusion")
    wpfusion_sync_timestamp = DateTimeField(null=True, blank=True)


# In accounts/services/wpfusion_service.py (NEW FILE - stub for future)
class WPFusionService:
    """
    PLACEHOLDER for future WP Fusion integration.
    
    This service will handle:
    - User creation/update sync with WP Fusion
    - Password sync (one-time)
    - Email sync
    - Active/inactive status sync
    - SSO authentication
    - Directory sync (LDAP/Active Directory via WP Fusion)
    
    Current status: NOT IMPLEMENTED
    Target: Q2 2026 (when WP Fusion integration is ready)
    """
    
    def sync_user_to_wpfusion(self, user):
        """
        TODO-WPFUSION: Implement this when WP Fusion API ready
        
        Will push user data to WP Fusion:
        - Email → update
        - Active status → sync
        - Custom fields → sync
        """
        # For now: just log intention
        logger.info(f"[WP FUSION PLACEHOLDER] Would sync user {user.username} to WP Fusion")
        pass
    
    def sync_active_status_from_wpfusion(self, user):
        """
        TODO-WPFUSION: Implement when WP Fusion ready
        
        Currently: System is source of truth
        Eventually: Read active status from WP Fusion
        """
        logger.info(f"[WP FUSION PLACEHOLDER] Would fetch active status for {user.username} from WP Fusion")
        pass
    
    def authenticate_with_wpfusion(self, email, password):
        """
        TODO-WPFUSION: Implement SSO when WP Fusion ready
        
        Currently: Django auth
        Eventually: WP Fusion SSO
        """
        logger.info(f"[WP FUSION PLACEHOLDER] Would authenticate {email} via WP Fusion SSO")
        pass
```

**In forms/views when editing member:**

```python
# accounts/forms.py - MemberProfileForm
class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'workshop_code', 'profile_active_status']
    
    def save(self, commit=True):
        user = super().save(commit=True)
        
        # System update: DONE
        # TODO-WPFUSION: After save, sync to WP Fusion
        # from accounts.services.wpfusion_service import WPFusionService
        # WPFusionService().sync_user_to_wpfusion(user)
        
        return user
```

### Integration Timeline & Steps

**Phase 1: Placeholder Phase (Jan 2026 - NOW)**
- System manages all: password, email, active status, credits
- Marked with `TODO-WPFUSION` comments
- All fields independently editable
- Audit trail logged locally

**Phase 2: WP Fusion API Ready (Expected Q2 2026)**
1. WP Fusion provides API credentials & documentation
2. Uncomment `wpfusion_service.py` code
3. Implement each sync method:
   - `sync_user_to_wpfusion()` - push updates
   - `sync_active_status_from_wpfusion()` - pull status
   - `authenticate_with_wpfusion()` - SSO
4. Test bidirectional sync

**Phase 3: Gradual Migration (Q2-Q3 2026)**
1. First: One-time migration of existing users to WP Fusion
2. Map: `system_user_id` → `wpfusion_user_id`
3. Verify: Email and status match
4. Enable: Real-time sync (user edits trigger WP Fusion updates)

**Phase 4: Source of Truth Flip (Q3 2026)**
1. Disable: Direct system editing of certain fields (email, password)
2. Enable: Read-only display of WP Fusion data
3. Redirect: "Update email in WP Fusion" message
4. Monitor: Sync errors & conflicts

### Specific Integration Points

**1. User Creation**
```python
# Current (System only)
user = User.objects.create(
    email='jane@company.com',
    username='jane.doe',
    role='member'
)

# Future (System + WP Fusion)
# TODO-WPFUSION: After create, also create in WP Fusion
# WPFusionService().create_user_in_wpfusion(user)
```

**2. Email Update**
```python
# Current: Direct system edit
user.email = 'newemail@company.com'
user.save()

# Future: 
# Option A: Sync to WP Fusion immediately
# TODO-WPFUSION: WPFusionService().sync_user_to_wpfusion(user)

# Option B: Disable edit, tell tech "update in WP Fusion"
# if settings.WP_FUSION_ENABLED:
#     raise PermissionError("Update email in WP Fusion, not here")
```

**3. Active Status Toggle**
```python
# Current: System controls
user.profile_active_status = False
user.save()

# Future: Also sync to WP Fusion
# TODO-WPFUSION: WPFusionService().sync_active_status_to_wpfusion(user)

# Or: Read from WP Fusion
# if settings.WP_FUSION_ENABLED:
#     status = WPFusionService().get_active_status_from_wpfusion(user)
```

**4. Authentication**
```python
# Current: Django built-in
authenticate(username=email, password=password)

# Future: WP Fusion SSO
# if settings.WP_FUSION_ENABLED:
#     WPFusionService().authenticate_with_wpfusion(email, password)
# else:
#     authenticate(username=email, password=password)
```

### Settings Configuration

```python
# config/settings.py
WP_FUSION_ENABLED = os.getenv('WP_FUSION_ENABLED', 'False') == 'True'
WP_FUSION_API_KEY = os.getenv('WP_FUSION_API_KEY', None)
WP_FUSION_API_URL = os.getenv('WP_FUSION_API_URL', None)
WP_FUSION_SITE_ID = os.getenv('WP_FUSION_SITE_ID', None)

# When WP Fusion is ready, set in .env:
# WP_FUSION_ENABLED=True
# WP_FUSION_API_KEY=xxxxx
# WP_FUSION_API_URL=https://wpfusion.company.com
# WP_FUSION_SITE_ID=12345
```

### Documentation & Handoff

**For Future Developer (When WP Fusion is Ready):**

1. Search codebase for `TODO-WPFUSION` comments
2. Follow the integration points listed above
3. Implement each method in `wpfusion_service.py`
4. Test with WP Fusion staging environment
5. Enable flag: `WP_FUSION_ENABLED = True`
6. Migrate existing users (run management command)
7. Monitor sync logs for 1 week before full cutover

**WP Fusion Integration Checklist:**
- [ ] WP Fusion API documentation received
- [ ] API credentials obtained & stored in .env
- [ ] wpfusion_service.py methods implemented
- [ ] Unit tests for sync logic
- [ ] Test migration script with 10 users
- [ ] Full user migration (production)
- [ ] Email/password fields set read-only
- [ ] Monitoring alerts set up
- [ ] Rollback plan documented

---

## Q&A: Your Specific Questions

### Q1: How to handle multiple advisors with shared credit pool?
**A: Use AdvisorPool model**
- Link multiple techs to pool
- Pool has total credit allocation
- Individual members stay assigned to tech, but pool status visible
- Dashboard shows: "My credits: $3,200 / Pool total: $10,000"

### Q2: Can we "link" advisors together?
**A: Yes - AdvisorPool is exactly this**
- Multiple techs in one pool
- Shared budget visibility
- Coordinated case management
- One pool → many techs → many members

### Q3: Set delegate access in member's or delegate's profile?
**A: Set in MEMBER profile (primary source)**
```
✅ Member Profile Tab: "Delegates"
  └─ [+ Add] Alice Johnson (Submit Cases)
  └─ [+ Add] Bob Smith (Full Access)

✓ Reverse view in delegate dashboard:
  └─ "I can access Jane Doe (Submit Cases)"
  └─ "I can access Sarah Johnson (Full Access)"
```
Single source of truth, easier to manage.

### Q4: Can we set in either place and sync both?
**A: Not recommended (complexity > benefit)**
- Causes sync issues
- Two sources of truth = conflicts
- Harder to debug permissions
- Better: One place to edit (member), multiple places to view

---

## Next Steps

1. **Confirm approach** with this analysis
2. **Clarify WP Fusion integration** for active/inactive status
3. **Database migrations** - create models
4. **Tech permission checks** - only techs can edit
5. **UI implementation** - profile edit form
6. **Testing** - audit trail, permissions, constraints

---

## Related Features (Already Implemented)
- ✅ Role-based access control (Admin, Tech, Member, Manager)
- ✅ is_active flag exists (could be repurposed or kept separate)
- ✅ Case workflow with member interactions
- ✅ Audit logging infrastructure

## Related Features (Not Yet Built)
- ❌ Delegate authority system (NEW - this analysis)
- ❌ Advisor pooling (NEW - this analysis)
- ❌ Editable member profiles (NEW - this analysis)
- ❌ Credit management (NEW - this analysis)
