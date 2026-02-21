# C1: Cron Job Status - Verification & Setup

## Current State Analysis

### ✅ What EXISTS (Infrastructure in place):

1. **Management Commands Already Built:**
   - `release_scheduled_cases.py` - Releases cases on scheduled date
   - `send_scheduled_emails.py` - Sends notification emails on scheduled date
   - Both have `--dry-run` capability for testing

2. **Case Model Fields Ready:**
   - `scheduled_release_date` - When case should be released
   - `actual_release_date` - When case was actually released
   - `scheduled_email_date` - When email should be sent
   - `actual_email_sent_date` - When email was actually sent
   - `hold_start_date`, `hold_end_date`, `hold_duration_days` - Hold tracking

3. **System Settings:**
   - `batch_release_time` - Configured time for batch releases
   - `batch_release_enabled` - Feature toggle
   - `enable_scheduled_releases` - Feature toggle

### ❌ What's MISSING (Not Implemented):

1. **Cron Job Configuration** 
   - NOT set up in Linux crontab
   - NOT configured in Windows Task Scheduler
   - Commands exist but aren't being automatically triggered

2. **No Celery/Beat Setup**
   - Celery listed in archived requirements but not active
   - No periodic tasks configured
   - Could use Django-APScheduler as alternative

3. **Environment-Specific Setup**
   - Local (sqlite): Doesn't need cron (manual testing)
   - Remote TEST (MariaDB): NEEDS cron configured
   - No automation currently running on TEST

## What Needs to Be Done

### Option 1: Simple Approach (Recommended for Quick Testing)
- Add manual cron job to Linux/Windows for TEST server
- Commands already exist and work
- Just need to wire them up to scheduler

### Option 2: Production Approach
- Set up Celery + Django-Celery-Beat
- More robust but requires Redis/message broker
- Better for scaling

## Next Steps

1. **Determine your environment:**
   - Is TEST server Windows or Linux?
   - Do you have sudo access to modify crontab?
   - Is there a production server already running?

2. **Choose your approach:**
   - Quick: Set up crontab (5 min)
   - Robust: Set up Celery Beat (1-2 hours)

3. **Then configure and test:**
   - Verify commands work manually
   - Set up scheduler
   - Test with dry-run
   - Monitor execution

## Files Involved

- **Commands**: `cases/management/commands/release_scheduled_cases.py`, `send_scheduled_emails.py`
- **Models**: `cases/models.py` (Case model with scheduled_* fields)
- **Settings**: `config/settings.py`

## Questions to Answer

1. What OS is your TEST server running? (Windows/Linux)
2. Do you have access to crontab or Task Scheduler?
3. Want simple cron setup or robust Celery setup?
