# Email Response — SSO Tag Discussion

---

Hi Chris,

Thank you for the thoughtful feedback — great questions. Here are my thoughts on each:

**1. Tags as the only access control — Yes, keep it simple.**

That's exactly how I'd like it to work. One tag = access. Remove the tag = no access. We don't need to look at "Active Member" status or any other attribute. If someone has the `Portal: Member` tag, they can log in. If it's removed, they're locked out. Simple to grant, simple to revoke.

**2. Administrator tag security — Completely agree with your concern.**

I'd recommend we do NOT use SSO tags for Administrator or Manager access at all. Those are a very small number of people, and I can set up their accounts directly in the portal with secure credentials. That way, there's zero risk of someone tagging themselves into admin access. SSO tags would only be used for Members and Technicians.

**3. Tech levels — your call.**

If you'd prefer to control technician levels inside the portal (from the Admin/Manager dashboard), we can simplify down to just one tag: `Portal: Technician`. I would then set their level (1, 2, or 3) inside the portal when their account is created. That means promotions and level changes happen in the portal, not in GHL. Fewer tags to manage on your side. But if you'd rather keep three separate tags for the tech levels, that works too — either way is fine on my end.

**4. Delegates — no tags needed.**

Delegates do not get a portal tag and do not go through SSO. Delegate assignments are managed exclusively by Benefits Technicians inside the portal — members (advisors) do not assign their own delegates. This keeps it tightly controlled and prevents members from granting access on their own.

Important safeguard: a Benefits Technician can only assign someone as a delegate if that person already has an authorized user account in the portal. They can't just type in a name — the person must already exist in the system. This prevents unauthorized access.

Benefits Technicians can add, change, or remove delegate assignments at any time — no GHL changes needed. The portal tracks who made each assignment and when.

If a delegate also happens to be a member (advisor) in their own right, they'd have the `Portal: Member` tag for their own account, and the delegate assignment is a separate thing managed by the Benefits Technician.

**Bottom line — the tag list could be as simple as:**

- `Portal: Member`
- `Portal: Technician` (if tech levels are managed in the portal)

Or if you prefer tag-based tech levels:

- `Portal: Member`
- `Portal: Technician - Level 1`
- `Portal: Technician - Level 2`
- `Portal: Technician - Level 3`

No tags needed for Administrator, Manager, or Delegates.

Agreed on no automation for now — we'll figure out the right triggers together before adding any.

Let me know which direction you'd like to go on the tech levels, and I'll get everything set up on my side.

Best,  
Phil

---
