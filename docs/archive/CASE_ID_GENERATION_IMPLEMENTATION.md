# Case ID Generation - Implementation Summary

## Overview
Implemented **Option 1: Workshop Code + Date + Sequence** for meaningful Case ID generation.

## New Format
**`WS###-YYYY-MM-####`**

Example: `WS001-2026-01-0042`

### Format Breakdown:
- **WS** - Workshop prefix (constant)
- **###** - Workshop code (3-digit numeric part)
- **YYYY-MM** - Year and month of case creation
- **####** - Sequential counter for that workshop/month (zero-padded)

## Benefits
✅ **Meaningful for members** - Shows workshop, creation date, and sequence at a glance  
✅ **Trackable** - Members can easily track and organize cases  
✅ **Non-breaking** - Maintains same database field (`external_case_id`)  
✅ **Flexible** - Handles various workshop code formats (WS001, 001, WS-001, etc.)  
✅ **Sortable** - Naturally sorts by date and sequence within each month  

## Implementation Details

### New Service File
**Location:** `cases/services/case_id_generator.py`

**Function:** `generate_case_id(workshop_code: str) -> str`

Logic:
1. Extracts 3-digit numeric code from workshop_code (handles multiple formats)
2. Gets current date (year/month)
3. Queries existing cases matching the prefix (WS###-YYYY-MM)
4. Finds highest sequence number in database
5. Returns new ID with incremented sequence

### Updated Views

#### 1. `cases/views_submit_case.py`
- Removed: `import uuid`
- Added: `from cases.services.case_id_generator import generate_case_id`
- Changed: Case ID generation from UUID to meaningful format

**Before:**
```python
external_case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
```

**After:**
```python
external_case_id = generate_case_id(workshop_code)
```

#### 2. `cases/views_quick_submit.py`
- Removed: `import uuid`
- Added: `from cases.services.case_id_generator import generate_case_id`
- Added: `workshop_code = user.workshop_code`
- Changed: Case ID generation from UUID to meaningful format

**Before:**
```python
external_case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
```

**After:**
```python
workshop_code = user.workshop_code
external_case_id = generate_case_id(workshop_code)
```

## Database Compatibility
✅ **No migration required** - Uses existing `external_case_id` field  
✅ **Backward compatible** - Can coexist with old UUID-format cases  
✅ **Indexed field** - Performance maintained with existing index  
✅ **Unique constraint** - Still enforced as before  

## Testing
The generator function has been tested and verified to:
- Handle various workshop code formats
- Properly extract numeric codes
- Generate correct format: WS###-YYYY-MM-####
- Increment sequences within each month/workshop combination

## Example Output
```
WS001-2026-01-0001  (First case in WS001 for Jan 2026)
WS001-2026-01-0002  (Second case in WS001 for Jan 2026)
WS002-2026-01-0001  (First case in WS002 for Jan 2026)
WS001-2026-02-0001  (First case in WS001 for Feb 2026)
```

## Existing Cases
Current database cases using old UUID format (CASE-XXXXXXXX) will continue to work. New cases created going forward will use the meaningful format.

## Future Enhancements
- Could add prefix customization via settings
- Could track case sequence in a separate table for better performance at scale
- Could provide API endpoint to search by date range
