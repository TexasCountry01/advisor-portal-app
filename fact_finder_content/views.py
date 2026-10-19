"""
Views for the Fact Finder content panel (Option A, step 2-4).

Admin-only for now (mirrors core.views.is_admin's role check). No HTML
sanitization on save yet (step 5) — see docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md.
"""
import datetime
import json
from copy import deepcopy
from html import unescape
from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.html import strip_tags

from core.models import SystemSettings
from . import pdf_structure_map
from .golden_master import evaluate_display_condition
from .forms import WordingDraftForm
from .models import ContentBlock, ContentBlockGroup, ContentBlockVersion
from .rules import AVAILABLE_FIELDS, coerce_value, field_value_choices, validate_rules
from .wiring_status import is_wired
from .sanitize import sanitize_body_html


def _require_admin(request):
    """Returns an HttpResponseForbidden if the user isn't an administrator, else None."""
    if not (request.user.is_authenticated and request.user.role == 'administrator'):
        return HttpResponseForbidden('Access denied. Administrators only.')
    return None


def _validation_messages(error):
    return error.messages if isinstance(error, ValidationError) else [str(error)]


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


def _clean_system_type(raw_value):
    """Validate a GET-submitted system_type against pdf_structure_map's own
    known values; an unrecognized/missing value falls back to the first
    known value rather than trusting arbitrary input."""
    if raw_value in pdf_structure_map.SYSTEM_TYPES:
        return raw_value
    return pdf_structure_map.SYSTEM_TYPES[0]


def _clean_retirement_type(raw_value):
    """Validate a GET-submitted retirement_type against pdf_structure_map's
    own known values; '' or anything unrecognized means 'Any' (no
    retirement-type filter applied), never a raised error or a trusted
    arbitrary string."""
    if raw_value in pdf_structure_map.RETIREMENT_TYPES:
        return raw_value
    return None


def _safe_next_url(request):
    """Return request.GET['next'] if, and only if, it passes Django's own
    open-redirect guard (the same django.utils.http.url_has_allowed_host_and_scheme
    helper Django's own LoginView/auth views use to validate a 'next'
    parameter) — otherwise '' (never trust an unvalidated value as a
    redirect target). Reads request.GET even for POST requests, since a
    query string is present on any request method and every form on
    content_block_detail.html omits its own `action` attribute, so it
    resubmits back to the same URL (path + query string) it was rendered
    from — meaning a `next` present on the original GET automatically
    reappears in request.GET on every subsequent POST to that same page."""
    next_url = request.GET.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ''


def _pdf_preview_return_url(system_type, retirement_type, plan_year, group_key=None, row_block_id=None):
    """Build the canonical PDF-ordered preview URL (fact_finder_content:content_list),
    carrying forward the current scenario (and, optionally, which section/row to
    re-expand and scroll to on return) as a query string. Used both to build each
    row's "Edit" link (as its `next` target) and, indirectly, to restore that same
    scenario/row when content_block_detail later redirects back here."""
    params = {'system_type': system_type, 'plan_year': plan_year}
    if retirement_type:
        params['retirement_type'] = retirement_type
    if group_key:
        params['section'] = group_key
    if row_block_id:
        params['row_block_id'] = row_block_id
    return f"{reverse('fact_finder_content:content_list')}?{urlencode(params)}"


def _edit_url_for(block_id, system_type, retirement_type, plan_year, group_key=None, row_block_id=None):
    """Build an "Edit" link target for one content row: the existing, unmodified
    content_block_detail route, with a `next` query parameter pointing back to the
    canonical PDF-ordered preview with the current scenario (and, for governed PDF
    rows, which section/row to re-expand) preserved. Introduces no new editing
    behavior — content_block_detail already reads/validates `next` via
    _safe_next_url() above and falls back to the plain content_list URL if it is
    absent or unsafe."""
    return_to = _pdf_preview_return_url(system_type, retirement_type, plan_year, group_key, row_block_id)
    edit_path = reverse('fact_finder_content:content_block_detail', args=[block_id])
    return f"{edit_path}?{urlencode({'next': return_to, 'plan_year': plan_year})}"


def _describe_condition(entry):
    """Build a plain-language applicability sentence from a SlotEntry's own
    documented system_type/retirement_type/description fields. Presentation
    only — transcribes data already declared in pdf_structure_map.py; does
    not evaluate ContentBlock.display_condition or any business rule."""
    parts = []
    if entry.system_type:
        parts.append('System type: ' + ' or '.join(entry.system_type))
    if entry.retirement_type:
        parts.append('Retirement type: ' + ' or '.join(entry.retirement_type))
    if entry.description:
        description = entry.description
        for section in pdf_structure_map.PDF_STRUCTURE_MAP:
            for related_entry in section.entries:
                if (
                    related_entry.key
                    and related_entry.key in description
                    and related_entry.label
                ):
                    description = description.replace(related_entry.key, related_entry.label)
        parts.append(description)
    return ' — '.join(parts)


def _short_applicability_label(entry):
    """A compact, badge-sized applicability label (e.g. 'FERS or Transfers',
    'Deferred only', 'Always shown') for the collapsed row header — the
    short counterpart to _describe_condition's longer, detail-panel text.
    Presentation only; introduces no new rule-evaluation logic."""
    parts = []
    if entry.system_type:
        parts.append(' or '.join(entry.system_type))
    if entry.retirement_type:
        parts.append(' or '.join(entry.retirement_type))
    return ' · '.join(parts) if parts else 'Always shown'


def _content_row_dom_id(group_key, index):
    """A stable, unique HTML id for one governed content row's expandable
    published-content panel. Includes the row's position within its
    section's rendered scenario outline so repeated occurrences cannot
    collide. The content key is intentionally omitted so the HTML identifier
    does not expose it when technical identifiers are disabled."""
    return f'content-{group_key}-{index}'


def _section_display_rows(report_section, system_type, retirement_type):
    """Build an ordered list of display rows for one ReportSection: the
    GOVERNED entries resolve_outline() returns for the given scenario (in
    PDF order), with each COMPUTED placeholder inserted immediately after
    whichever rendered governed row(s) it is documented (anchor_after /
    anchor_after_variant_group) to follow. Pure presentation logic over
    pdf_structure_map's own static data — performs no business calculation,
    reads no live Fact Finder Data Contract data, and does not evaluate
    ContentBlock.display_condition."""
    rendered_entries = pdf_structure_map.resolve_outline(report_section.group_key, system_type, retirement_type)
    rendered_keys = [entry.key for entry in rendered_entries]
    ties = pdf_structure_map.variant_tie_groups((report_section,))

    items = []
    for index, entry in enumerate(rendered_entries):
        tie_members = []
        for bp in entry.positions:
            members = ties.get((report_section.group_key, bp.branch, bp.position))
            if members and len(members) > 1:
                tie_members = [member for member in members if member.key != entry.key]
                break
        items.append((float(index), {
            'kind': 'governed',
            'entry': entry,
            'condition': _describe_condition(entry),
            'applicability_label': _short_applicability_label(entry),
            'tie_members': tie_members,
            'dom_id': _content_row_dom_id(report_section.group_key, index),
        }))

    for entry in report_section.entries:
        if entry.kind is not pdf_structure_map.SlotKind.COMPUTED:
            continue
        anchor_keys = entry.anchor_after_variant_group or (entry.anchor_after,)
        matched_indexes = [i for i, key in enumerate(rendered_keys) if key in anchor_keys]
        if not matched_indexes:
            # This scenario doesn't render any key this placeholder follows
            # (e.g. the CSRS-branch SBP table when the scenario is FERS) —
            # correctly omitted, not an error.
            continue
        items.append((max(matched_indexes) + 0.5, {'kind': 'computed', 'entry': entry}))

    items.sort(key=lambda pair: pair[0])
    return [row for _sort_key, row in items]


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
def pdf_order_preview(request):
    """Read-only preview of the real PDF's reading order, grouped/sequenced
    per fact_finder_content.pdf_structure_map instead of content_list's
    alphabetical-by-label fallback (see PDF_CONTENT_ARCHITECTURE_AUDIT.md).

    GET renders the outline; an eligible Super Dev POST changes only a
    session-scoped display preference. Neither method mutates content.
    Does not evaluate ContentBlock.display_condition, does not read
    any real employee/case data, and does not generate or resemble any
    specific retiree's actual PDF — it only renders pdf_structure_map's own
    static, declarative data for a hypothetical, user-selected scenario.

    Phase 2C-1: each governed row's `published`/`draft` ContentBlockVersion
    objects (already retrieved below via the pre-existing
    `published_version_for()`/`.versions.filter(status=...)` calls — no new
    query is added to expose this) are passed through to the template so an
    administrator can expand a row and read the actual published wording.
    `ContentBlockVersion.body_html` is sanitized at save time by
    `sanitize_body_html()` (see `models.py::ContentBlockVersion.save()` and
    `sanitize.py`) — the template renders it with Django's `|safe` filter,
    the same, already-established pattern `content_block_detail.html`
    already uses for this exact field. Draft content is never rendered as
    page body — only its presence/absence drives the existing "Draft" badge.
    """
    if request.method not in ('GET', 'POST'):
        return HttpResponseNotAllowed(['GET', 'POST'])

    denied = _require_admin(request)
    if denied:
        return denied

    configured_environment = getattr(settings, 'ENVIRONMENT', '')
    is_local_development_admin = (
        configured_environment == 'local'
        and request.user.username == 'admin'
    )
    configured_super_dev_email = (SystemSettings.get_settings().super_dev_email or '').strip().lower()
    user_email = (request.user.email or '').strip().lower()
    is_super_dev = is_local_development_admin or bool(
        configured_super_dev_email and user_email and user_email == configured_super_dev_email
    )
    show_technical_identifiers = (
        is_super_dev
        and request.session.get('fact_finder_content_show_technical_identifiers') is True
    )
    if request.method == 'POST':
        if not is_super_dev:
            return HttpResponseNotAllowed(['GET'])
        request.session['fact_finder_content_show_technical_identifiers'] = (
            request.POST.get('show_technical_identifiers') == '1'
        )
        preserved = {
            name: request.POST.get(name)
            for name in ('system_type', 'retirement_type', 'plan_year', 'section', 'row_block_id')
            if request.POST.get(name)
        }
        target = reverse('fact_finder_content:content_list')
        if preserved:
            target = f'{target}?{urlencode(preserved)}'
        return redirect(target)

    plan_year = int(request.GET.get('plan_year', _default_plan_year()))
    system_type = _clean_system_type(request.GET.get('system_type', ''))
    retirement_type = _clean_retirement_type(request.GET.get('retirement_type', ''))
    # Phase 2C-2: which section/row (if any) to re-expand and scroll to on load —
    # e.g. when returning here from content_block_detail after an edit. Both are
    # validated below against the actual rendered rows for the CURRENT scenario,
    # not trusted blindly; an unrecognized or no-longer-present combination is
    # silently ignored (renders the normal page, no error), per the requirement
    # that a record missing from the current scenario must fail safely.
    requested_section = request.GET.get('section', '')
    requested_row_key = request.GET.get('row', '')
    requested_row_block_id = request.GET.get('row_block_id', '')
    scroll_to_dom_id = ''

    governed_keys = list(pdf_structure_map.flatten_governed_keys())
    unwired_keys = list(pdf_structure_map.all_unwired_keys())
    blocks_by_key = {
        block.key: block
        for block in ContentBlock.objects.filter(key__in=governed_keys + unwired_keys, is_active=True)
    }
    if requested_row_block_id:
        try:
            requested_block_id = int(requested_row_block_id)
        except ValueError:
            requested_block_id = None
        if requested_block_id is not None:
            requested_row_key = next(
                (key for key, block in blocks_by_key.items() if block.id == requested_block_id),
                '',
            )
    elif requested_row_key:
        matching_block = blocks_by_key.get(requested_row_key)
        if matching_block is not None:
            requested_row_block_id = str(matching_block.id)

    def _block_status(key):
        block = blocks_by_key.get(key)
        if block is None:
            return {'block': None, 'published': None, 'draft': None}
        return {
            'block': block,
            'published': block.published_version_for(plan_year),
            'draft': block.versions.filter(
                plan_year=plan_year,
                status=ContentBlockVersion.STATUS_DRAFT,
            ).order_by('-created_at').first(),
        }

    sections = []
    for report_section in pdf_structure_map.PDF_STRUCTURE_MAP:
        rows = []
        for row in _section_display_rows(report_section, system_type, retirement_type):
            if row['kind'] == 'governed':
                status = _block_status(row['entry'].key)
                if status['block'] is not None:
                    status['edit_url'] = _edit_url_for(
                        status['block'].id, system_type, retirement_type, plan_year,
                        group_key=report_section.group_key, row_block_id=status['block'].id,
                    )
                else:
                    status['edit_url'] = None
                if (
                    requested_section == report_section.group_key
                    and requested_row_key == row['entry'].key
                ):
                    scroll_to_dom_id = row['dom_id']
                rows.append({**row, **status})
            else:
                rows.append(row)

        unwired_rows = []
        for key in report_section.unwired_keys:
            status = _block_status(key)
            if status['block'] is not None:
                status['edit_url'] = _edit_url_for(status['block'].id, system_type, retirement_type, plan_year)
            else:
                status['edit_url'] = None
            unwired_rows.append({'key': key, **status})

        sections.append({
            'section': report_section,
            'rows': rows,
            'unwired_rows': unwired_rows,
        })

    return render(request, 'fact_finder_content/pdf_order_preview.html', {
        'sections': sections,
        'ungoverned_sections': pdf_structure_map.UNGOVERNED_SECTIONS,
        'plan_year': plan_year,
        'system_type': system_type,
        'retirement_type': retirement_type or '',
        'system_types': pdf_structure_map.SYSTEM_TYPES,
        'retirement_types': pdf_structure_map.RETIREMENT_TYPES,
        'scroll_to_dom_id': scroll_to_dom_id,
        'requested_section': requested_section,
        'requested_row_block_id': requested_row_block_id,
        'is_super_dev': is_super_dev,
        'show_technical_identifiers': show_technical_identifiers,
    })


@login_required
def content_block_detail(request, block_id):
    denied = _require_admin(request)
    if denied:
        return denied

    block = get_object_or_404(ContentBlock, pk=block_id)
    # Phase 2C-2: validated 'next' (see _safe_next_url) — where to send the admin
    # after this action/when they click "Back to list". Carried across every POST
    # redirect below so it survives the whole create-draft/submit/publish/rule
    # workflow, not just the initial page load.
    next_url = _safe_next_url(request)
    try:
        editing_year = forms.IntegerField(min_value=1, max_value=9999).clean(
            request.GET.get('plan_year', _default_plan_year())
        )
    except ValidationError:
        return render(request, 'fact_finder_content/content_block_detail.html', {
            'content_block': block,
            'invalid_year': True,
            'back_to_list_url': next_url or reverse('fact_finder_content:content_list'),
        }, status=400)
    draft_form = None

    def _redirect_to_self():
        target = reverse('fact_finder_content:content_block_detail', args=[block.id])
        params = {'plan_year': editing_year}
        if next_url:
            params['next'] = next_url
        return redirect(f"{target}?{urlencode(params)}")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_and_publish':
            draft_form = WordingDraftForm(request.POST)
            if draft_form.is_valid():
                data = draft_form.cleaned_data
                plan_year = data['plan_year']
                try:
                    with transaction.atomic():
                        ContentBlock.objects.select_for_update().get(pk=block.pk)
                        source_id = data['source_version_id'] or data['version_id']
                        source = None
                        if source_id:
                            source = block.versions.select_for_update().filter(pk=source_id).first()
                            if source is None or source.plan_year != plan_year:
                                draft_form.add_error(
                                    None,
                                    'The source wording must belong to this content and plan year. '
                                    'Cross-year copying is not available here.',
                                )
                        elif block.versions.filter(plan_year=plan_year).exists():
                            draft_form.add_error(
                                None,
                                'Load a source version for this plan year before publishing.',
                            )

                        if not draft_form.errors:
                            version = ContentBlockVersion(
                                block=block,
                                plan_year=plan_year,
                                merge_field_policy=deepcopy(source.merge_field_policy) if source else None,
                                created_by=request.user,
                            )
                            version.body_html = sanitize_body_html(data['body_html'])
                            if not unescape(strip_tags(version.body_html)).strip():
                                draft_form.add_error(
                                    'body_html',
                                    'Enter report wording before publishing. No changes were saved.',
                                )
                            else:
                                version.full_clean()
                                version.save()
                                version.publish(by_user=request.user, allow_draft=True)
                except ValidationError as exc:
                    draft_form.add_error(
                        None,
                        _wording_workflow_error('publish', exc),
                    )
                except DatabaseError:
                    draft_form.add_error(
                        None,
                        'Save & Publish could not be completed because of a database error. '
                        'No changes were saved. Please try again or contact your technical administrator.',
                    )

                if not draft_form.errors:
                    editing_year = plan_year
                    messages.success(
                        request,
                        f'Published for plan year {editing_year}. '
                        'The previous version remains in version history.',
                    )
                    return _redirect_to_self()

        if action == 'create_draft':
            draft_form = WordingDraftForm(request.POST)
            if draft_form.is_valid():
                data = draft_form.cleaned_data
                plan_year = data['plan_year']
                with transaction.atomic():
                    ContentBlock.objects.select_for_update().get(pk=block.pk)
                    version = None
                    source = None
                    version_id = data['version_id']
                    source_id = data['source_version_id']
                    if version_id:
                        version = block.versions.select_for_update().filter(pk=version_id).first()
                        if version is None or version.status != ContentBlockVersion.STATUS_DRAFT:
                            draft_form.add_error(None, 'Only an existing draft for this content can be edited. Reload the page.')
                        elif version.plan_year != plan_year:
                            draft_form.add_error('plan_year', 'The draft belongs to a different plan year. Load it again before saving.')
                    if source_id:
                        source = block.versions.filter(pk=source_id).first()
                        if source is None or source.plan_year != plan_year:
                            draft_form.add_error(None, 'The source wording must belong to this content and plan year. Cross-year copying is not available here.')
                        elif version_id and source_id != version_id:
                            draft_form.add_error(None, 'The selected draft and source wording do not match. Load the draft again.')
                    elif not version_id and block.versions.filter(plan_year=plan_year).exists():
                        draft_form.add_error(None, 'Load a source version for this plan year before saving a new draft.')
                    if not draft_form.errors:
                        editing_year = plan_year
                        if version is None:
                            version = ContentBlockVersion(
                                block=block,
                                plan_year=editing_year,
                                merge_field_policy=deepcopy(source.merge_field_policy) if source else None,
                                created_by=request.user,
                            )
                        version.body_html = sanitize_body_html(data['body_html'])
                        if not unescape(strip_tags(version.body_html)).strip():
                            draft_form.add_error('body_html', 'Enter report wording before saving. No changes were saved.')
                        else:
                            try:
                                version.full_clean()
                            except ValidationError:
                                draft_form.add_error(
                                    'body_html',
                                    'This wording no longer matches its configured report fields. Restore the required fields or ask your technical administrator to check the setup. No changes were saved.',
                                )
                        if not draft_form.errors:
                            version.save()
                if not draft_form.errors:
                    missing = version.missing_placeholders()
                    if missing:
                        messages.warning(
                            request,
                            'Draft saved, but missing required placeholder(s). Insert the required report fields before sending it for review.',
                        )
                    else:
                        messages.success(request, f'Draft saved for plan year {editing_year}.')
                    return _redirect_to_self()

        if action == 'submit_for_review':
            version = get_object_or_404(ContentBlockVersion, pk=request.POST.get('version_id'), block=block)
            try:
                version.submit_for_review()
            except ValidationError as exc:
                messages.error(request, _wording_workflow_error('submit for review', exc))
            else:
                messages.success(request, 'Submitted for review.')
            return _redirect_to_self()

        if action == 'publish':
            version = get_object_or_404(ContentBlockVersion, pk=request.POST.get('version_id'), block=block)
            try:
                version.publish(by_user=request.user)
            except ValidationError as exc:
                messages.error(request, _wording_workflow_error('publish', exc))
            else:
                messages.success(request, f'Published for plan year {version.plan_year}.')
            return _redirect_to_self()

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
            return _redirect_to_self()

        if action == 'remove_display_rule':
            index = int(request.POST.get('rule_index', -1))
            current_rules = (block.display_condition or {}).get('rules', [])
            if 0 <= index < len(current_rules):
                current_rules.pop(index)
                block.display_condition = {'rules': current_rules}
                block.save()
                messages.success(request, 'Display rule removed.')
            return _redirect_to_self()

    versions = list(block.versions.all())

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

    # Never source wording or policy from a different year implicitly.
    current_version = (
        block.published_version_for(editing_year)
        or block.versions.filter(plan_year=editing_year).order_by('-id').first()
    )
    current_body_html = current_version.body_html if current_version else ''
    if draft_form is None:
        draft_form = WordingDraftForm(initial={
            'plan_year': editing_year,
            'version_id': current_version.pk if current_version and current_version.status == ContentBlockVersion.STATUS_DRAFT else '',
            'source_version_id': current_version.pk if current_version else '',
            'body_html': current_body_html,
        })

    return render(request, 'fact_finder_content/content_block_detail.html', {
        # NOTE: deliberately NOT named 'block' — Django's {% block %} tag pushes a
        # BlockContext entry into context['block'] to support {{ block.super }}, which
        # silently shadows any user context variable named 'block' inside {% block %}...
        # {% endblock %} sections. Use 'content_block' everywhere in the template instead.
        'content_block': block,
        'versions': versions,
        'draft_form': draft_form,
        'is_wired': is_wired(block.key),
        'display_rules': display_rules,
        'presentable_rules': presentable_rules,
        'field_options': field_options,
        'field_value_options_json': json.dumps(field_value_options),
        'default_plan_year': editing_year,
        'golden_master_results': golden_master_results,
        'golden_master_match_count': golden_master_match_count,
        'golden_master_total_count': len(golden_master_results),
        'back_to_list_url': next_url or reverse('fact_finder_content:content_list'),
    })


def _wording_workflow_error(action, error):
    errors = getattr(error, 'message_dict', {})
    if 'status' in errors:
        return f'Cannot {action}: {errors["status"][0]}'
    if any('placeholder' in message.lower() for message in error.messages):
        return f'Cannot {action}: Missing required placeholder. Restore the required report fields and try again.'
    return (
        f'Cannot {action}: the wording does not match its configured report fields. '
        'Load the version, check the required fields, or ask your technical administrator for help.'
    )
