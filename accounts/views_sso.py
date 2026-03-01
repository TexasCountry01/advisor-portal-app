"""
SSO Views — OAuth2 Authorization Code Grant flow

Two views:
  1. sso_login  — Redirects user to WP OAuth authorization page
  2. sso_callback — Handles redirect back from WP, exchanges code, logs user in
"""

import logging
from django.shortcuts import redirect
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.conf import settings

from .sso import (
    generate_state_token,
    get_authorization_url,
    exchange_code_for_token,
    fetch_user_profile,
    get_or_create_user_from_sso,
    SSOError,
    SSOAccessDenied,
)

logger = logging.getLogger(__name__)


def sso_login(request):
    """
    Step 1: Redirect user to WP OAuth authorization page.
    
    Generates a CSRF state token, stores it in session, then redirects to
    the miniOrange authorization endpoint on profeds.com.
    """
    state = generate_state_token()
    request.session['sso_state'] = state
    
    # Preserve 'next' URL for post-login redirect
    next_url = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
    request.session['sso_next'] = next_url
    
    auth_url = get_authorization_url(state)
    return redirect(auth_url)


def sso_callback(request):
    """
    Step 2: Handle redirect back from WP OAuth server.
    
    Flow:
    1. Validate state parameter (CSRF check)
    2. Exchange authorization code for access token
    3. Fetch user profile from resource endpoint
    4. Match or create Django user
    5. Log user in and redirect to dashboard
    """
    # Check for error from OAuth server
    error = request.GET.get('error')
    if error:
        error_desc = request.GET.get('error_description', 'Unknown error')
        logger.error(f'SSO callback error: {error} — {error_desc}')
        messages.error(request, f'Login failed: {error_desc}')
        return redirect('login')
    
    # Validate state parameter
    state = request.GET.get('state')
    stored_state = request.session.pop('sso_state', None)
    
    if not state or state != stored_state:
        logger.warning(f'SSO state mismatch: got={state}, expected={stored_state}')
        messages.error(request, 'Login failed: Invalid session state. Please try again.')
        return redirect('login')
    
    # Get authorization code
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Login failed: No authorization code received.')
        return redirect('login')
    
    try:
        # Exchange code for token
        token_data = exchange_code_for_token(code)
        access_token = token_data['access_token']
        
        # Fetch user profile
        profile_data = fetch_user_profile(access_token)
        logger.info(f'SSO resource payload: {list(profile_data.keys())}')
        
        # Match or create user
        user, created, changes = get_or_create_user_from_sso(profile_data, request=request)
        
        # Log the user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        if created:
            logger.info(f'New SSO user created and logged in: {user.username}')
            messages.success(request, f'Welcome to the Advisor Portal, {user.first_name}!')
        else:
            if changes:
                logger.info(f'SSO user synced and logged in: {user.username} — changes: {changes}')
            
        # Redirect to stored 'next' URL or dashboard
        next_url = request.session.pop('sso_next', settings.LOGIN_REDIRECT_URL)
        return redirect(next_url)
    
    except SSOAccessDenied as e:
        logger.warning(f'SSO access denied: {e}')
        messages.error(request, str(e))
        return redirect('login')
    
    except SSOError as e:
        logger.error(f'SSO error during callback: {e}')
        messages.error(request, 'Login failed due to a technical issue. Please try again or use manual login.')
        return redirect('login')
    
    except Exception as e:
        logger.exception(f'Unexpected SSO error: {e}')
        messages.error(request, 'An unexpected error occurred during login. Please try again.')
        return redirect('login')
