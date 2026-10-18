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
import html
import json
import logging
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cases.fact_finder_data_contract import FactFinderDataContractSerializer
from core.models import SystemSettings

from .models import ContentBlock, ContentBlockVersion, ContentSlot, ContentSlotVersion
from .merge_field_policy import (
    extract_merge_field_tokens,
    validate_merge_field_policy,
    validate_merge_field_template,
)
from .rules import (
    RuleEvaluationError,
    RuleOutcome,
    RuleValidationError,
    evaluate_rules,
    evaluate_rules_v2,
    validate_condition_v2,
)

logger = logging.getLogger(__name__)

PLACEHOLDER_API_KEY = 'placeholder-api-key-change-in-production'
_MERGE_TOKEN_RE = re.compile(r'\[\[([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\]\]')
_NUMERIC_MERGE_FORMATTERS = {
    'tsp.deff_limit': 'whole_number',
    'tsp.catchup_limit': 'whole_number',
    'social_security.ss_earned_income_limit': 'whole_number',
    'pension.unused_sick_leave_months': 'two_decimals',
    'tsp.sal_percentage_in_contri_rounded': 'integer',
}
_V2_MERGE_FIELD_CAPABILITY = 'merge_field_validation_v1'
_MISSING_MERGE_VALUE = object()


class _StrictMergeFieldError(Exception):
    def __init__(self, reason_code, tokens=()):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.tokens = sorted(set(tokens))


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


def _nested_value(data, dotted_path):
    value = data
    for part in dotted_path.split('.'):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _format_merge_value(value, formatter):
    try:
        number = Decimal(str(value))
    except (ArithmeticError, ValueError):
        raise ValueError('Invalid numeric merge value.')
    if not number.is_finite():
        raise ValueError('Invalid numeric merge value.')
    if formatter == 'whole_number':
        return f'{number.quantize(Decimal("1"), rounding=ROUND_HALF_UP):,}'
    if formatter == 'two_decimals':
        return f'{number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):,}'
    if formatter == 'integer':
        return str(number.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    raise ValueError('Unsupported merge formatter.')


def _substitute_merge_fields(html, data_contract):
    """Apply the existing dotted-token convention without evaluating templates."""
    def replace_token(match):
        path = match.group(1)
        value = _nested_value(data_contract, path)
        if value is None or isinstance(value, (dict, list)):
            return match.group(0)

        formatter = _NUMERIC_MERGE_FORMATTERS.get(path)
        if formatter:
            return _format_merge_value(value, formatter)
        if isinstance(value, bool):
            return '1' if value else ''
        return str(value)

    return _MERGE_TOKEN_RE.sub(replace_token, html)


def _strict_merge_value(data_contract, dotted_path):
    value = data_contract
    for part in dotted_path.split('.'):
        if not isinstance(value, dict) or part not in value:
            return _MISSING_MERGE_VALUE
        value = value[part]
    return value


def _strict_value_matches_type(value, value_type):
    if value_type == 'string':
        return isinstance(value, str)
    if value_type == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == 'decimal':
        return isinstance(value, Decimal) and value.is_finite()
    if value_type == 'boolean':
        return isinstance(value, bool)
    if value_type == 'date':
        return isinstance(value, date) and not isinstance(value, datetime)
    if value_type == 'datetime':
        return isinstance(value, datetime)
    return False


def _strict_format_merge_value(value, definition):
    format_name = definition['format']
    if format_name == 'display_mdy':
        try:
            datetime.strptime(value, '%m/%d/%Y')
        except ValueError:
            raise _StrictMergeFieldError('invalid_merge_value', [definition['token']])
    elif format_name == 'display_month_year':
        try:
            datetime.strptime(value, '%B %Y')
        except ValueError:
            raise _StrictMergeFieldError('invalid_merge_value', [definition['token']])

    formatter = _NUMERIC_MERGE_FORMATTERS.get(definition['token'])
    if formatter:
        try:
            return _format_merge_value(value, formatter)
        except ValueError:
            raise _StrictMergeFieldError('invalid_merge_value', [definition['token']])
    if isinstance(value, bool):
        return '1' if value else ''
    return str(value)


def _strict_substitute_merge_fields(content_version, raw_data_contract, validated_contract):
    if content_version.merge_field_policy is None:
        raise _StrictMergeFieldError('merge_policy_missing')

    try:
        policy_definitions = validate_merge_field_policy(content_version.merge_field_policy)
        html_tokens = extract_merge_field_tokens(content_version.body_html)
    except ValidationError as exc:
        reason = (
            'unknown_merge_token'
            if any('Unknown Data Contract merge token' in str(message) for message in exc.messages)
            else 'invalid_published_content'
        )
        raise _StrictMergeFieldError(reason) from exc

    unknown_tokens = html_tokens - set(policy_definitions)
    if unknown_tokens:
        raise _StrictMergeFieldError('unknown_merge_token', unknown_tokens)

    try:
        validate_merge_field_template(
            content_version.body_html,
            content_version.merge_field_policy,
            content_version.block.required_placeholders,
        )
    except ValidationError as exc:
        reason = (
            'unknown_merge_token'
            if any('absent from the policy' in str(message) for message in exc.messages)
            else 'invalid_published_content'
        )
        raise _StrictMergeFieldError(reason) from exc

    replacements = {}
    for token, definition in policy_definitions.items():
        raw_value = _strict_merge_value(raw_data_contract, token)
        value = _strict_merge_value(validated_contract, token)
        if raw_value is _MISSING_MERGE_VALUE:
            raise _StrictMergeFieldError('missing_required_merge_value', [token])
        if raw_value is None:
            raise _StrictMergeFieldError('null_required_merge_value', [token])
        if isinstance(raw_value, str) and not raw_value.strip():
            raise _StrictMergeFieldError('blank_required_merge_value', [token])
        if definition['value_type'] in {'string', 'integer', 'boolean'}:
            value = raw_value
        elif value is _MISSING_MERGE_VALUE:
            raise _StrictMergeFieldError('missing_required_merge_value', [token])
        elif value is None:
            raise _StrictMergeFieldError('null_required_merge_value', [token])
        if not _strict_value_matches_type(value, definition['value_type']):
            raise _StrictMergeFieldError('invalid_merge_value', [token])
        formatted_value = _strict_format_merge_value(value, definition)
        if not formatted_value.strip():
            raise _StrictMergeFieldError('invalid_merge_value', [token])
        replacements[token] = html.escape(formatted_value, quote=False)

    result = _MERGE_TOKEN_RE.sub(
        lambda match: replacements[match.group(1)],
        content_version.body_html,
    )
    try:
        unresolved_tokens = extract_merge_field_tokens(result)
    except ValidationError as exc:
        raise _StrictMergeFieldError('invalid_published_content') from exc
    if unresolved_tokens:
        raise _StrictMergeFieldError('invalid_published_content', unresolved_tokens)
    return result


def _v2_error(message, status, resolution_id=None):
    response = {'error': message}
    if resolution_id:
        response['resolution_id'] = resolution_id
    return JsonResponse(response, status=status)


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


@csrf_exempt
@require_POST
def resolve_content_v2(request):
    if not _is_authorized(request):
        logger.warning('resolve_content_v2: rejected request with invalid/missing API key')
        return _v2_error('unauthorized', 403)

    try:
        payload = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        return _v2_error('invalid_request', 400)
    if not isinstance(payload, dict):
        return _v2_error('invalid_request', 400)

    api_version = payload.get('api_version')
    plan_year = payload.get('plan_year')
    slot_keys = payload.get('slots')
    data_contract = payload.get('data_contract')
    capabilities = payload.get('capabilities', [])
    if (
        not isinstance(capabilities, list)
        or not all(isinstance(capability, str) for capability in capabilities)
        or len(capabilities) != len(set(capabilities))
    ):
        return _v2_error('invalid_request', 400)
    unsupported_capabilities = set(capabilities) - {_V2_MERGE_FIELD_CAPABILITY}
    if unsupported_capabilities:
        return _v2_error('unsupported_capability', 400)
    strict_merge_validation = _V2_MERGE_FIELD_CAPABILITY in capabilities
    if type(api_version) is not int or api_version != 2:
        return _v2_error('unsupported_api_version', 400)
    if (
        type(plan_year) is not int
        or not 1 <= plan_year <= 9999
        or not isinstance(slot_keys, list)
        or not all(isinstance(key, str) and key for key in slot_keys)
        or not isinstance(data_contract, dict)
    ):
        return _v2_error('invalid_request', 400)
    if len(slot_keys) != len(set(slot_keys)):
        return _v2_error('duplicate_slots', 400)

    serializer = FactFinderDataContractSerializer(data=data_contract)
    if strict_merge_validation:
        pension_serializer = serializer.fields['pension']
        pension_serializer.fields['cola'].allow_blank = True
        pension_serializer.fields['retirement_date'].allow_blank = True
    if not serializer.is_valid():
        # Do not return serializer details: choice/type errors can echo supplied values.
        return _v2_error('invalid_data_contract', 400)
    validated_contract = serializer.validated_data
    resolution_id = str(uuid.uuid4())

    requested_slots = {
        slot.key: slot
        for slot in ContentSlot.objects.filter(key__in=slot_keys)
    }
    published_config_rows = list(
        ContentSlotVersion.objects.filter(
            slot__key__in=slot_keys,
            plan_year=plan_year,
            status=ContentSlotVersion.STATUS_PUBLISHED,
        ).select_related('slot')
    )
    published_configs = {}
    for config in published_config_rows:
        if config.slot.key in published_configs:
            logger.error(
                'resolve_content_v2: multiple published configurations for slot %s and year %s',
                config.slot.key,
                plan_year,
            )
            return _v2_error('invalid_published_configuration', 500, resolution_id)
        published_configs[config.slot.key] = config
    decisions = []
    config_version_refs = {
        slot_key: str(config.pk)
        for slot_key, config in published_configs.items()
    }
    for slot_key in slot_keys:
        slot = requested_slots.get(slot_key)
        if slot is None:
            decisions.append({
                'slot_key': slot_key,
                'status': 'configuration_missing',
                'reason_code': 'slot_not_found',
            })
            continue

        config = published_configs.get(slot_key)
        if not slot.is_active:
            decision = {
                'slot_key': slot_key,
                'status': 'configuration_missing',
                'reason_code': 'slot_inactive',
            }
            if config is not None:
                decision['slot_config_version'] = str(config.pk)
            decisions.append(decision)
            continue

        if config is None:
            decisions.append({
                'slot_key': slot_key,
                'status': 'configuration_missing',
                'reason_code': 'no_published_slot_configuration',
            })
            continue

        try:
            config.full_clean()
            variants = config.configuration['variants']
            evaluations = []
            for variant in variants:
                condition = variant['when']
                validate_condition_v2(condition)
                evaluations.append((variant, evaluate_rules_v2(condition, data_contract)))
        except RuleEvaluationError:
            logger.warning(
                'resolve_content_v2: invalid employee fact type for slot %s',
                slot_key,
            )
            return _v2_error('invalid_data_contract', 400, resolution_id)
        except (ValidationError, RuleValidationError, KeyError, TypeError, ValueError):
            logger.error(
                'resolve_content_v2: invalid published configuration for slot %s (version %s)',
                slot_key,
                config.pk,
            )
            return _v2_error('invalid_published_configuration', 500, resolution_id)

        if slot.requirement == ContentSlot.REQUIREMENT_CALCULATION_DRIVEN:
            decisions.append({
                'slot_key': slot_key,
                'status': 'no_match',
                'reason_code': 'calculation_driven_slot',
                'slot_config_version': str(config.pk),
            })
            continue

        matching = [
            variant for variant, result in evaluations
            if result.outcome is RuleOutcome.MATCH
        ]
        unknown_facts = sorted({
            fact
            for _variant, result in evaluations
            if result.outcome is RuleOutcome.UNKNOWN
            for fact in result.unknown_facts
        })
        if len(matching) > 1:
            decisions.append({
                'slot_key': slot_key,
                'status': 'ambiguous',
                'variant_ids': [variant['variant_id'] for variant in matching],
                'reason_code': 'multiple_matching_variants',
                'slot_config_version': str(config.pk),
            })
            continue
        if unknown_facts and (not matching or len(matching) == 1):
            decisions.append({
                'slot_key': slot_key,
                'status': 'unknown_facts',
                'unknown_facts': unknown_facts,
                'reason_code': 'required_facts_unknown',
                'slot_config_version': str(config.pk),
            })
            continue
        if not matching:
            decisions.append({
                'slot_key': slot_key,
                'status': 'no_match',
                'reason_code': 'no_variant_matched',
                'slot_config_version': str(config.pk),
            })
            continue

        selected = matching[0]
        if selected['action'] == 'suppress':
            decisions.append({
                'slot_key': slot_key,
                'status': 'suppressed',
                'variant_id': selected['variant_id'],
                'reason_code': 'explicit_suppression_variant',
                'slot_config_version': str(config.pk),
            })
            continue

        content_key = selected['content_key']
        content_versions = list(ContentBlockVersion.objects.filter(
            block__key=content_key,
            plan_year=plan_year,
            status=ContentBlockVersion.STATUS_PUBLISHED,
        ).select_related('block'))
        if not content_versions:
            decisions.append({
                'slot_key': slot_key,
                'status': 'missing_publication',
                'variant_id': selected['variant_id'],
                'content_key': content_key,
                'plan_year': plan_year,
                'reason_code': 'no_published_content_for_plan_year',
                'slot_config_version': str(config.pk),
            })
            continue
        if len(content_versions) > 1:
            logger.error(
                'resolve_content_v2: multiple published wording versions for content key %s and year %s',
                content_key,
                plan_year,
            )
            return _v2_error('invalid_published_content', 500, resolution_id)
        content_version = content_versions[0]
        if not content_version.block.is_active:
            logger.error(
                'resolve_content_v2: inactive content block referenced by published slot %s',
                slot_key,
            )
            return _v2_error('invalid_published_configuration', 500, resolution_id)

        if strict_merge_validation:
            try:
                resolved_html = _strict_substitute_merge_fields(
                    content_version,
                    data_contract,
                    validated_contract,
                )
            except _StrictMergeFieldError as exc:
                failed_decision = {
                    'slot_key': slot_key,
                    'status': (
                        'merge_field_error'
                        if exc.reason_code.endswith('_merge_value')
                        else 'invalid_published_content'
                    ),
                    'reason_code': exc.reason_code,
                    'variant_id': selected['variant_id'],
                    'content_key': content_key,
                    'content_version': str(content_version.pk),
                    'slot_config_version': str(config.pk),
                }
                if exc.tokens:
                    failed_decision['merge_field_errors'] = [
                        {'token': token, 'reason_code': exc.reason_code}
                        for token in exc.tokens
                    ]
                decisions.append(failed_decision)
                continue
        else:
            try:
                resolved_html = _substitute_merge_fields(content_version.body_html, data_contract)
            except ValueError:
                logger.error('resolve_content_v2: invalid merge field value for slot %s', slot_key)
                return _v2_error('invalid_published_content', 500, resolution_id)
        decisions.append({
            'slot_key': slot_key,
            'status': 'selected',
            'variant_id': selected['variant_id'],
            'content_key': content_key,
            'html': resolved_html,
            'content_version': str(content_version.pk),
            'slot_config_version': str(config.pk),
        })

    response = {
        'api_version': 2,
        'plan_year': plan_year,
        'resolution_id': resolution_id,
        'slot_config_versions': config_version_refs,
        'slots': decisions,
    }
    if strict_merge_validation:
        response['capabilities'] = [_V2_MERGE_FIELD_CAPABILITY]
    return JsonResponse(response)
