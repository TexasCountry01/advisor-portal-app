# Setup Passwordless Deployment

## Problem
The `dev` user needs sudo password to restart gunicorn, which blocks automated deployments.

## Solution
Configure sudoers to allow `dev` user to restart gunicorn/nginx without password.

## Steps (Run on Remote Server)

### 1. SSH into the server as root or use DigitalOcean console
```bash
ssh root@157.245.141.42
# OR use DigitalOcean Droplet Console from web interface
```

### 2. Create sudoers configuration file
```bash
sudo visudo -f /etc/sudoers.d/dev-deployment
```

### 3. Add the following content:
```
# Allow dev user to restart gunicorn and nginx without password
dev ALL=(ALL) NOPASSWD: /bin/systemctl restart gunicorn
dev ALL=(ALL) NOPASSWD: /bin/systemctl restart nginx
dev ALL=(ALL) NOPASSWD: /bin/systemctl status gunicorn
dev ALL=(ALL) NOPASSWD: /bin/systemctl status nginx
```

### 4. Set correct permissions
```bash
sudo chmod 0440 /etc/sudoers.d/dev-deployment
```

### 5. Test the configuration
```bash
# Switch to dev user
su - dev

# Test restart without password
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## After Setup

Your deployment command will work without password prompts:
```bash
ssh dev@157.245.141.42 "cd /var/www/advisor-portal && git pull origin main && sudo systemctl restart gunicorn"
```

## Alternative: Use DigitalOcean Console

If you don't have the sudo password:
1. Log into DigitalOcean dashboard
2. Go to your Droplet (157.245.141.42)
3. Click "Console" or "Access" → "Launch Droplet Console"
4. You'll have root access directly
5. Run the commands above

## Repeat for PROD Server (104.248.126.74)

Run the same steps on the production server.
