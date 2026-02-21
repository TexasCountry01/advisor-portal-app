# Submit New Case Feature - Quick Start

## What's New?

The case submission process has been completely redesigned. Instead of filling a complex PDF form online, members now:

1. **Submit basic case info** on a simple form (5 minutes)
2. **Download the PDF template** 
3. **Fill it offline** at their own pace
4. **Upload the completed PDF** back to the case

---

## For Developers

### 1. Deploy the Code

```bash
# Pull the latest changes
git pull origin main

# Create migrations for new models
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Test locally
python manage.py runserver
```

### 2. Verify Files Are in Place

✓ `cases/views_submit_case.py` - New view file  
✓ `cases/templates/cases/submit_case.html` - New template  
✓ Updated `cases/urls.py`  
✓ Updated `accounts/models.py` (AdvisorDelegate model)  
✓ Updated `cases/models.py` (created_by field)  

### 3. Test the Form

Visit: `http://localhost:8000/cases/member/submit/`

**Test as Advisor:**
- Should see your name pre-filled
- Should not see advisor dropdown

**Test as Delegate:**
- Should see dropdown of authorized advisors
- Should be able to select different advisors

### 4. Configure Advisors (Optional)

If using delegate feature, set up relationships in Django admin:

```
Admin > Accounts > Advisor Delegates

+ Add Advisor Delegate
  Delegate: [Your Name]
  Advisor: [Advisor Name]
  ☑ Can Submit
  ☑ Can Edit
  ☑ Can View
```

---

## For End Users (Advisors)

### Quick Steps

1. **Log in** to your ProFeds account
2. **Click "Submit New Case"** (or visit `/cases/member/submit/`)
3. **Your name is already filled in** ✓
4. **Enter employee info:**
   - Federal employee's first name
   - Federal employee's last name
   - Their email (optional)
5. **Set due date** (defaults to 7 days out)
6. **Select number of reports** (1-5 retirement scenarios)
7. **Add any special notes** (optional)
8. **Upload supporting documents** (all at once):
   - Drag & drop multiple files
   - Or click to browse and select multiple
9. **Click "Create Case & Continue"**
10. **Download the Federal Fact Finder PDF**
11. **Fill it out** (online, or print and scan)
12. **Upload the completed PDF**

### What about the rush fee?

If you set the due date to **less than 7 days**, you'll see a yellow alert:

```
⚠️ Rushed Report Detected!
This case is due in less than 7 days.
A rush fee of $150 will apply.
```

The cost is $50 per day under the standard 7-day window.

---

## For Help/Support

### Common Questions

**Q: Where do I find the form?**  
A: Visit `/cases/member/submit/` or look for "Submit New Case" button on your dashboard

**Q: Can I edit the form after submitting?**  
A: Yes, you can edit case details from the case detail page

**Q: What if I forget to upload documents?**  
A: You can upload them anytime from the case detail page

**Q: Can I upload documents after submitting the case?**  
A: Yes, the case shows a document upload section

**Q: What formats are accepted?**  
A: PDF, DOC, DOCX, JPG, PNG (10MB max per file)

**Q: Why no PDF form filling online?**  
A: We simplified the process! Download the template, fill it at your own pace, upload it. Much easier.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Access Denied" | Make sure you're logged in as a member |
| Advisor dropdown not showing | You need to be set up as a delegate |
| Rush alert not appearing | Try refreshing the page after changing the date |
| Files won't upload | Check file size (max 10MB) and format |
| Can't find downloaded PDF | Check your Downloads folder |

---

## Technical Details

### New Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/cases/member/submit/` | GET | Show case submission form |
| `/cases/member/submit/` | POST | Process case submission |
| `/cases/api/calculate-rushed-fee/` | GET | AJAX - Calculate rush fee |

### New Models

**AdvisorDelegate**
```python
delegate → User (who submits)
advisor → User (whose cases they submit)
can_submit → Boolean
can_edit → Boolean
can_view → Boolean
```

### Model Updates

**Case Model - New Field**
```python
created_by → ForeignKey(User, null=True)
# Tracks who actually created the case
# (advisor or delegate)
```

### Form Fields

| Field | Type | Required | Default |
|-------|------|----------|---------|
| advisor_id | Hidden/Select | Yes | Auto-filled or must select |
| fed_first_name | Text | Yes | - |
| fed_last_name | Text | Yes | - |
| fed_email | Email | No | - |
| due_date | Date | Yes | Today + 7 days |
| num_reports_requested | Select | Yes | 1 |
| notes | Textarea | No | - |
| documents | File (multiple) | No | - |

---

## Rollout Checklist

- [ ] Code deployed to staging
- [ ] Database migrations applied
- [ ] Form tested with advisor account
- [ ] Form tested with delegate account (if applicable)
- [ ] Multi-file upload tested
- [ ] Rush detection tested
- [ ] Email notifications working
- [ ] PDF download working
- [ ] User training/documentation updated
- [ ] Deployed to production
- [ ] Monitored for errors in first 24 hours

---

## Files Reference

### New Files
- `cases/views_submit_case.py` - Backend view logic
- `cases/templates/cases/submit_case.html` - Frontend form
- `SUBMIT_CASE_IMPLEMENTATION.md` - Complete documentation
- `SUBMIT_CASE_FORM_WALKTHROUGH.md` - User walkthrough

### Modified Files
- `cases/urls.py` - Added new routes
- `accounts/models.py` - Added AdvisorDelegate model
- `cases/models.py` - Added created_by field

### Deprecated (can remove later)
- `cases/views_quick_submit.py` - Old quick submit view
- `cases/templates/cases/quick_case_submit.html` - Old template

---

## Performance Notes

- Form loads in < 1 second
- File upload is multi-file single request (fast)
- Rush calculation is AJAX (no page reload)
- Database queries optimized with select_related
- Static assets cached with versioning

---

## Security

✓ CSRF protection on all form submissions  
✓ Permission checks for delegate access  
✓ File upload validated (type & size)  
✓ User input sanitized  
✓ Case created_by correctly attributed  
✓ Audit trail via existing AuditLog model  

---

## Support Contact

For questions or issues with the new form:

1. **Check** SUBMIT_CASE_IMPLEMENTATION.md for details
2. **Review** SUBMIT_CASE_FORM_WALKTHROUGH.md for UI help
3. **Check** Django logs for errors
4. **Contact** dev team with error messages

---

**Last Updated:** December 29, 2025  
**Version:** 1.0 (Initial Release)  
**Status:** Ready for Testing
