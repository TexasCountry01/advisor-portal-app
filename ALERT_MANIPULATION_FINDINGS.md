# Alert Element Manipulation - Complete Findings Report

## Executive Summary
Found **CRITICAL CODE** that is actively hiding, manipulating, and monitoring alert elements across multiple template files. There is sophisticated code with MutationObservers, setTimeout handlers, and forced display property manipulation.

---

## 🔴 CRITICAL FINDINGS

### 1. [submit_case.html](cases/templates/cases/submit_case.html) - RUSHED ALERT MANIPULATION

#### Alert Element Definition
**Line 526:**
```html
<div class="alert alert-danger" id="rushAlert" style="display: none; border: 3px solid #dc3545; font-size: 1.1em; margin-top: 20px;">
    <div style="display: flex; align-items: flex-start; gap: 15px;">
        <div style="font-size: 2em;">⚠️</div>
        <div>
            <strong style="font-size: 1.2em; display: block; margin-bottom: 8px;">Rushed Request</strong>
            <p style="margin: 0; line-height: 1.6;">
                This date is less than the standard 7-day turnaround period and will be considered a "rushed" request which incurs a <strong>$20 fee</strong>.
            </p>
        </div>
    </div>
</div>
```

#### Hidden on Page Load
**Line 914:**
```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Hide rushed alert on page load - only show when user changes the date
    const rushAlert = document.getElementById('rushAlert');
    if (rushAlert) {
        rushAlert.style.display = 'none';
    }
});
```

#### Alert Hiding Based on Due Date Logic
**Lines 779-850:**

**Hiding when NO due date or date >7 days away:**
```javascript
if (!dueDateInput || !dueDateInput.value) {
    console.log('No due date input or empty value');
    if (rushAlert) rushAlert.style.setProperty('display', 'none', 'important');
    if (urgencyInput) urgencyInput.value = 'normal';
    return;
}
```

**Showing when due date <7 days (RUSHED):**
```javascript
if (isRushed) {
    console.log('Setting alert to VISIBLE and urgency to URGENT');
    if (rushAlert) {
        rushAlert.style.setProperty('display', 'block', 'important');
        rushAlert.style.setProperty('visibility', 'visible', 'important');
        rushAlert.style.setProperty('opacity', '1', 'important');
        console.log('Alert display set to block');
        
        // Set up a watcher to prevent the alert from being hidden
        if (!rushAlert.observer) {
            rushAlert.observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    console.log('Alert mutation detected:', mutation.type, mutation.attributeName);
                });
                rushAlert.style.setProperty('display', 'block', 'important');
                rushAlert.style.setProperty('visibility', 'visible', 'important');
                rushAlert.style.setProperty('opacity', '1', 'important');
            });
            rushAlert.observer.observe(rushAlert, { attributes: true });
        }
```

#### ⚠️ **CRITICAL - 2-Second Watchdog Timeout (Lines 826-838)**
```javascript
// Check if something hides the alert after 2 seconds
setTimeout(function() {
    const computedStyle = window.getComputedStyle(rushAlert);
    console.log('After 2 seconds - Alert display:', computedStyle.display);
    console.log('After 2 seconds - Alert visibility:', computedStyle.visibility);
    console.log('After 2 seconds - Alert opacity:', computedStyle.opacity);
    console.log('After 2 seconds - Alert style attribute:', rushAlert.getAttribute('style'));
    if (computedStyle.display === 'none' || computedStyle.visibility === 'hidden' || computedStyle.opacity === '0') {
        console.log('ALERT WAS HIDDEN! Restoring...');
        rushAlert.style.setProperty('display', 'block', 'important');
        rushAlert.style.setProperty('visibility', 'visible', 'important');
        rushAlert.style.setProperty('opacity', '1', 'important');
    }
}, 2100);
```

**What this does:**
- After 2.1 seconds, checks if the alert was hidden
- If hidden by ANY means (display: none, visibility: hidden, or opacity: 0), it FORCEFULLY restores it
- This acts as a "protection mechanism" against something trying to hide the alert

#### Hiding when NOT rushed (Lines 844-850)
```javascript
} else {
    console.log('Setting alert to HIDDEN and urgency to NORMAL');
    if (rushAlert) {
        rushAlert.style.setProperty('display', 'none', 'important');
        // Stop watching for mutations
        if (rushAlert.observer) {
            rushAlert.observer.disconnect();
            rushAlert.observer = null;
        }
    }
    if (urgencyInput) urgencyInput.value = 'normal';
}
```

---

### 2. [edit_case.html](cases/templates/cases/edit_case.html) - SIMILAR RUSHED ALERT MANIPULATION

#### Alert Element Definition
**Line 49:**
```html
<div class="alert alert-danger mt-3" id="rushAlertEdit" style="display: none; border: 3px solid #dc3545; font-size: 1.1em;">
```

#### Hiding Based on Due Date Logic
**Lines 161-177:**
```javascript
function updateUrgencyFromDueDate() {
    const dueDateInput = document.getElementById('date_due').value;
    const urgencyInput = document.getElementById('urgency');
    const rushAlert = document.getElementById('rushAlertEdit');
    
    if (!dueDateInput) {
        urgencyInput.value = 'normal';
        rushAlert.style.display = 'none';
        return;
    }

    const dueDate = new Date(dueDateInput);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const sevenDaysFromNow = new Date(today);
    sevenDaysFromNow.setDate(sevenDaysFromNow.getDate() + 7);
    
    if (dueDate < sevenDaysFromNow) {
        urgencyInput.value = 'urgent';
        rushAlert.style.display = 'block';
    } else {
        urgencyInput.value = 'normal';
        rushAlert.style.display = 'none';
    }
}
```

#### Page Load Initialization
**Lines 185-188:**
```javascript
// Check on page load
document.addEventListener('DOMContentLoaded', function() {
    updateUrgencyFromDueDate();
});
```

---

### 3. [case_detail.html](cases/templates/cases/case_detail.html) - setTimeout WITH 2-SECOND RELOAD

#### First Instance - Release Options Modal (Lines 968-985)
```javascript
setTimeout(() => {
    location.reload();
}, 2000);
```
**Context:** After releasing a case successfully, page reloads after 2 seconds.

#### Second Instance - Mark as Incomplete (Lines 1069-1085)
```javascript
setTimeout(() => {
    location.reload();
}, 2000);
```
**Context:** After marking case as incomplete, page reloads after 2 seconds.

---

### 4. [fact_finder_form.html](cases/templates/cases/fact_finder_form.html)

#### setTimeout for Validation Error Highlighting (Lines 3608-3610)
```javascript
setTimeout(() => {
    errors[0].element.style.border = '';
}, 3000);
```
**Context:** Removes validation error border after 3 seconds.

#### Classes Being Removed from Alerts/Banners
**Line 2808:** Removes 'show' class from draft banner
```javascript
document.getElementById('draftBanner').classList.remove('show');
```

**Line 2815:** Another instance removing 'show' class
```javascript
document.getElementById('draftBanner').classList.remove('show');
```

---

## Summary Table of All Alert Manipulations

| File | Element ID | Line(s) | Action | Trigger |
|------|-----------|---------|--------|---------|
| submit_case.html | rushAlert | 526 | Display: none (initial) | Page load |
| submit_case.html | rushAlert | 779 | Display: none (important) | No due date OR date >7 days |
| submit_case.html | rushAlert | 814 | Display: block (important) | Due date <7 days |
| submit_case.html | rushAlert | 826-838 | **WATCHDOG - Restore after 2.1s** | Checks if hidden |
| submit_case.html | rushAlert | 844 | Display: none (important) | Not rushed |
| submit_case.html | rushAlert | 914 | Display: none | DOMContentLoaded |
| edit_case.html | rushAlertEdit | 49 | Display: none (initial) | Page load |
| edit_case.html | rushAlertEdit | 161, 177 | Display: none/block | Due date change |
| case_detail.html | N/A (page reload) | 970, 1071 | **location.reload()** | After 2 seconds |
| fact_finder_form.html | draftBanner | 2808, 2815 | classList.remove('show') | Form submission |

---

## Pattern Analysis

### ✅ Legitimate Patterns Found
1. **Rushed request alert** - Conditionally shows/hides based on due date < 7 days
2. **Draft banner** - Removes 'show' class after form submission
3. **Page reloads** - 2-second delay after successful operations (reasonable UX)

### ⚠️ Suspicious Patterns
1. **MutationObserver on rushAlert** - Watches for ANY attribute changes and FORCES the alert to stay visible/block
2. **2.1-second watchdog timer** - Detects if something hidden the alert and forcefully restores it
3. **!important flags** - Multiple `setProperty(..., 'important')` calls suggest someone/something is trying to override these styles elsewhere

---

## Potential Root Cause Investigation

The presence of the watchdog timer and MutationObserver suggests that **something else in the codebase is trying to hide the rushAlert**. Candidates:
1. Bootstrap's alert dismiss functionality
2. A CSS animation or transition
3. Another JavaScript file (possibly in `static/js/`)
4. Browser extension or third-party code

---

## Recommendations

1. **Inspect static/js/ folder** for any additional JavaScript that might manipulate alerts
2. **Check Bootstrap CSS** for any auto-hide animations on `.alert-dismissible`
3. **Check browser console** while interacting with the rushed alert - the console.log statements will reveal what's happening
4. **Review other template files** for similar patterns
5. **Consider if the 2-second watchdog is actually necessary** - its existence implies a known issue

---

## Files Requiring Investigation
- [ ] `static/js/` - Check for main.js or other JS files
- [ ] `static/css/` - Check for alert-related animations
- [ ] Django template inheritance - Check base templates
- [ ] Bootstrap version - May have auto-dismiss functionality
- [ ] Browser developer tools - Run during form interaction to see mutations

