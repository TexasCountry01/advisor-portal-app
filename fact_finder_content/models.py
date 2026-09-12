"""
Fact Finder Content models — Option A from
docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md ("Concrete UI design:
the verbiage/content panel in advisor-portal").

Purpose: centrally govern the yearly-changing verbiage currently hardcoded in
benefits-software's report_pdf.blade.php, with a draft -> review -> publish
workflow, plan-year scoping (so historical PDFs stay reproducible), and full
version history (no destructive overwrites).

This is step 1 of Option A: models only. No views/admin UI/API wiring yet —
those are later, separately-tested increments.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from .sanitize import sanitize_body_html


class ContentBlockGroup(models.Model):
    """Mirrors the PDF's own sections, so the panel's grouping matches the
    document structure (Cover, Pension, SBP, SRS/SS, FEGLI, FEHB, FLTCIP, TSP,
    Checklist — see the analysis doc's section table)."""

    key = models.SlugField(unique=True)
    label = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'label']
        verbose_name = 'Content Block Group'
        verbose_name_plural = 'Content Block Groups'

    def __str__(self):
        return self.label


class ContentBlock(models.Model):
    """One stable, addressable piece of verbiage (e.g. 'fegli.basic_description').

    The block itself never holds text — only identity/metadata. The actual
    wording lives in versioned `ContentBlockVersion` rows below, so plan-year
    history and draft/review state are tracked per edit, not per block.
    """

    key = models.SlugField(
        unique=True,
        help_text="Stable identifier, e.g. 'fegli.basic_description'. Never reused for a different meaning once published."
    )
    group = models.ForeignKey(
        ContentBlockGroup,
        on_delete=models.PROTECT,
        related_name='blocks',
    )
    label = models.CharField(
        max_length=200,
        help_text='Human-readable name shown in the content list UI.'
    )
    help_text_internal = models.TextField(
        blank=True,
        help_text="Internal note for content editors, e.g. \"Appears under Federal Pension when system is FERS\"."
    )
    required_placeholders = models.JSONField(
        default=list,
        blank=True,
        help_text='Merge-field tokens this block must contain, e.g. ["mra_years", "mra_months"]. Validated on publish.'
    )
    display_condition = models.JSONField(
        null=True,
        blank=True,
        help_text='Structured rule (field/operator/value rows) evaluated against the Fact Finder Data Contract. Null = always shown.'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive blocks are hidden from the content list but keep their history.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group__display_order', 'label']
        verbose_name = 'Content Block'
        verbose_name_plural = 'Content Blocks'

    def __str__(self):
        return f'{self.group.label} — {self.label}'

    @property
    def published_versions(self):
        """All currently-published versions of this block, across plan years."""
        return self.versions.filter(status=ContentBlockVersion.STATUS_PUBLISHED)

    def published_version_for(self, plan_year):
        """The single published version for a given plan year, if any."""
        return self.versions.filter(
            status=ContentBlockVersion.STATUS_PUBLISHED,
            plan_year=plan_year,
        ).first()


class ContentBlockVersion(models.Model):
    """One edit of a block, scoped to a plan year, moving through
    draft -> in_review -> published -> superseded.

    Only one (block, plan_year) pair may be 'published' at a time. This is
    enforced in `publish()` below, not with a DB constraint, so old versions
    can stay as 'superseded' rows for historical PDF reproducibility (per the
    analysis doc: regenerating a prior year's PDF needs that year's wording,
    not whatever is live today).
    """

    STATUS_DRAFT = 'draft'
    STATUS_IN_REVIEW = 'in_review'
    STATUS_PUBLISHED = 'published'
    STATUS_SUPERSEDED = 'superseded'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_IN_REVIEW, 'In Review'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_SUPERSEDED, 'Superseded'),
    ]

    block = models.ForeignKey(
        ContentBlock,
        on_delete=models.CASCADE,
        related_name='versions',
    )
    plan_year = models.PositiveIntegerField()
    body_html = models.TextField(
        help_text='Sanitized HTML (restricted tag set only — see Security notes in the analysis doc).'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_versions_created',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_versions_reviewed',
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-plan_year', '-created_at']
        verbose_name = 'Content Block Version'
        verbose_name_plural = 'Content Block Versions'
        indexes = [
            models.Index(fields=['block', 'plan_year', 'status']),
        ]

    def __str__(self):
        return f'{self.block.key} ({self.plan_year}) — {self.get_status_display()}'

    def save(self, *args, **kwargs):
        """Sanitize body_html at the trust boundary (save time), not just on
        render — see fact_finder_content/sanitize.py. Applies on every save
        (create AND update), regardless of which code path (view, admin,
        shell, tests) is writing this row."""
        self.body_html = sanitize_body_html(self.body_html)
        super().save(*args, **kwargs)

    def missing_placeholders(self):
        """Return the subset of block.required_placeholders NOT present in
        body_html as a `[[token]]` merge field. Empty list = all present."""
        return [
            token for token in self.block.required_placeholders
            if f'[[{token}]]' not in self.body_html
        ]

    def publish(self, by_user=None):
        """Publish this version, superseding any other currently-published
        version of the same block for the same plan year. Does not touch
        versions for other plan years (each plan year's published wording is
        independent, per the plan-year-scoping requirement)."""
        ContentBlockVersion.objects.filter(
            block=self.block,
            plan_year=self.plan_year,
            status=self.STATUS_PUBLISHED,
        ).exclude(pk=self.pk).update(status=self.STATUS_SUPERSEDED)

        self.status = self.STATUS_PUBLISHED
        self.published_at = timezone.now()
        if by_user is not None:
            self.reviewed_by = by_user
        self.save()

