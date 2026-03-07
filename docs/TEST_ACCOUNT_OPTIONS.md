# Test Account Tagging Options

## Problem
We need permanent test users across various roles (member, delegate, technician, etc.) that survive SSO data clears and database resets. These test accounts should be easily identifiable so cleanup scripts can exclude them.

---

## Option A: Database Field (Recommended)

**Approach:** Add an `is_test_account = BooleanField(default=False)` on the User model.

**How it works:**
- Add a single boolean field to the Django User model
- Set it once via Django Admin (checkbox) or a management command
- Cleanup scripts use `.exclude(is_test_account=True)` to skip test users
- WordPress/SSO passes nothing extra — the flag lives entirely in Django
- When a test user arrives via SSO from WordPress, Django creates/updates the user as normal. You then mark that user as `is_test_account=True` in Django. It's a one-time flag that persists regardless of SSO activity.

**Pros:**
- Cleanest, most explicit approach
- No naming conventions to remember or enforce
- Queryable — easy to filter in scripts, admin, and reporting
- Can't be accidentally broken by renaming a user
- Can later be used to skip test accounts in analytics/reporting
- No WordPress changes required

**Cons:**
- Requires a model migration (minor — one field addition)

**Example usage in cleanup scripts:**
```python
# Delete all non-test users and their cases
User.objects.filter(role='member', is_test_account=False).delete()

# Clear cases but keep test account cases
Case.objects.exclude(member__is_test_account=True).delete()
```

---

## Option B: Username Convention

**Approach:** Prefix or suffix test usernames with a tag (e.g., `test_member_dale`, `test_tech_jaylon`, or `dale_test`).

**How it works:**
- Create test users in WordPress with the naming convention
- SSO brings them into Django with the tagged username
- Filter by `username__startswith='test_'` or `username__endswith='_test'` when clearing data

**Pros:**
- No model changes needed — zero migrations
- Easy to visually identify test accounts
- Works immediately with existing codebase

**Cons:**
- Relies on naming discipline — nothing enforces the convention
- Can break if a user is renamed in WordPress
- Slightly less clean in queries (string matching vs boolean)
- WordPress users must follow the convention exactly

**Example usage in cleanup scripts:**
```python
# Delete all non-test users
User.objects.filter(role='member').exclude(username__startswith='test_').delete()
```

---

## Option C: Django Group

**Approach:** Add test users to a Django Group called "TestAccounts".

**How it works:**
- Create a Group named "TestAccounts" in Django Admin
- Add each test user to that group (via Admin or script)
- Filter by group membership when clearing data

**Pros:**
- Uses built-in Django infrastructure (Groups are native)
- No model changes or migrations
- Can manage group membership via Django Admin

**Cons:**
- Slightly more overhead — requires joining through the group table
- Group membership is managed separately from user creation
- More complex queries than a simple boolean
- Group assignments don't survive if you delete and re-create users

**Example usage in cleanup scripts:**
```python
# Delete all non-test users
User.objects.filter(role='member').exclude(groups__name='TestAccounts').delete()
```

---

## Recommendation

**Option A (Database Field)** is the best approach because:
1. It's the simplest to query and maintain
2. It's explicit — no conventions or group management to track
3. It requires zero changes to WordPress or SSO
4. It's a one-time setup per test user that persists permanently
5. It can be extended later for reporting/analytics exclusions

The only cost is a single model migration to add the boolean field, which is trivial.
