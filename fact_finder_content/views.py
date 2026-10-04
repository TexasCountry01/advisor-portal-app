"""
Views for the Fact Finder content panel (Option A, step 2-4).

Admin-only for now (mirrors core.views.is_admin's role check). No HTML
sanitization on save yet (step 5) — see docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md.
"""
import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .golden_master import evaluate_display_condition
from .models import ContentBlock, ContentBlockGroup, ContentBlockVersion
from .rules import AVAILABLE_FIELDS, coerce_value, field_value_choices, validate_rules
from .wiring_status import is_wired


def _require_admin(request):
    """Returns an HttpResponseForbidden if the user isn't an administrator, else None."""
    if not (request.user.is_authenticated and request.user.role == 'administrator'):
        return HttpResponseForbidden('Access denied. Administrators only.')
    return None


def _default_plan_year():
    return datetime.date.today().year


def _presentable_rules(rules):
    """Map stored {field, operator, value} rows (dotted schema keys, raw
    operator codes, raw values) to business-friendly display strings for the
    "When should this content appear?" section — purely presentational; the
    underlying stored rule list (field/operator/value) is never altered here."""
    presented = []
    for index, rule in enumerate(rules):
        field_def = AVAILABLE_FIELDS.get(rule['field'], {})
        value = rule['value']
        if field_def.get('type') == 'boolean':
            value_label = 'Yes' if value else 'No'
        else:
            value_label = value
        presented.append({
            'index': index,
            'field_label': field_def.get('label', rule['field']),
            'operator_label': 'is' if rule['operator'] == 'equals' else 'is not',
            'value_label': value_label,
        })
    return presented


@login_required
def content_list(request):
    denied = _require_admin(request)
    if denied:
        return denied

    plan_year = int(request.GET.get('plan_year', _default_plan_year()))

    groups = ContentBlockGroup.objects.prefetch_related('blocks').all()
    group_rows = []
    for group in groups:
        block_rows = []
        for block in group.blocks.filter(is_active=True):
            published = block.published_version_for(plan_year)
            draft = block.versions.filter(
                plan_year=plan_year,
                status=ContentBlockVersion.STATUS_DRAFT,
            ).order_by('-created_at').first()
            block_rows.append({
                'block': block,
                'published': published,
                'draft': draft,
                'is_wired': is_wired(block.key),
            })
        group_rows.append({'group': group, 'blocks': block_rows})

    return render(request, 'fact_finder_content/content_list.html', {
        'group_rows': group_rows,
        'plan_year': plan_year,
    })


@login_required
def content_block_detail(request, block_id):
    denied = _require_admin(request)
    if denied:
        return denied

    block = get_object_or_404(ContentBlock, pk=block_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_draft':
            plan_year = int(request.POST.get('plan_year') or _default_plan_year())
            body_html = request.POST.get('body_html', '')
            version = ContentBlockVersion.objects.create(
                block=block,
                plan_year=plan_year,
                body_html=body_html,
                created_by=request.user,
            )
            missing = version.missing_placeholders()
            if missing:
                messages.warning(
                    request,
                    f'Draft saved, but missing required placeholder(s): {", ".join(missing)}.'
                )
            else:
                messages.success(request, f'Draft saved for plan year {plan_year}.')
            return redirect('fact_finder_content:content_block_detail', block_id=block.id)

        if action == 'submit_for_review':
            version = get_object_or_404(ContentBlockVersion, pk=request.POST.get('version_id'), block=block)
            version.status = ContentBlockVersion.STATUS_IN_REVIEW
            version.save()
            messages.success(request, 'Submitted for review.')
            return redirect('fact_finder_content:content_block_detail', block_id=block.id)

        if action == 'publish':
            version = get_object_or_404(ContentBlockVersion, pk=request.POST.get('version_id'), block=block)
            missing = version.missing_placeholders()
            if missing:
                messages.error(
                    request,
                    f'Cannot publish — missing required placeholder(s): {", ".join(missing)}.'
                )
            else:
                version.publish(by_user=request.user)
                messages.success(request, f'Published for plan year {version.plan_year}.')
            return redirect('fact_finder_content:content_block_detail', block_id=block.id)

        if action == 'add_display_rule':
            field_key = request.POST.get('rule_field', '')
            operator = request.POST.get('rule_operator', '')
            raw_value = request.POST.get('rule_value', '')
            new_rule = {
                'field': field_key,
                'operator': operator,
                'value': coerce_value(field_key, raw_value),
            }
            current_rules = (block.display_condition or {}).get('rules', [])
            candidate_rules = current_rules + [new_rule]

            errors = validate_rules(candidate_rules)
            if errors:
                messages.error(request, 'Could not add rule: ' + ' '.join(errors))
            else:
                block.display_condition = {'rules': candidate_rules}
                block.save()
                messages.success(request, 'Display rule added.')
            return redirect('fact_finder_content:content_block_detail', block_id=block.id)

        if action == 'remove_display_rule':
            index = int(request.POST.get('rule_index', -1))
            current_rules = (block.display_condition or {}).get('rules', [])
            if 0 <= index < len(current_rules):
                current_rules.pop(index)
                block.display_condition = {'rules': current_rules}
                block.save()
                messages.success(request, 'Display rule removed.')
            return redirect('fact_finder_content:content_block_detail', block_id=block.id)

    versions = block.versions.all()

    display_rules = (block.display_condition or {}).get('rules', [])
    presentable_rules = _presentable_rules(display_rules)
    field_options = [
        {'key': key, 'label': field_def['label']}
        for key, field_def in AVAILABLE_FIELDS.items()
    ]
    field_value_options = {key: field_value_choices(key) for key in AVAILABLE_FIELDS}

    # Pre-publish validation gate: show which of the 24 golden-master real
    # cases this block's CURRENT display_condition would appear for, so an
    # admin can catch an unintended audience before ever publishing anything.
    # See docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md's "Concrete
    # UI design" section — this is the missing safety net the shelved
    # feature/pdf-viewer-v2 attempt didn't have.
    golden_master_results = evaluate_display_condition(block.display_condition)
    golden_master_match_count = sum(1 for r in golden_master_results if r['matches'])

    # Pre-fill the "New Draft" editor with the block's current content instead of
    # starting blank — editing a block should default to "modify what's live now",
    # not "retype everything from scratch while squinting at a truncated history
    # table" (the exact confusion this was built to fix). Prefers the published
    # version for the default plan year; falls back to the single most recent
    # version overall (any status/plan year) if nothing is published yet.
    current_version = block.published_version_for(_default_plan_year()) or block.versions.order_by('-id').first()
    current_body_html = current_version.body_html if current_version else ''

    return render(request, 'fact_finder_content/content_block_detail.html', {
        # NOTE: deliberately NOT named 'block' — Django's {% block %} tag pushes a
        # BlockContext entry into context['block'] to support {{ block.super }}, which
        # silently shadows any user context variable named 'block' inside {% block %}...
        # {% endblock %} sections. Use 'content_block' everywhere in the template instead.
        'content_block': block,
        'versions': versions,
        'current_body_html': current_body_html,
        'is_wired': is_wired(block.key),
        'display_rules': display_rules,
        'presentable_rules': presentable_rules,
        'field_options': field_options,
        'field_value_options_json': json.dumps(field_value_options),
        'default_plan_year': _default_plan_year(),
        'golden_master_results': golden_master_results,
        'golden_master_match_count': golden_master_match_count,
        'golden_master_total_count': len(golden_master_results),
    })
