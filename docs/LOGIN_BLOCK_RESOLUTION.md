# Login Block Resolution

## What Happened

When logging in as many different users from the same computer, the hosting company's security system flagged the activity as suspicious. It looks the same as a hacker trying stolen passwords, so it blocked your IP address from both sites.

## How to Fix It

Ask your **hosting company** or **WordPress developer** to do ONE of these:

1. **Whitelist your IP address** — This tells the security system to trust your computer and stop blocking you
2. **Increase the login attempt limit** — Allow more logins before triggering a block
3. **Temporarily disable brute-force protection** while you finish provisioning, then re-enable it

## Where the Block Might Be

Your WordPress developer should check these (in order):

1. **Security plugins** installed on the WordPress sites (Wordfence, iThemes, Sucuri, etc.) — check their block/lockout logs
2. **Cloudflare** or any CDN — if the sites use one, it may have its own rate limiting
3. **The hosting company itself** — if it's not a plugin, only the host can remove the block

## Going Forward

To avoid getting blocked again while provisioning the remaining users:

- **Do 10–20 users at a time**, then take a break before doing more
- **Ask the WP developer to whitelist your IP** before you start the next batch
- If possible, ask the WP developer if roles can be **assigned in bulk** through the WordPress admin instead of logging in as each user individually
