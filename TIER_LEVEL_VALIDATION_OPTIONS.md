# Tier-Level Validation for Technician Assignment - Options

**Date:** January 24, 2026  
**Issue:** When accepting a case and assigning to a technician during initial case review, need to ensure the assigned technician has the minimum level to handle that tier.

---

## Current System Understanding

### Technician Levels
- **Level 1** - New Technician (can handle Tier 1 only)
- **Level 2** - Technician (can handle Tier 1 & 2)
- **Level 3** - Senior Technician (can handle Tier 1, 2, & 3)

### Case Tiers
- **Tier 1** - Standard cases (any tech)
- **Tier 2** - Complex cases (Level 2+ required)
- **Tier 3** - Critical/specialized cases (Level 3 only)

### Current Validation (For Accepting Tech)
When a technician ACCEPTS a case, their own level is validated:
- ❌ Level 1 cannot accept Tier 2 (blocked, can override with note)
- ❌ Level 1 cannot accept Tier 3 (blocked, can override with note)
- ❌ Level 2 cannot accept Tier 3 (blocked, can override with note)

### Gap Identified
When assigning to a DIFFERENT technician during acceptance:
- ⚠️ NO validation that assigned tech meets tier requirement
- ⚠️ Could assign Level 1 tech to a Tier 3 case
- ⚠️ Could create workload imbalance

---

## 5 Options for Validating Assigned Tech Level

---

## **Option 1: Strict Validation - Block Invalid Assignments** ⭐ RECOMMENDED

### How It Works
- Admin/manager assigns tech when accepting case
- System validates: `tech.user_level >= tier_requirement`
- If tech level insufficient: Assignment blocked, error returned
- No override allowed

### Tier Requirements
- Tier 1: Any level (level_1, level_2, level_3)
- Tier 2: level_2 or level_3 only
- Tier 3: level_3 only

### Validation Logic
```
if tier == '2' and assigned_tech.user_level == 'level_1':
    BLOCK - "Level 1 techs cannot be assigned Tier 2 cases"
    
if tier == '3' and assigned_tech.user_level in ['level_1', 'level_2']:
    BLOCK - "Only Level 3 techs can handle Tier 3 cases"
```

### Pros
- ✅ Ensures correct skill matching
- ✅ Prevents over/under-utilization
- ✅ Clear, enforceable rules
- ✅ No ambiguity

### Cons
- ❌ Less flexibility for emergency situations
- ❌ May slow case processing

### Implementation Effort
- Low (add validation in accept_case view)

---

## **Option 2: Strict Validation with Override (Management Override)**

### How It Works
Same as Option 1, but:
- Manager/Admin with override role can assign anyway
- Requires explicit note explaining override reason
- Audit logged as "tier_level_override"

### Validation Logic
```
if tier_mismatch:
    if user.role == 'administrator' and override_note provided:
        ALLOW - "Override by admin"
    else:
        BLOCK - "Tech level insufficient"
```

### Pros
- ✅ Strict enforcement normally
- ✅ Allows exceptions when needed (sick leave, emergency)
- ✅ Audit trail of overrides
- ✅ Balances control with flexibility

### Cons
- ❌ Requires additional fields (override_reason, override_by)
- ❌ Slightly more complex logic

### Implementation Effort
- Medium (add override mechanism, audit logging)

---

## **Option 3: Warning Only (Advisory Mode)**

### How It Works
- Assignment allowed even if level insufficient
- System shows WARNING in UI: "⚠️ This tech is Level 1 - Tier 2 may be challenging"
- Accepts with warning, still creates case assignment
- Audit logs as "tier_level_warning_accepted"

### Validation Logic
```
if tier_mismatch:
    WARN - "This combination may be risky"
    if user clicks "Accept Anyway":
        ALLOW with warning logged
    else:
        CANCEL
```

### Pros
- ✅ Maximum flexibility
- ✅ Doesn't block workflow
- ✅ Still alerts user to issue
- ✅ Empowers techs to upskill

### Cons
- ❌ Risky - could assign Level 1 to complex Tier 3
- ❌ No enforcement mechanism
- ❌ Could cause poor quality work

### Implementation Effort
- Low (add warning modal, don't block)

---

## **Option 4: Smart Filtering in Dropdown**

### How It Works
- Dropdown only shows techs QUALIFIED for that tier
- No validation needed (constraints built into UI)
- "Unassigned" option still available

### Dropdown Display
```
Tier 1: [Tech A (L1)] [Tech B (L2)] [Tech C (L3)] [Unassigned]
Tier 2: [Tech B (L2)] [Tech C (L3)] [Unassigned]
Tier 3: [Tech C (L3)] [Unassigned]
```

### Pros
- ✅ Clean UX - no invalid options available
- ✅ Prevents mistakes at source
- ✅ Shows which techs CAN handle case
- ✅ Educates users about levels

### Cons
- ❌ More complex filtering logic
- ❌ What if you need to unassign? (can still do it)
- ❌ Doesn't show ALL available techs

### Implementation Effort
- Medium (add context filtering in case_detail view)

---

## **Option 5: Combination - Smart Filter + Strict Validation**

### How It Works
1. **Frontend (HTML):** Dropdown filtered to show only qualified techs
2. **Backend (Views):** Strict validation blocks any invalid assignments
3. **User sees:** Only qualified options, but system validates anyway

### Best of Both Worlds
- Prevents user from selecting invalid options
- Backend also validates (defense in depth)
- Clear communication about requirements
- Protects against edge cases

### Pros
- ✅ Maximum safety (double-check)
- ✅ Clean UX + strict enforcement
- ✅ Educates while protecting
- ✅ Professional appearance

### Cons
- ❌ Most implementation work
- ❌ Slight code duplication (validation in 2 places)

### Implementation Effort
- Medium-High (filtering + validation)

---

## Comparison Matrix

| Option | Flexibility | Safety | UX | Effort | Recommended |
|--------|-------------|--------|-----|--------|-------------|
| 1: Strict | Low | ⭐⭐⭐⭐⭐ | Fair | Low | **YES** |
| 2: Override | Medium | ⭐⭐⭐⭐ | Good | Medium | Maybe |
| 3: Warning | High | ⭐⭐ | Poor | Low | No |
| 4: Filter | Medium | ⭐⭐⭐ | Great | Medium | Maybe |
| 5: Filter+Valid | Medium | ⭐⭐⭐⭐⭐ | Great | Medium-High | Best |

---

## My Recommendation

### **Start with Option 1 (Strict Validation)**

**Why:**
1. **Simplest to implement** - Just add validation logic
2. **Most professional** - Enforces business rules
3. **Easy to upgrade** - Can add override later if needed
4. **Protects quality** - Ensures right person for right tier

**Implementation:**
```python
# In accept_case view
def validate_tier_level(tier, tech):
    if tier == 'tier_2' and tech.user_level == 'level_1':
        raise ValidationError("Level 1 techs cannot handle Tier 2")
    if tier == 'tier_3' and tech.user_level in ['level_1', 'level_2']:
        raise ValidationError("Only Level 3 techs can handle Tier 3")
```

**If Needed Later:**
Can upgrade to Option 2 (add override) or Option 5 (add UI filtering) in Phase 2

---

## Current Tier-Level Mapping

Based on code review:
- **Tier 1** → Any technician level (level_1, level_2, level_3)
- **Tier 2** → Requires level_2 or level_3
- **Tier 3** → Requires level_3 only

This matches the current validation in accept_case for the accepting tech.

---

## Questions to Answer Before Implementation

1. **Should Managers be able to override?**
   - Yes = Option 2 or 5
   - No = Option 1 or 4

2. **Is flexibility important for emergency situations?**
   - Yes = Option 2 (override) or 3 (warning)
   - No = Option 1 (strict)

3. **Do you want the dropdown to show ALL techs or only qualified ones?**
   - Show all = Option 1 + validation
   - Show qualified only = Option 4 or 5

4. **What should happen if someone tries to assign invalid tech?**
   - Error/block = Option 1, 2, 5
   - Warning = Option 3, 4

---

## Next Steps

1. **Choose an option** (I recommend Option 1)
2. **Answer the 4 questions above**
3. **Implement validation logic**
4. **Add to accept_case view**
5. **Test edge cases**
6. **Commit changes**

---

**Decision Status:** Awaiting user selection  
**Estimated Implementation:** 1-2 hours once option chosen
