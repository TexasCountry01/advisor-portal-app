# Advisor Portal — Workshop Codes & Delegate Access Options

**Date:** February 28, 2026  
**Purpose:** Present options for how members, workshop codes, and delegates work together

---

## The Situation

In the Advisor Portal, we need to support the following real-world scenarios:

- **A member (financial advisor) may work with multiple workshop codes** — not just one
- **A delegate (staff person) may work for more than one advisor**, each with different workshop codes
- **Delegates should only see cases for the specific workshop codes they are assigned to** — not everything the advisor has access to
- **Delegate assignments need to be controlled** — managed by Benefits Technicians inside the portal, not by members (advisors) and not through WordPress or SSO

---

## How It Works Today

Currently, each member has **one** workshop code. Delegates are assigned to a workshop code and can submit cases for any member in that workshop.

**What needs to change:** Members need to be associated with **multiple** workshop codes, and delegates need to be scoped to only the specific workshop codes they are authorized for.

---

## Options

### Option A — Manage Everything in the Advisor Portal *(Recommended)*

**How it works:**
- Benefits Technicians assign workshop codes to members directly in the portal
- Benefits Technicians assign delegates to specific workshop codes in the portal
- Members (advisors) do not assign their own delegates — this is controlled by the Benefits Technician team
- A person must already have an authorized user account in the portal before they can be assigned as a delegate — Benefits Technicians select from existing users only
- A delegate only sees cases under the workshop codes they've been assigned to
- Nothing changes on the WordPress / SSO side

**Example:**

| Person | Role | Workshop Codes |
|--------|------|---------------|
| Anna Haber | Member (Advisor) | MRP, FWS, GVT |
| John Smith | Delegate for Anna | MRP only |
| Jane Doe | Delegate for Anna | MRP and FWS |

- Anna sees all her cases across MRP, FWS, and GVT
- John only sees Anna's MRP cases
- Jane sees Anna's MRP and FWS cases, but not GVT

**Pros:**
- No changes needed on the WordPress or SSO side
- Benefits Technicians have full control over all delegate assignments
- Members cannot grant access on their own
- Easy to adjust when delegates change — just update in the portal
- Full audit trail of who assigned what and when

**Cons:**
- Benefits Technicians must manage workshop code and delegate assignments in the portal

---

### Option B — WordPress Sends Workshop Codes, Portal Manages Delegates

**How it works:**
- WordPress sends the member's workshop code(s) during SSO login
- The portal automatically updates which workshop codes belong to that member
- Delegate assignments are still managed by Benefits Technicians in the portal

**Example:**
- When Anna logs in through WordPress, the system receives her workshop codes (MRP, FWS, GVT) and updates her portal profile automatically
- Benefits Technicians still assign John and Jane to specific workshop codes in the portal

**Pros:**
- Workshop code assignments for members stay in sync with WordPress automatically
- Delegate assignments are still controlled in the portal

**Cons:**
- Requires adding workshop codes as tags or fields in WordPress / WP Fusion
- Any changes to workshop codes in WordPress affect the portal immediately (could be a pro or a con)
- More setup work on the WordPress side

---

### Option C — WordPress Manages Everything (Workshop Codes + Delegates)

**How it works:**
- Workshop codes AND delegate assignments are all managed through WordPress tags
- The portal reads everything from WordPress during login

**Pros:**
- Single place to manage everything (WordPress)

**Cons:**
- Delegate assignments are complex and change frequently — WordPress tags are not designed for this level of detail
- Much more setup and maintenance work on the WordPress side
- Harder to control who can see what — tags don't naturally support "John can see MRP but not FWS"
- **Not recommended** due to complexity and lack of fine-grained control

---

## Side-by-Side Comparison

| Feature | Option A (Portal Only) | Option B (Hybrid) | Option C (WordPress Only) |
|---------|----------------------|-------------------|--------------------------|
| Workshop codes managed in | Portal | WordPress | WordPress |
| Delegate assignments managed in | Portal | Portal | WordPress |
| Changes to WordPress needed | None | Some | Significant |
| Fine-grained delegate control | Yes | Yes | Difficult |
| Benefits Tech/Admin control | Full | Partial | Limited |
| Maintenance effort | Normal | Normal | High |
| Audit trail | Complete | Partial | Limited |
| **Recommendation** | **Best fit** | Viable | Not recommended |

---

## Our Recommendation: Option A

Option A keeps all the control inside the Advisor Portal where Benefits Technicians can manage it directly. Members (advisors) cannot assign their own delegates. It requires **no changes to WordPress or SSO**, keeps things simple, and gives you the most flexibility.

Workshop code assignments and delegate permissions can be updated at any time by Benefits Technicians, with a full record of every change.

---

## What This Looks Like Day-to-Day

1. **New member joins** → Benefits Tech assigns their workshop code(s) in the portal
2. **Member gets a new workshop code** → Benefits Tech adds it in the portal
3. **Delegate needs access** → Benefits Tech assigns the delegate to specific workshop code(s)
4. **Delegate no longer needs access** → Benefits Tech removes or deactivates the assignment
5. **Advisor leaves** → Benefits Tech deactivates the member, all delegate access automatically stops

All of this is tracked — who made the change, when, and why.

---

*Questions or preferences? Let us know which option works best for your team.*
