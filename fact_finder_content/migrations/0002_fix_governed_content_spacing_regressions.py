"""
Data migration: corrects 6 governed-content blocks whose stored body_html
regressed PDF geometry relative to PROD's original hardcoded Blade fallback,
per the experimental findings in benefits-software/PDF_REGRESSION_FINDINGS_2026-09-27.md
(Addendum, section 12 — "Four Residual Governed-Content Defects — Experimentally
Proven").

Every root cause below was demonstrated (not inferred) by rendering isolated
HTML fragments through the real MYPDF/TCPDF pipeline and measuring exact word
coordinates with pdfplumber. See that document for the full methodology,
ruled-out hypotheses, and exact coordinate evidence.

Design, per explicit instruction:
  - Creates and PUBLISHES NEW ContentBlockVersion rows via the model's normal
    draft -> publish() lifecycle. Never mutates a historical published row in
    place (old versions remain in history as 'superseded', same as every
    other content correction in this project).
  - Content passes through ContentBlockVersion.save() -> sanitize_body_html()
    like any other save -- no bypass.
  - No changes to sanitize.py's allow-lists, FactFinderGovernedContentResolver,
    Blade, or global CSS -- every correction below is expressible using tags/
    entities/CSS properties already on the existing allow-list.
  - Corrections are computed from each block's CURRENT published body_html
    (not a hardcoded retyped snapshot), via small, targeted, uniquely-scoped
    string substitutions -- this avoids transcription errors across very long
    stored HTML strings and is naturally a no-op if a key's content doesn't
    contain the expected (buggy) substring.

Reverse migration re-publishes whichever ContentBlockVersion was published
immediately before this migration ran, for each affected (block, plan_year)
pair -- using the same .publish() lifecycle (supersedes the version this
migration created, does not delete it).

UPDATE (page 27 follow-on investigation): checklist.topics_after_srs's PROD/
original fallback is NOT internally consistent with its 2 sibling Checklist
blocks -- confirmed against origin/master (see PDF_REGRESSION_FINDINGS_2026-09-27.md,
Addendum section 14). The generic top-level &nbsp;&nbsp; correction below is
still correct for 4 of its 5 headings, but over-corrects the FEHB heading
(which had zero leading whitespace in PROD, unlike the other 4), and the
block also has one nested <li> (TSP's 3rd question) that PROD never styled
at all. _checklist_topics_after_srs_fix() layers 2 narrow, explicit
exceptions on top of the generic fix for this one block only -- verified to
reproduce PROD's rendered geometry exactly (256/256 words, all 22 lines,
identical block height).

UPDATE (idempotency hardening, 2026-10-03): a read-only database audit found
that repeated manual apply/revert/reapply cycles during local verification
(outside Django's normal single-application `migrate` usage) exposed that
_high3_pay_included_table_fix() and _checklist_topic_list_fix() were blind
prepends -- safe for exactly one application, but NOT safe if ever invoked
again against their own output (3->5->7 nbsp; 0->2->4 nbsp). Both are now
implemented as exact source-form-recognizing regex substitutions that
recognize the already-corrected target form and leave it unchanged, matching
the idempotency guard already used by _checklist_topics_after_srs_fix() (see
PDF_REGRESSION_FINDINGS_2026-09-27.md, Addendum section 15, for the full
audit and hardening record). This changes no block's CORRECTED content --
only how safely each transform tolerates re-application.
"""
import re

from django.db import migrations

PLAN_YEAR = 2026

# Matches exactly 3 non-breaking spaces followed by a literal space, as long
# as they are not themselves preceded by 2 more non-breaking spaces (i.e. not
# already part of an already-corrected 5-&nbsp; run). This makes the
# transform idempotent: the 3-&nbsp; original matches and becomes 5; the
# already-corrected 5-&nbsp; form has no substring satisfying the pattern
# (its only 3-in-a-row + space candidate is immediately preceded by 2 more
# &nbsp;, which the lookbehind excludes), so re-running this against already-
# corrected content is a true no-op -- it can never produce 7.
_HIGH3_NBSP_RE = re.compile(r'(?<!&nbsp;&nbsp;)&nbsp;&nbsp;&nbsp; ')


def _high3_pay_included_table_fix(html):
    # Section 12.1: CMS serialization dropped the original fallback's
    # newline+indentation whitespace before each "&nbsp;&nbsp;&nbsp; <item>"
    # line, which TCPDF rendered as extra significant leading space. Proven
    # durable replacement: 3 -> 5 non-breaking spaces (exact PROD coordinate
    # reproduction verified via pdfplumber; see Addendum section 12.1).
    return _HIGH3_NBSP_RE.sub('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ', html)


def _fegli_coverage_available_fix(html):
    # Section 12.2: pure content gap -- the final <td> is missing the
    # trailing <br> that PROD's original hardcoded fallback had, which
    # shortens the table's rendered height by exactly one line.
    old_tail = 'multiples selected (1-5)</td></tr></tbody></table>'
    new_tail = 'multiples selected (1-5)<br></td></tr></tbody></table>'
    return html.replace(old_tail, new_tail)


def _fltcip_coverage_available_intro_fix(html):
    # Section 12.3: pure content gap -- the "Coverage available" heading
    # span is missing the line-height: 11px declaration PROD's original
    # fallback had (already-allowed CSS property, just absent here).
    old_style = 'style="font-size: 11px; font-weight: bold;">Coverage available</span>'
    new_style = 'style="font-size: 11px; line-height: 11px; font-weight: bold;">Coverage available</span>'
    return html.replace(old_style, new_style)


# Matches the top-level heading marker only when NOT already followed by the
# 2-&nbsp; prefix this fix inserts -- makes the transform idempotent (0->2
# matches and is corrected; an already-corrected 2-&nbsp; heading has the
# prefix immediately after the marker, so the negative lookahead excludes it
# and re-running this against already-corrected content is a true no-op --
# it can never produce 4). Nested sub-item <li> style attributes never
# contain 'color: #285FBF;' at all, so they are structurally untouched
# either way.
_CHECKLIST_MARKER_RE = re.compile(r'color: #285FBF;">(?!&nbsp;&nbsp;)')


def _checklist_topic_list_fix(html):
    # Section 12.4: CMS serialization dropped the original leading
    # whitespace inside each top-level <li>'s heading text, shifting the
    # custom list-style-type:img|svg|... bullet/list heading text
    # horizontally. Proven durable replacement: prepend &nbsp;&nbsp; to each
    # top-level <li>'s heading text (exact PROD x0 coordinate reproduced;
    # see Addendum section 12.4). The 'color: #285FBF;">' substring is
    # unique to top-level <li> style attributes in these 3 blocks (nested
    # sub-item <li>s use a different style with no #285FBF), so this
    # targeted replace cannot affect sub-item text.
    return _CHECKLIST_MARKER_RE.sub('color: #285FBF;">&nbsp;&nbsp;', html)


def _checklist_topics_after_srs_fix(html):
    # checklist.topics_after_srs-SPECIFIC correction (Addendum section 14).
    # Starts from the same generic top-level fix used by the other 2
    # Checklist blocks, then layers exactly 2 narrow, explicit exceptions
    # that exist ONLY because PROD's own original fallback for this one
    # block is internally inconsistent (confirmed against origin/master):
    #
    # Exception 1 -- FEHB heading: PROD's original "Federal Employees
    # Health Benefits (FEHB)" heading has ZERO leading whitespace before its
    # text (unlike TSP/FEGLI/FLTCIP/General Concerns, which all have the
    # collapsed-whitespace gap the generic fix restores). Applying the
    # generic &nbsp;&nbsp; fix to FEHB over-corrects it away from its true
    # PROD position (PROD x0 56.037; the generic fix alone produces 62.153).
    # Undo the generic fix for this one heading only.
    #
    # Exception 2 -- TSP's 3rd nested question: PROD's original markup for
    # "How do withdrawal options from TSP compare to withdrawal options from
    # a private account?" is a bare <li> with NO style attribute at all --
    # every other nested <li> in every Checklist block has
    # style="font-family:Arial, sans-serif; line-height: 17px;"). The CMS
    # content has that style attribute present on this one line (added
    # during an earlier, separate content migration), which is a content
    # gap relative to PROD, not a sanitizer/whitespace artifact. Its
    # presence causes every line below it in the block to render ~1.18pt
    # too high relative to PROD (PROD's missing line-height falls back to a
    # taller effective line height for just that one line, cascading through
    # the rest of the block). Remove the style attribute from this one <li>
    # only -- every other nested checklist <li> keeps its style attribute.
    #
    # Experimentally verified: applying both exceptions on top of the
    # generic fix reproduces PROD's rendered geometry EXACTLY -- 256/256
    # words and all 22 lines pixel-identical (0 mismatches), including
    # total block height (see Addendum section 14 for the full controlled
    # experiment matrix).
    #
    # Idempotency guard: this early-return keeps the explicit, auditable
    # "fully corrected" end state check this function has always used. Note
    # that _checklist_topic_list_fix() (called below) and both exceptions
    # that follow it are now ALSO independently idempotent (see their own
    # docstrings/comments), so this guard is a redundant, belt-and-suspenders
    # short-circuit rather than the only thing preventing drift -- kept
    # as-is, unchanged, per instruction not to alter this function's
    # behavior beyond using the now-safe shared helper.
    fully_corrected = (
        'color: #285FBF;">&nbsp;&nbsp;Thrift Savings Plan (TSP)' in html
        and 'color: #285FBF;">&nbsp;&nbsp;Federal Employees Group Life Insurance (FEGLI)' in html
        and 'color: #285FBF;">&nbsp;&nbsp;Federal Long Term Care Insurance Program (FLTCIP)' in html
        and 'color: #285FBF;">&nbsp;&nbsp;General Concerns for Retirement' in html
        and 'color: #285FBF;">Federal Employees Health Benefits (FEHB)' in html
        and 'color: #285FBF;">&nbsp;&nbsp;Federal Employees Health Benefits (FEHB)' not in html
        and (
            '<li><em>How do withdrawal options from TSP compare to withdrawal '
            'options from a private account?</em></li>'
        ) in html
    )
    if fully_corrected:
        return html

    html = _checklist_topic_list_fix(html)

    html = html.replace(
        'color: #285FBF;">&nbsp;&nbsp;Federal Employees Health Benefits (FEHB)',
        'color: #285FBF;">Federal Employees Health Benefits (FEHB)',
    )

    old_li = (
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>How do withdrawal options from TSP compare to withdrawal '
        'options from a private account?</em></li>'
    )
    new_li = (
        '<li><em>How do withdrawal options from TSP compare to withdrawal '
        'options from a private account?</em></li>'
    )
    html = html.replace(old_li, new_li)

    return html


# key -> fix function
CORRECTIONS = {
    'pension.high3_pay_included_table': _high3_pay_included_table_fix,
    'fegli.coverage_available': _fegli_coverage_available_fix,
    'fltcip.coverage_available_intro': _fltcip_coverage_available_intro_fix,
    'checklist.topics_before_srs': _checklist_topic_list_fix,
    'checklist.srs_topic': _checklist_topic_list_fix,
    'checklist.topics_after_srs': _checklist_topics_after_srs_fix,
}


def apply_corrections(apps, schema_editor):
    ContentBlock = apps.get_model('fact_finder_content', 'ContentBlock')
    ContentBlockVersion = apps.get_model('fact_finder_content', 'ContentBlockVersion')
    # sanitize_body_html is plain Python (no model-state dependency), safe to
    # import directly even in a historical-models data migration.
    from fact_finder_content.sanitize import sanitize_body_html

    for key, fix_fn in CORRECTIONS.items():
        block = ContentBlock.objects.filter(key=key).first()
        if block is None:
            # Reproducible across environments that may not have every block
            # seeded yet -- skip rather than fail the whole migration.
            continue

        current = block.versions.filter(
            status='published', plan_year=PLAN_YEAR,
        ).order_by('-created_at').first()
        if current is None:
            continue

        corrected_html = sanitize_body_html(fix_fn(current.body_html))
        if corrected_html == current.body_html:
            # Nothing to do -- either already fixed, or this environment's
            # content doesn't contain the expected buggy substring.
            continue

        new_version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=PLAN_YEAR,
            body_html=corrected_html,
        )
        # Mirror ContentBlockVersion.publish()'s real logic here, since the
        # historical (apps.get_model) model class used by data migrations
        # does not carry custom methods defined on the real model.
        ContentBlockVersion.objects.filter(
            block=block, plan_year=PLAN_YEAR, status='published',
        ).exclude(pk=new_version.pk).update(status='superseded')
        new_version.status = 'published'
        new_version.save()


def revert_corrections(apps, schema_editor):
    ContentBlock = apps.get_model('fact_finder_content', 'ContentBlock')
    ContentBlockVersion = apps.get_model('fact_finder_content', 'ContentBlockVersion')

    for key in CORRECTIONS:
        block = ContentBlock.objects.filter(key=key).first()
        if block is None:
            continue

        versions = list(
            block.versions.filter(plan_year=PLAN_YEAR).order_by('-created_at')
        )
        if len(versions) < 2:
            continue

        currently_published, previous = versions[0], versions[1]
        if currently_published.status != 'published':
            continue

        ContentBlockVersion.objects.filter(pk=currently_published.pk).update(status='superseded')
        ContentBlockVersion.objects.filter(pk=previous.pk).update(status='published')


class Migration(migrations.Migration):

    dependencies = [
        ('fact_finder_content', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(apply_corrections, revert_corrections),
    ]
