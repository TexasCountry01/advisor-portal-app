"""
Shared name-capitalization normalization for GHL-sourced names.

Used at the GHL -> Portal data boundary by both the SSO login path
(accounts/sso.py) and the direct GHL API path (accounts/ghl_client.py), so
there is exactly one implementation of this rule instead of two copies.
"""


def smart_case(name):
    """Title-case a name ONLY when it arrives entirely lowercase (e.g. GHL
    sometimes supplies 'dale' -> 'Dale'). Preserves an already mixed-case
    name untouched (e.g. 'McGregor', 'DeLuca'), since blindly calling
    .title() on those would incorrectly produce 'Mcgregor'/'Deluca'.
    """
    if not name:
        return name
    s = name.strip()
    return s.title() if s == s.lower() else s
