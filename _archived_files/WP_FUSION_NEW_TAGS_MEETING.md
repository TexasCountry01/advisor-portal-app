# Advisor Portal — New Tags Needed in WP Fusion

**Date:** February 28, 2026  
**Prepared for:** WP Fusion Configuration Meeting

---

## What This Is About

We are building a login connection (Single Sign-On) between the ProFeds WordPress website and the Advisor Portal at reports.profeds.com. When someone logs into the ProFeds website, they will be automatically logged into the Advisor Portal — no separate username or password needed.

To make this work, the system needs to know **what role** each user should have in the Advisor Portal. WordPress already has a tagging system through WP Fusion. We just need **7 new tags** added so the portal knows how to handle each person who logs in.

---

## The 7 New Tags We Need

### 4 Role Tags (every portal user gets exactly ONE of these)

| # | Tag to Add | Who Gets This Tag |
|---|-----------|-------------------|
| 1 | `advisor-portal -> role: member` | Financial Advisors who submit cases and view their own reports |
| 2 | `advisor-portal -> role: benefits-technician` | Benefits Technicians who process and review cases |
| 3 | `advisor-portal -> role: administrator` | Administrators with full access to the system |
| 4 | `advisor-portal -> role: manager` | Managers with view-only access to dashboards and analytics |

### 3 Tier Tags (only for Benefits Technicians)

| # | Tag to Add | Who Gets This Tag |
|---|-----------|-------------------|
| 5 | `advisor-portal -> tier: level-1` | New Technicians (work requires senior review) |
| 6 | `advisor-portal -> tier: level-2` | Standard Technicians |
| 7 | `advisor-portal -> tier: level-3` | Senior Technicians (can review others' work) |

---

## Why We Need These

Right now, the WordPress site has many tags for marketing, webinars, events, and membership tracking — but **none of them tell the Advisor Portal what a person's job role is**. Without these tags, the system can't determine whether someone logging in is a Member, a Technician, an Administrator, or a Manager.

Each role sees a completely different view of the portal, so this is essential for security and functionality.

---

## Important: User ID, Not Email

Members sometimes change their email addresses. To make sure we never lose track of someone's cases and account history, the system will identify every user by their **WordPress User ID** (a permanent number that never changes), not by their email.

When a member updates their email in WordPress, everything in the Advisor Portal stays connected — nothing gets lost.

---

## How It Will Work (Simple Overview)

1. A user logs into the **ProFeds WordPress site** as they normally do
2. WordPress sees this person has the tag `advisor-portal -> role: member` (for example)
3. WordPress sends the user over to the **Advisor Portal** with their login information
4. The Advisor Portal recognizes them, logs them in automatically, and shows them the correct dashboard for their role
5. No separate password needed — it's all handled through the existing WordPress login

---

## What We Need From You

1. **Create the 7 tags** listed above in WP Fusion
2. **Assign the correct role tag** to each person who should have access to the Advisor Portal
3. **For Benefits Technicians**, also assign the appropriate tier tag (level 1, 2, or 3)
4. Confirm that the **WordPress User ID** (the number like `705`) is included when sending user information to the portal

---

## Quick Reference: Who Is Who

| Role | What They Do in the Portal | How Many (approx.) |
|------|---------------------------|-------------------|
| **Member** | Submit benefit analysis cases, view their completed reports | Most users |
| **Benefits Technician** | Process and review submitted cases, generate reports | Small team |
| **Administrator** | Manage all users, cases, and system settings | Very few |
| **Manager** | View dashboards and reports (read-only, no changes) | Very few |

---

*Questions? Reach out before the tags are created so we can clarify any assignments.*
