"""
Template context processor that provides a cache-busting version string.

Reads the short git commit hash once at startup and injects it as {{ ASSET_VERSION }}
into all templates. Use it as a query parameter on static file URLs:

    <link rel="stylesheet" href="{% static 'css/main.css' %}?v={{ ASSET_VERSION }}">
"""
import subprocess
import logging

logger = logging.getLogger(__name__)

# Read once at process start — changes only on deploy/restart
try:
    _version = subprocess.check_output(
        ['git', 'rev-parse', '--short', 'HEAD'],
        stderr=subprocess.DEVNULL,
        timeout=5,
    ).decode().strip()
except Exception:
    _version = '1'
    logger.debug('Could not read git hash for ASSET_VERSION, using fallback')


def asset_version(request):
    return {'ASSET_VERSION': _version}
