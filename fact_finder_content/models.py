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
import django
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import connections, models, transaction
from django.db.models import F
from django.db.models import Q
from django.utils import timezone

from .sanitize import sanitize_body_html
from .rules import validate_rules
from .merge_field_policy import validate_merge_field_template


_CHECK_CONSTRAINT_ARGUMENT = 'condition' if django.VERSION >= (6, 0) else 'check'


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
    merge_field_policy = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            'Versioned runtime merge-field policy. Null means legacy/unvalidated; '
            'no policy is inferred for existing content.'
        ),
    )
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

    def clean(self):
        super().clean()
        if self.merge_field_policy is None or self.block_id is None:
            return
        try:
            validate_merge_field_template(
                self.body_html,
                self.merge_field_policy,
                self.block.required_placeholders,
            )
        except ValidationError as exc:
            raise ValidationError({'merge_field_policy': exc.messages}) from exc

    def missing_placeholders(self):
        """Return the subset of block.required_placeholders NOT present in
        body_html as a `[[token]]` merge field. Empty list = all present."""
        return [
            token for token in self.block.required_placeholders
            if f'[[{token}]]' not in self.body_html
        ]

    def validate_publishable(self):
        """Validate the saved body, any merge policy, and legacy required tokens."""
        self.full_clean()
        missing = self.missing_placeholders()
        if missing:
            raise ValidationError({
                'body_html': (
                    'Missing required placeholder(s): ' + ', '.join(missing) + '.'
                ),
            })

    def submit_for_review(self):
        """Move a valid draft into review without changing its published predecessor."""
        if self.pk is None:
            raise ValidationError({'status': 'Only saved drafts can be submitted for review.'})

        database = self._state.db
        with transaction.atomic(using=database):
            version = type(self).objects.using(database).select_for_update().get(pk=self.pk)
            if version.status != self.STATUS_DRAFT:
                raise ValidationError({'status': 'Only draft versions can be submitted for review.'})
            version.validate_publishable()
            version.status = self.STATUS_IN_REVIEW
            version.save()

        self.status = version.status
        self.updated_at = version.updated_at

    def publish(self, by_user=None, allow_draft=False):
        """Atomically publish an in-review version or an explicitly authorized draft."""
        if self.pk is None:
            raise ValidationError({'status': 'Only saved versions can be published.'})

        database = self._state.db
        with transaction.atomic(using=database):
            block_query = ContentBlock.objects.using(database).filter(pk=self.block_id)
            connection = connections[database]
            if connection.features.has_select_for_update:
                block_query.select_for_update().get()
            else:
                # SQLite has no SELECT FOR UPDATE. Acquire its serialized write
                # lock before examining or superseding published versions.
                block_query.update(is_active=F('is_active'))

            version = (
                type(self).objects.using(database)
                .select_for_update()
                .select_related('block')
                .get(pk=self.pk)
            )
            allowed_statuses = {self.STATUS_IN_REVIEW}
            if allow_draft:
                allowed_statuses.add(self.STATUS_DRAFT)
            if version.status not in allowed_statuses:
                raise ValidationError({
                    'status': (
                        'Only draft or in-review versions can be published.'
                        if allow_draft
                        else 'Only versions in review can be published.'
                    ),
                })

            # Validate the persisted candidate while holding the block lock and
            # before touching its currently published predecessor.
            version.validate_publishable()
            was_in_review = version.status == self.STATUS_IN_REVIEW
            type(self).objects.using(database).filter(
                block_id=version.block_id,
                plan_year=version.plan_year,
                status=self.STATUS_PUBLISHED,
            ).exclude(pk=version.pk).update(
                status=self.STATUS_SUPERSEDED,
                updated_at=timezone.now(),
            )

            version.status = self.STATUS_PUBLISHED
            version.published_at = timezone.now()
            if by_user is not None and was_in_review:
                version.reviewed_by = by_user
            version.save()

        self.status = version.status
        self.published_at = version.published_at
        self.reviewed_by = version.reviewed_by
        self.updated_at = version.updated_at


class ContentSlot(models.Model):
    """Stable logical position for governed or calculated PDF content."""

    REQUIREMENT_REQUIRED = 'required'
    REQUIREMENT_OPTIONAL = 'optional'
    REQUIREMENT_CALCULATION_DRIVEN = 'calculation_driven'
    REQUIREMENT_CHOICES = [
        (REQUIREMENT_REQUIRED, 'Required'),
        (REQUIREMENT_OPTIONAL, 'Optional'),
        (REQUIREMENT_CALCULATION_DRIVEN, 'Calculation-driven'),
    ]

    key = models.CharField(
        max_length=100,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9]+(?:[._-][a-z0-9]+)*$',
                message='Use lowercase letters, numbers, dots, underscores, or hyphens.',
            ),
        ],
        help_text='Stable logical PDF position, e.g. "pension.federal_pension_intro".',
    )
    label = models.CharField(max_length=200)
    group = models.ForeignKey(
        ContentBlockGroup,
        on_delete=models.PROTECT,
        related_name='slots',
    )
    requirement = models.CharField(
        max_length=32,
        choices=REQUIREMENT_CHOICES,
        default=REQUIREMENT_REQUIRED,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group__display_order', 'label']
        constraints = [
            models.CheckConstraint(
                **{
                    _CHECK_CONSTRAINT_ARGUMENT: Q(requirement__in=[
                        'required',
                        'optional',
                        'calculation_driven',
                    ]),
                    'name': 'ff_slot_valid_requirement',
                }
            ),
        ]
        verbose_name = 'PDF Content Slot'
        verbose_name_plural = 'PDF Content Slots'

    def __str__(self):
        return f'{self.group.label} — {self.label}'


class ContentSlotVersion(models.Model):
    """Plan-year-scoped, versioned variant and applicability configuration."""

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

    slot = models.ForeignKey(
        ContentSlot,
        on_delete=models.PROTECT,
        related_name='versions',
    )
    plan_year = models.PositiveIntegerField()
    configuration = models.JSONField(
        default=dict,
        help_text='Structured variants and applicability clauses; content HTML stays in ContentBlockVersion.',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_slot_versions_created',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_slot_versions_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-plan_year', '-created_at']
        constraints = [
            models.CheckConstraint(
                **{
                    _CHECK_CONSTRAINT_ARGUMENT: Q(status__in=[
                        'draft',
                        'in_review',
                        'published',
                        'superseded',
                    ]),
                    'name': 'ff_slot_version_valid_status',
                }
            ),
            models.UniqueConstraint(
                fields=['slot', 'plan_year'],
                condition=Q(status='published'),
                name='ff_slot_one_published_per_year',
            ),
        ]
        indexes = [
            models.Index(fields=['slot', 'plan_year', 'status']),
        ]
        verbose_name = 'PDF Content Slot Configuration'
        verbose_name_plural = 'PDF Content Slot Configurations'

    def __str__(self):
        return f'{self.slot.key} ({self.plan_year}) — {self.get_status_display()}'

    def clean(self):
        super().clean()
        if self.slot_id is None:
            raise ValidationError({'slot': 'A content slot is required.'})
        configuration = self.configuration

        if not isinstance(configuration, dict) or set(configuration) != {'variants'}:
            raise ValidationError({
                'configuration': 'Configuration must be an object containing only a "variants" list.',
            })

        variants = configuration['variants']
        if not isinstance(variants, list):
            raise ValidationError({'configuration': '"variants" must be a list.'})
        if self.slot.requirement == ContentSlot.REQUIREMENT_CALCULATION_DRIVEN:
            if variants:
                raise ValidationError({
                    'configuration': 'Calculation-driven slots cannot define content or suppression variants.',
                })
            return
        if not variants:
            raise ValidationError({
                'configuration': 'Required and optional slots must define at least one variant.',
            })

        errors = []
        seen_variant_ids = set()
        referenced_keys = set()
        for index, variant in enumerate(variants):
            prefix = f'Variant {index + 1}: '
            if not isinstance(variant, dict):
                errors.append(prefix + 'each variant must be an object.')
                continue

            action = variant.get('action')
            expected_fields = {'variant_id', 'action', 'when'}
            if action == 'content':
                expected_fields.add('content_key')
            if set(variant) != expected_fields:
                errors.append(
                    prefix + 'unsupported or missing fields; expressions and arbitrary properties are not allowed.'
                )
                continue

            variant_id = variant.get('variant_id')
            if (
                not isinstance(variant_id, str)
                or not variant_id
                or len(variant_id) > 64
                or not all(char in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for char in variant_id)
                or variant_id[0] not in 'abcdefghijklmnopqrstuvwxyz0123456789'
            ):
                errors.append(prefix + 'variant_id must be a stable lowercase identifier.')
                continue
            if variant_id in seen_variant_ids:
                errors.append(prefix + f'duplicate variant_id "{variant_id}".')
                continue
            seen_variant_ids.add(variant_id)

            if action not in ('content', 'suppress'):
                errors.append(prefix + 'action must be "content" or "suppress".')
                continue
            if action == 'suppress' and self.slot.requirement == ContentSlot.REQUIREMENT_REQUIRED:
                errors.append(prefix + 'required slots cannot define suppression variants.')
                continue

            if action == 'content':
                content_key = variant.get('content_key')
                if not isinstance(content_key, str) or not content_key:
                    errors.append(prefix + 'content variants require a ContentBlock key.')
                else:
                    referenced_keys.add(content_key)

            when = variant.get('when')
            if (
                not isinstance(when, dict)
                or set(when) != {'any'}
                or not isinstance(when['any'], list)
                or not when['any']
            ):
                errors.append(prefix + '"when" must contain a non-empty "any" list.')
                continue

            for clause_index, clause in enumerate(when['any']):
                if not isinstance(clause, dict) or set(clause) != {'all'} or not isinstance(clause['all'], list):
                    errors.append(
                        prefix + f'condition alternative {clause_index + 1} must contain an "all" rule list.'
                    )
                    break
                rules = clause['all']
                if any(
                    not isinstance(rule, dict) or set(rule) != {'field', 'operator', 'value'}
                    for rule in rules
                ):
                    errors.append(
                        prefix + f'condition alternative {clause_index + 1} contains an unsupported rule.'
                    )
                    break
                rule_errors = validate_rules(rules)
                if rule_errors:
                    errors.extend(prefix + error for error in rule_errors)
                    break

        if referenced_keys:
            existing_keys = set(
                ContentBlock.objects.filter(key__in=referenced_keys).values_list('key', flat=True)
            )
            unknown_keys = referenced_keys - existing_keys
            if unknown_keys:
                errors.append('Unknown ContentBlock key(s): ' + ', '.join(sorted(unknown_keys)) + '.')

        if errors:
            raise ValidationError({'configuration': errors})

    def _content_keys(self):
        return {
            variant['content_key']
            for variant in self.configuration.get('variants', [])
            if isinstance(variant, dict)
            and variant.get('action') == 'content'
            and isinstance(variant.get('content_key'), str)
        }

    def validate_publishable(self):
        """Validate structure and require every content variant published for this year."""
        self.full_clean()
        content_keys = self._content_keys()
        if not content_keys:
            return

        published_keys = set(
            ContentBlockVersion.objects.filter(
                block__key__in=content_keys,
                plan_year=self.plan_year,
                status=ContentBlockVersion.STATUS_PUBLISHED,
            ).values_list('block__key', flat=True)
        )
        missing_keys = sorted(content_keys - published_keys)
        if missing_keys:
            raise ValidationError({
                'configuration': (
                    f'No published ContentBlockVersion for plan year {self.plan_year}: '
                    + ', '.join(missing_keys) + '.'
                ),
            })

    def submit_for_review(self):
        if self.status != self.STATUS_DRAFT:
            raise ValidationError({'status': 'Only draft configurations can be submitted for review.'})
        self.full_clean()
        self.status = self.STATUS_IN_REVIEW
        self.save()

    def publish(self, by_user=None):
        """Atomically publish this configuration and supersede this slot/year's prior one."""
        if self.status != self.STATUS_IN_REVIEW:
            raise ValidationError({'status': 'Only configurations in review can be published.'})
        with transaction.atomic():
            ContentSlot.objects.select_for_update().get(pk=self.slot_id)
            self.validate_publishable()
            ContentSlotVersion.objects.filter(
                slot_id=self.slot_id,
                plan_year=self.plan_year,
                status=self.STATUS_PUBLISHED,
            ).exclude(pk=self.pk).update(
                status=self.STATUS_SUPERSEDED,
                updated_at=timezone.now(),
            )

            now = timezone.now()
            self.status = self.STATUS_PUBLISHED
            self.published_at = now
            if by_user is not None:
                self.reviewed_by = by_user
                self.reviewed_at = now
            self.save()
