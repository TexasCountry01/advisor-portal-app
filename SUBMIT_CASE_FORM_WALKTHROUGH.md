# Submit New Case - Form Walkthrough

## Page Layout

```
┌─────────────────────────────────────────────────────────┐
│                 Submit New Case                         │
│  Create a new federal retirement planning case and     │
│  upload supporting documents                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SECTION 1: ADVISOR INFORMATION                        │
│  ┌──────────────────────────────────────┐              │
│  │ Advisor Name (Disabled for advisors) │              │
│  │ [Sarah Johnson - Auto-filled]        │              │
│  │                                      │              │
│  │ OR (for delegates):                  │              │
│  │ ○ Sarah Johnson  ○ Mike Chen        │              │
│  └──────────────────────────────────────┘              │
│                                                         │
│  SECTION 2: FEDERAL EMPLOYEE INFORMATION               │
│  ┌──────────────────────────────────────┐              │
│  │ First Name (Required)*               │              │
│  │ [John                              ] │              │
│  │                                      │              │
│  │ Last Name (Required)*                │              │
│  │ [Smith                             ] │              │
│  │                                      │              │
│  │ Email Address (Optional)             │              │
│  │ [john.smith@agency.gov             ] │              │
│  └──────────────────────────────────────┘              │
│                                                         │
│  SECTION 3: CASE DETAILS                               │
│  ┌──────────────────────────────────────┐              │
│  │ Due Date (Required)*                 │              │
│  │ [2025-01-06 ▼] (7 days from today)  │              │
│  │                                      │              │
│  │ Number of Reports (Required)*        │              │
│  │ [1 Report        ▼]                 │              │
│  │                                      │              │
│  │ ⚠️ RUSHED REPORT DETECTED!          │              │
│  │ Less than 7 days. Rush fee: $150    │              │
│  └──────────────────────────────────────┘              │
│                                                         │
│  SECTION 4: ADDITIONAL INFORMATION                     │
│  ┌──────────────────────────────────────┐              │
│  │ Notes/Comments (Optional)            │              │
│  │ ┌────────────────────────────────┐   │              │
│  │ │ TSP Account: 12345678          │   │              │
│  │ │ Retiring January 2026          │   │              │
│  │ └────────────────────────────────┘   │              │
│  └──────────────────────────────────────┘              │
│                                                         │
│  SECTION 5: SUPPORTING DOCUMENTS                       │
│  📄 Required Documents:                                 │
│  • Federal Fact Finder form (download below)           │
│  • Recent pay stub                                      │
│  • TSP account statement                               │
│  • Social Security statement                           │
│                                                         │
│  Document Type: [Pay Stub ▼]                          │
│                                                         │
│  ┌──────────────────────────────────────┐              │
│  │           📁                         │              │
│  │    Click to upload or drag & drop   │              │
│  │                                      │              │
│  │  Accepted: PDF, DOC, DOCX, JPG, PNG │              │
│  │  (Max 10MB per file)                │              │
│  └──────────────────────────────────────┘              │
│                                                         │
│  Uploaded Files:                                       │
│  ┌─────────────────────────────────────┐              │
│  │ 📄 pay_stub_dec_2025.pdf 2.1 MB [X] │              │
│  │ 📄 tsp_statement.pdf 1.8 MB    [X] │              │
│  │ 📄 ss_statement.pdf 0.9 MB     [X] │              │
│  └─────────────────────────────────────┘              │
│                                                         │
│  📥 DOWNLOAD THE TEMPLATE                              │
│  After creating this case, you'll be able to download   │
│  the Federal Fact Finder PDF template to fill out and   │
│  upload.                                                │
│                                                         │
│  ┌─────────────────────────────────────┐              │
│  │ [Cancel]  [Create Case & Continue]  │              │
│  └─────────────────────────────────────┘              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Interactive Elements

### Advisor Selection (Delegates Only)
```
When user is a delegate, they see:

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Sarah Johnson│  │ Mike Chen    │  │ Jane Davis   │
│ (Disabled)   │  │ (Available)  │  │ (Available)  │
└──────────────┘  └──────────────┘  └──────────────┘

Click on "Mike Chen" to select him
→ Button highlights: ┌─────────────────┐
                    │ Mike Chen       │
                    │ (Selected)      │
                    └─────────────────┘
```

### Date Picker with Rush Detection
```
Default View (7+ days):
[2025-01-06] (7 days from today)
✓ Normal processing - No alert

Changed to < 7 days (e.g., 2025-01-05):
[2025-01-05] (6 days from today)
⚠️ RUSHED REPORT DETECTED!
Less than 7 days. Rush fee: $50

Changed to 1 day (2024-12-30):
[2024-12-30] (1 day from today) 
⚠️ RUSHED REPORT DETECTED!
Less than 7 days. Rush fee: $300
```

### File Upload Workflow

**Step 1: Initial State**
```
    ┌──────────────────────────────────────┐
    │           📁                         │
    │    Click to upload or drag & drop   │
    │                                      │
    │  Accepted: PDF, DOC, DOCX, JPG, PNG │
    │  (Max 10MB per file)                │
    └──────────────────────────────────────┘

Files uploaded: 0
```

**Step 2: Hover State**
```
    ┌──────────────────────────────────────┐
    │  Highlighted border, different bg   │
    │           📁                         │
    │    Click to upload or drag & drop   │
    │                                      │
    │  Accepted: PDF, DOC, DOCX, JPG, PNG │
    └──────────────────────────────────────┘
```

**Step 3: After Selection**
```
Selected files appear in list:

Uploaded Files:
┌────────────────────────────────────────┐
│ 📄 pay_stub_dec_2025.pdf 2.1 MB [X]   │
│ 📄 tsp_statement.pdf 1.8 MB    [X]   │
│ 📄 ss_statement.pdf 0.9 MB     [X]   │
│ 📄 fact_finder_filled.pdf 3.2 MB [X] │
└────────────────────────────────────────┘

Users can:
- See file names and sizes
- Remove individual files with [X] button
- Add more files by clicking upload area again
- Submit form with all selected files
```

## Form States & Validation

### Valid Form
```
✓ Fed First Name: Filled
✓ Fed Last Name: Filled
✓ Due Date: Valid date
✓ Advisor: Selected
✓ # of Reports: Selected

[Create Case & Continue] Button: ENABLED
```

### Invalid Form (Missing Required Fields)
```
✗ Fed First Name: EMPTY (Red border)
  Error message: "Required field"
✓ Fed Last Name: Filled
✗ Due Date: NOT SET (Red border)
  Error message: "Date required"
✓ Advisor: Selected
✓ # of Reports: Selected

[Create Case & Continue] Button: DISABLED
```

### Rushed Report Alert
```
┌────────────────────────────────────────┐
│ ⚠️  Rushed Report Detected!            │
│ This case is due in less than 7 days.  │
│ A rush fee of $150 will apply.         │
└────────────────────────────────────────┘

(Red/yellow alert box appears when due date < 7 days)
```

## Field Descriptions

| Field | Default | Validation | Help Text |
|-------|---------|-----------|-----------|
| **Advisor** | Pre-filled for advisors | Must select if delegate | Your cases will be submitted under your name |
| **Fed First Name** | Empty | Required, text | John |
| **Fed Last Name** | Empty | Required, text | Smith |
| **Fed Email** | Empty | Optional, email | john.smith@agency.gov |
| **Due Date** | +7 days | Req'd, no past dates | Default: 7 days from today |
| **# Reports** | 1 | Required, 1-5 | Number of retirement scenarios |
| **Notes** | Empty | Optional, textarea | TSP Account: 12345678 |
| **Documents** | None | Optional, multiple | Upload all at once |

## Mobile View

```
On mobile (< 768px):

┌──────────────┐
│ SUBMIT CASE  │
├──────────────┤
│              │
│ Advisor Name │
│ [Disabled]   │
│              │
│ First Name*  │
│ [          ] │
│              │
│ Last Name*   │
│ [          ] │
│              │
│ Email        │
│ [          ] │
│              │
│ Due Date*    │
│ [          ] │
│              │
│ Reports*     │
│ [1 ▼       ] │
│              │
│ Notes        │
│ [          ] │
│ [          ] │
│              │
│ Documents    │
│ [📁 Upload ] │
│              │
│ [Cancel    ] │
│ [Create    ] │
│              │
└──────────────┘

- Single column layout
- Full-width buttons
- Touch-friendly spacing
- Easy scrolling
```

## Success Flow

```
1. User fills form
   ↓
2. Clicks "Create Case & Continue"
   ↓
3. Form validates (client + server)
   ↓
4. Files uploaded to server
   ↓
5. Case created in database
   ↓
6. Success message shown:
   "✓ Case created successfully! Case ID: CASE-ABC12345"
   (If rushed: Yellow warning instead)
   ↓
7. Redirect to case detail page
   ↓
8. User can download Federal Fact Finder PDF template
   ↓
9. User fills PDF offline
   ↓
10. User uploads completed PDF
```

## Error Handling

```
Scenario 1: Missing Required Field
┌──────────────────────────────────┐
│ ✗ Error                          │
│ Federal employee first and last  │
│ name are required.               │
└──────────────────────────────────┘

Scenario 2: Invalid Date
┌──────────────────────────────────┐
│ ✗ Error                          │
│ Due date cannot be in the past.  │
└──────────────────────────────────┘

Scenario 3: No Advisor Selected
┌──────────────────────────────────┐
│ ✗ Error                          │
│ Advisor selection is required.   │
└──────────────────────────────────┘

Scenario 4: Permission Denied
┌──────────────────────────────────┐
│ ✗ Error                          │
│ You do not have permission to    │
│ submit cases for this advisor.   │
└──────────────────────────────────┘
```

---

## Key Features At a Glance

✅ **No PDF Form Filling Online**  
Users download template and fill it themselves

✅ **Smart Rush Detection**  
Automatic alerts when due date < 7 days

✅ **Multi-File Upload**  
Select multiple files at once, no repeated clicking

✅ **Drag & Drop**  
Intuitive file upload experience

✅ **Advisor Delegation**  
Staff can submit cases for advisors they work with

✅ **Pre-populated Fields**  
Advisor name auto-fills for advisors

✅ **Real-time Validation**  
Errors shown instantly, red borders on invalid fields

✅ **Mobile Responsive**  
Works great on phones, tablets, desktops

✅ **WCAG Accessible**  
Keyboard navigation, screen readers, color contrast
