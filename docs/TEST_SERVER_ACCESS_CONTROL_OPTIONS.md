# TEST Server Access Control — Options

## Current Implementation

The TEST server currently uses an **email allowlist** (`SSOAllowedEmail` model + `SSO_ALLOWED_EMAILS` env var) that gates SSO authentication. Only emails explicitly listed can log in. This works but has limitations:

- Every new tester requires a manual entry in the allowlist
- Users who discover the TEST URL still hit the SSO flow and see an error — they know something exists
- Both TEST and PROD share the same WordPress OAuth app, so any WP user with the right tags could attempt access
- The allowlist only protects the SSO path — direct URL access to the Django app itself is still open

---

## Option 1: Separate OAuth App per Environment (Recommended)

**Approach:** Create a second WordPress OAuth application exclusively for TEST. TEST and PROD each get their own OAuth client ID/secret.

**How it works:**
- In WordPress, create a new OAuth app (e.g., "Advisor Portal - TEST") with a different client ID/secret
- Point it to the TEST server's callback URL only
- PROD keeps its existing OAuth app unchanged
- Only users who are authorized in the TEST OAuth app can authenticate

**Pros:**
- Complete isolation — PROD users cannot accidentally or intentionally reach TEST
- No code changes needed in Django (just different `.env` values per server)
- WordPress admin controls who has access to each OAuth app
- Clean separation of concerns

**Cons:**
- Requires WordPress admin access to create a second OAuth app
- Two OAuth apps to manage instead of one
- If the OAuth plugin doesn't support multiple apps easily, may need a workaround

**Effort:** Low — just WordPress configuration + `.env` changes on TEST

---

## Option 2: IP Allowlist via Server Firewall (Strongest)

**Approach:** Restrict the TEST server's port 443 (HTTPS) to only known IP addresses at the network/firewall level.

**How it works:**
- Use DigitalOcean's Cloud Firewall or `ufw` on the droplet itself
- Only allow HTTPS traffic from specific IP addresses (your office, testers' IPs)
- Everyone else gets a connection refused — they don't even see a login page

**Pros:**
- Strongest protection — TEST is invisible to unauthorized users
- No application-level changes
- Works regardless of SSO, direct URLs, or any other access path
- Zero load on the Django app from unauthorized requests

**Cons:**
- Testers with dynamic IPs need frequent updates
- Remote/mobile testers may have changing IPs
- Requires server/firewall admin access
- Can lock yourself out if your IP changes

**Effort:** Low — a few firewall rules. Can be combined with any other option.

**Example (ufw on TEST server):**
```bash
sudo ufw allow from YOUR.OFFICE.IP to any port 443
sudo ufw allow from TESTER.HOME.IP to any port 443
sudo ufw deny 443
```

**Example (DigitalOcean Cloud Firewall):**
- Create firewall rule: Inbound HTTPS (443) → Sources: specific IP list
- Attach to the TEST droplet only

---

## Option 3: HTTP Basic Auth at Nginx Level

**Approach:** Add a username/password prompt at the Nginx reverse proxy level, before Django is even reached.

**How it works:**
- Configure Nginx on the TEST server with `auth_basic`
- Users must enter a shared username/password before they can see the Django app
- This is completely separate from SSO — it's a server-level gate

**Pros:**
- Simple to implement — a few lines in Nginx config
- Users without the password can't even see the login page
- No Django code changes
- Works alongside SSO (two layers of auth)
- Easy to share credentials with testers: "Use `tester` / `ProFedsTest2026`"

**Cons:**
- One shared password for all testers (unless you create multiple htpasswd entries)
- Slightly annoying UX — testers enter credentials twice (HTTP Basic + SSO)
- Password must be shared out-of-band

**Effort:** Very low — 10 minutes of Nginx configuration.

**Example (Nginx config):**
```nginx
server {
    listen 443 ssl;
    server_name test.profeds.com;

    # Basic auth gate
    auth_basic "TEST Environment - Authorized Access Only";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:8000;
        # ... existing proxy config
    }
}
```

**Setup:**
```bash
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd tester
# Enter password when prompted
sudo systemctl reload nginx
```

---

## Option 4: Django Middleware — Environment Gate (Current Approach, Enhanced)

**Approach:** Keep the current email allowlist but enhance it with middleware that blocks ALL requests (not just SSO) from unauthorized users.

**How it works:**
- Add Django middleware that checks every request
- If the user is not authenticated and the page isn't the login/SSO callback, redirect to a "restricted access" page
- If authenticated, verify they're in the allowlist
- Optionally add a "site password" for unauthenticated access

**Pros:**
- Builds on existing infrastructure (SSOAllowedEmail model)
- Managed via Django Admin — no server config needed
- Can add/remove testers without server restarts

**Cons:**
- Application-level protection only — the Django app still receives and processes requests
- More complex than server-level solutions
- Doesn't prevent users from discovering the TEST server exists

**Effort:** Medium — requires new middleware code.

---

## Option 5: VPN-Only Access

**Approach:** Put the TEST server behind a VPN (e.g., WireGuard, Tailscale, or DigitalOcean VPC).

**How it works:**
- Install a VPN solution on the TEST server
- Testers install the VPN client and connect before accessing the TEST URL
- The TEST server only accepts connections from VPN-connected clients

**Pros:**
- Enterprise-grade security — TEST is completely invisible without VPN
- Protects all ports and services, not just the web app
- Centralized access management

**Cons:**
- Requires VPN client installation on every tester's machine
- More complex setup and maintenance
- Overkill for a small testing team
- Can cause connectivity issues for less technical testers

**Effort:** Medium-High — VPN setup and client distribution.

---

## Comparison Matrix

| Option | Security | Ease of Setup | UX Impact | Code Changes | Maintenance |
|--------|----------|--------------|-----------|-------------|-------------|
| 1. Separate OAuth App | High | Low | None | None | Low |
| 2. IP Firewall | Highest | Low | None | None | Medium (IP changes) |
| 3. HTTP Basic Auth | High | Very Low | Minor (extra login) | None | Low |
| 4. Enhanced Middleware | Medium | Medium | None | Yes | Low |
| 5. VPN | Highest | High | Medium (VPN client) | None | High |

---

## Recommendation

**For immediate use:** **Option 3 (HTTP Basic Auth)** — can be set up in 10 minutes, provides a strong gate with zero code changes. Share one password with your testers.

**For long-term:** **Option 1 (Separate OAuth App)** — cleanest separation. TEST and PROD are fully isolated at the authentication source. No extra logins, no IP management, no VPN clients.

**Best combination:** Options 1 + 3 together — separate OAuth app for clean isolation, plus HTTP Basic Auth as an extra layer so even someone with the URL can't see anything without the password.

---

## Revised Approach: Dedicated WordPress Test Accounts (Preferred)

After review, the priority is to **minimize differences between TEST and PROD environments**. Configuring a separate OAuth app is ruled out. Instead, the preferred approach is to create dedicated WordPress test accounts that use the same SSO flow as real users.

### Proposed Test Accounts

| WP Username | Django Role | Purpose |
|-------------|------------|---------|
| DevopsAdmin | administrator | Test admin workflows |
| DevopsManager | manager | Test manager workflows |
| DevopsMember | member | Test member case submission |
| DevopsDelegate | member (delegate) | Test delegate access |
| DevopsBen1 | technician | Test tech workflows |
| DevopsBen2 | technician | Test tech workflows |
| DevopsBen3 | technician | Test tech workflows |

### Email Options for the WP Accounts

**Option A: Gmail "+" aliases (recommended)**

Gmail (and Google Workspace) ignores everything after `+` in the local part. All emails land in one inbox, but WordPress sees each as a unique address:

| WP Account | Email |
|------------|-------|
| DevopsAdmin | devops+admin@profeds.com |
| DevopsManager | devops+manager@profeds.com |
| DevopsMember | devops+member@profeds.com |
| DevopsDelegate | devops+delegate@profeds.com |
| DevopsBen1 | devops+ben1@profeds.com |
| DevopsBen2 | devops+ben2@profeds.com |
| DevopsBen3 | devops+ben3@profeds.com |

All 7 emails deliver to `devops@profeds.com` (or whichever root address you choose). WordPress sees them as unique. You can verify email notifications actually arrive.

**Option B: Fake emails (simplest)**

Use emails at a domain you own but don't check, or use `@example.com` (reserved domain, guaranteed not to exist):

`devopsadmin@profeds.com`, `devopsmember@profeds.com`, etc.

Downside: you can't verify email delivery works. But if Chris can create them without email verification, this is the fastest path.

**Option C: Catch-all with role suffix**

If profeds.com has a catch-all mailbox configured, any address @profeds.com works:

`devops.admin@profeds.com`, `devops.manager@profeds.com`, etc.

All land in the catch-all. WordPress sees unique addresses.

### What to Ask Chris to Configure Per Account

1. **Create each WP user** with the username and email from the chosen option above
2. **Assign the correct WP Fusion / CRM tag** that maps to the Django role (same tags real users get)
3. **Set a known password** for each — or use "forgot password" if the emails are real
4. **Don't require email verification** if using fake emails

### On the Django Side (After Chris Creates Them)

Once the accounts SSO in for the first time, we flag them with `is_test_account=True` (see [TEST_ACCOUNT_OPTIONS.md](TEST_ACCOUNT_OPTIONS.md)), and cleanup scripts will always skip them. No code backdoor, no maintenance headaches. These accounts work identically to real user accounts through the same SSO pipeline.

### Why This Approach Is Best

- **Zero environment differences** — TEST and PROD use the exact same SSO, same tags, same OAuth app
- **Real user experience** — test accounts go through the identical authentication flow as production users
- **No infrastructure changes** — no separate OAuth apps, no firewalls, no VPN, no Nginx changes
- **Permanent** — once created in WordPress and flagged in Django, these accounts persist through any data cleanup
- **Complete role coverage** — all 4 roles + delegate access covered for testing any workflow
---

## Email Alias Analysis: Gmail `+` Addressing vs. Catch-All

### How Gmail `+` Aliases Work

Gmail supports a feature called **plus addressing** (also called **sub-addressing**). You can append `+anything` before the `@` symbol, and Gmail treats it as the same inbox:

| Alias Address | Delivers To |
|---|---|
| `dale@example.com` | `dale@example.com` |
| `dale+devopsadmin@example.com` | `dale@example.com` |
| `dale+devopsmember@example.com` | `dale@example.com` |
| `dale+test123@example.com` | `dale@example.com` |

**Key points:**
- Gmail silently ignores everything between `+` and `@`
- All messages land in the **same inbox** — no separate mailbox to manage
- You can create **unlimited aliases** without any configuration — just use them
- You can **filter** in Gmail by the `to:` address (e.g., filter all mail to `dale+devops*` into a "Test" label)
- The alias is only on the receiving end — the sender (our Django app) sends to the full `+` address and doesn't need to know it's an alias
- WordPress will accept these as valid, unique email addresses when creating accounts

**Practical example for our 7 test accounts:**

| Account | WordPress Email | All deliver to |
|---|---|---|
| DevopsAdmin | `dale+devopsadmin@example.com` | `dale@example.com` |
| DevopsManager | `dale+devopsmanager@example.com` | `dale@example.com` |
| DevopsMember | `dale+devopsmember@example.com` | `dale@example.com` |
| DevopsDelegate | `dale+devopsdelegate@example.com` | `dale@example.com` |
| DevopsBen1 | `dale+devopsben1@example.com` | `dale@example.com` |
| DevopsBen2 | `dale+devopsben2@example.com` | `dale@example.com` |
| DevopsBen3 | `dale+devopsben3@example.com` | `dale@example.com` |

This means one person can monitor all 7 test accounts from a single Gmail inbox, and use Gmail filters/labels to organize them if needed.

### The Catch-All Problem

Chris already has a **catch-all mailbox** configured, which accepts email sent to *any* address at the domain — even addresses that don't exist as real mailboxes. While useful for catching misrouted email, this creates a specific problem for testing:

**What happens with catch-all during testing:**
1. Our Django app sends HOLD, CHAT, or READY emails to test account addresses
2. The catch-all mailbox intercepts **every single one** of these
3. During active testing sessions (where we're repeatedly triggering email flows), dozens of test emails pile up
4. The catch-all inbox gets flooded with test notifications that are indistinguishable from real misrouted mail
5. Chris has to manually sift through or bulk-delete test messages, or risk missing legitimate catch-all items

**Why Gmail `+` aliases are better than catch-all for test emails:**
- **Controlled destination** — emails go to the tester's own Gmail, not Chris's catch-all
- **No inbox pollution** — Chris's catch-all stays clean for its intended purpose (catching misrouted production mail)
- **Self-service** — the tester can read, verify, and delete test emails without involving Chris
- **Filterable** — Gmail filters can auto-label or auto-archive test emails (e.g., `to:dale+devops*` → "DevTest" label, skip inbox)
- **No volume concerns** — Gmail handles the volume; the catch-all mailbox isn't burdened

**Recommendation:** Use Gmail `+` aliases pointed at the tester's own Gmail address. This completely removes the catch-all mailbox from the testing workflow and eliminates the inbox pollution problem Chris has experienced.