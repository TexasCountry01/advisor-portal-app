"""
Fact Finder Content — machine-to-machine API (Option A "Integration contract").

POST /api/fact-finder/resolve-content/ is called by benefits-software with a
Fact Finder Data Contract; it returns the published verbiage blocks that
apply to that specific case, evaluated via each block's display_condition
rules (fact_finder_content/rules.py) against the submitted contract.

See docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md, "Integration
contract with benefits-software" section, for the full design.

AUTH: shared-secret `Authorization: Bearer <key>` header, timing-safe compared
(hmac.compare_digest) against SystemSettings.benefits_software_api_key —
reusing the exact key/field this app already has for the *outbound* direction
(cases/services/api_integration.py), rather than inventing a second secret.
Falls back to settings.BENEFITS_SOFTWARE_API_KEY only if SystemSettings' field
is blank. The shipped placeholder value is deliberately never accepted, so a
misconfigured deployment fails closed instead of silently accepting requests.
"""
import hmac
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cases.fact_finder_data_contract import FactFinderDataContractSerializer
from core.models import SystemSettings

from .models import ContentBlock
from .rules import evaluate_rules

logger = logging.getLogger(__name__)

PLACEHOLDER_API_KEY = 'placeholder-api-key-change-in-production'


def _configured_api_key():
    configured = SystemSettings.get_settings().benefits_software_api_key
    if configured:
        return configured
    return getattr(settings, 'BENEFITS_SOFTWARE_API_KEY', None)


def _is_authorized(request):
    expected = _configured_api_key()
    if not expected or expected == PLACEHOLDER_API_KEY:
        # Fail closed: an unconfigured/placeholder key must never authenticate.
        return False
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False
    received = auth_header[len('Bearer '):]
    return hmac.compare_digest(received, expected)


@csrf_exempt
@require_POST
def resolve_content(request):
    if not _is_authorized(request):
        logger.warning('resolve_content: rejected request with invalid/missing API key')
        return JsonResponse({'error': 'Invalid or missing API key'}, status=403)

    try:
        payload = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Malformed JSON body'}, status=400)

    plan_year = payload.get('plan_year')
    data_contract = payload.get('data_contract')
    if not isinstance(plan_year, int) or not isinstance(data_contract, dict):
        return JsonResponse(
            {'error': "'plan_year' (integer) and 'data_contract' (object) are required."},
            status=400,
        )

    serializer = FactFinderDataContractSerializer(data=data_contract)
    if not serializer.is_valid():
        return JsonResponse({'error': 'Invalid data_contract', 'details': serializer.errors}, status=400)

    validated_contract = serializer.validated_data

    blocks_response = []
    order = 0
    content_blocks = (
        ContentBlock.objects
        .filter(is_active=True)
        .select_related('group')
        .order_by('group__display_order', 'id')
    )
    for block in content_blocks:
        version = block.published_version_for(plan_year)
        if not version:
            continue

        rules = (block.display_condition or {}).get('rules', [])
        try:
            included = evaluate_rules(rules, validated_contract)
        except ValueError:
            logger.warning('resolve_content: block %s has an invalid rule, excluding it', block.key)
            continue

        if included:
            order += 1
            blocks_response.append({'key': block.key, 'html': version.body_html, 'order': order})

    return JsonResponse({'blocks': blocks_response})
