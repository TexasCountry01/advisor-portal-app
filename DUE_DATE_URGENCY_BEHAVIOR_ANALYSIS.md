# Due Date & Urgency Behavior Analysis

**Question:** What happens if someone starts a case with a due date that is 7+ days out, saves as draft, then comes back 4 days later to attach documents and submit? Does the software reset the due date or throw an error that this is now a rushed case?

---

## Current Behavior

The `checkRushedStatus()` function in `submit_case.html` calculates urgency based on the **current date** compared to the due date:

- When form loads or user changes the date, it recalculates urgency based on **TODAY's date**
- If someone comes back 4 days later and the due date is now within 7 days, urgency will **automatically update to "rush"**
- The hidden urgency field gets updated to reflect this

**Example Scenario:**
1. User creates case on Jan 20 with due date of Feb 1 (12 days out) → urgency = "normal"
2. User saves as draft
3. User returns on Jan 24 to finish submission (due date now 8 days out) → urgency = "normal" ✓
4. User returns on Jan 26 to finish submission (due date now 6 days out) → urgency auto-updates to "rush" ⚠️

---

## Four Options

### **Option 1: Keep Current Behavior (Auto-Update Urgency) ✓ RECOMMENDED**

**Description:** Automatically recalculate urgency based on current date every time the form loads or is modified.

**Pros:**
- ✅ Automatic, no user friction
- ✅ Accurately reflects current reality (case IS rushed now)
- ✅ No accidental "normal" charges for cases that are actually rushed
- ✅ Prevents gaming the system by letting rush cases slip through

**Cons:**
- ⚠️ User might not realize urgency changed
- ⚠️ Could be surprised by rush fee/processing time

**Implementation:**
- Keep existing auto-update logic
- Add visual confirmation when user returns and urgency auto-updates
- Show notification banner: "Based on the current date and your due date of [DATE], this case is now marked as RUSH"
- Display "days remaining" indicator prominently
- Add explanation text about why urgency changed

**Code Location:** `cases/templates/cases/submit_case.html` - `checkRushedStatus()` function

---

### **Option 2: Show Warning but Allow Submission**

**Description:** Check urgency at submission time; if it changed from normal to rush, show alert but allow user to proceed.

**Pros:**
- ✅ User is aware of the change
- ✅ Still allows submission without blocking
- ✅ Gives user choice to proceed or revise dates
- ✅ Good balance of transparency and usability

**Cons:**
- ⚠️ Adds one confirmation step
- ⚠️ User might click through without reading

**Implementation:**
```javascript
form.addEventListener('submit', function(e) {
    if (submitAction === 'submit' && hasUrgencyChanged) {
        const proceed = confirm('This case is now marked as RUSH. Your due date is within 7 days. Continue?');
        if (!proceed) {
            e.preventDefault();
            return false;
        }
    }
    // continue with submission
});
```

---

### **Option 3: Throw Error - Require Due Date Reset**

**Description:** Block submission if urgency has changed, force user to confirm/update due date.

**Pros:**
- ✅ Forces user to consciously acknowledge the change
- ✅ Very clear audit trail of decisions
- ✅ Prevents accidental rush charges

**Cons:**
- ❌ High friction - frustrating UX
- ❌ User blocked from completing task
- ❌ Adds required action instead of automatic

**Implementation:**
```javascript
if (submitAction === 'submit' && hasUrgencyChanged) {
    e.preventDefault();
    alert('Due date is now within 7 days. Please review and update your due date if needed.');
    // Disable submit button until user re-confirms date
}
```

---

### **Option 4: Lock Due Date + Urgency in Draft**

**Description:** Freeze the due date and urgency when case is saved as draft. Don't recalculate when user returns.

**Pros:**
- ✅ What you see is what you get - no surprises
- ✅ Very predictable behavior
- ✅ No confusion about why urgency changed

**Cons:**
- ❌ Can't adjust urgency for changing priorities
- ❌ Inflexible - not aligned with business reality
- ❌ Could result in charging wrong rate (normal when should be rush)
- ❌ Creates inconsistency between draft and submitted urgency

**Implementation:**
```javascript
// Store original urgency value when saving draft
// Don't call checkRushedStatus() when loading draft
```

---

## Recommendation

### **Go with Option 1 (Keep Current) + Enhancement**

**Rationale:**
- Current behavior is actually correct - it accurately reflects business reality
- A case IS rushed if due date is now within 7 days, regardless of when it was created
- Prevents billing inconsistencies and processing delays
- Auto-update aligns with most SaaS applications

**Enhancements to Add:**

1. **✅ Notification Banner** - When user opens draft and urgency has changed:
   ```
   ℹ️ Alert: Based on today's date (Jan 26), this case is now marked as RUSH.
   Your due date is in 6 days. Processing may take longer.
   ```

2. **✅ Days Remaining Indicator** - Show prominently on form:
   ```
   Due Date: Feb 1, 2026
   Days Remaining: 6 days ⚠️ RUSH
   ```

3. **✅ Clear Explanation** - Under due date field:
   ```
   Note: Case urgency is automatically updated based on current date. 
   Cases with due dates within 7 days are marked as RUSH.
   ```

4. **✅ Visual Styling** - Make rush cases visually distinct:
   - Red/orange border around due date field when rushed
   - Red alert icon
   - Different background color for rush alert

---

## Implementation Checklist

- [ ] Add notification banner in submit form when urgency is auto-updated
- [ ] Add "days remaining" calculation and display
- [ ] Add visual styling for rush cases (red borders, icons)
- [ ] Add explanatory text about urgency auto-update
- [ ] Test scenario: Create draft as normal, return later as rush
- [ ] Document behavior in user guide/help text
- [ ] Consider backend validation to match frontend urgency

---

## Files to Modify

**Primary:** `cases/templates/cases/submit_case.html`
- Enhance `checkRushedStatus()` function
- Add notification elements
- Add days remaining calculation
- Update styling for rush cases

**Secondary:** `cases/views.py`
- Ensure backend also calculates urgency at submission time
- Verify consistency between frontend and backend logic

---

## Questions to Consider Before Implementation

1. **Fee Impact:** Does urgency affect billing? Should rush cases have different pricing?
2. **Notification:** Should we email user when their saved draft becomes rushed?
3. **User Expectation:** What do users expect to happen?
4. **Data Integrity:** Should we log when urgency auto-updated (audit trail)?
5. **Edge Cases:** What if due date is in the past when user returns?

---

**Document Created:** January 23, 2026  
**Status:** Analysis Complete - Ready for Decision
