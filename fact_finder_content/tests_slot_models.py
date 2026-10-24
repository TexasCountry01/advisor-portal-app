from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from fact_finder_content.models import (
    ContentBlock,
    ContentBlockGroup,
    ContentBlockVersion,
    ContentSlot,
    ContentSlotVersion,
)


class ContentSlotModelTests(TestCase):
    def setUp(self):
        self.group = ContentBlockGroup.objects.create(key='pension', label='Pension')
        self.block = ContentBlock.objects.create(
            key='pension.retirement_intro',
            group=self.group,
            label='Retirement Introduction',
        )

    def make_slot(self, requirement=ContentSlot.REQUIREMENT_REQUIRED, key='pension.intro'):
        return ContentSlot.objects.create(
            key=key,
            label='Pension Introduction',
            group=self.group,
            requirement=requirement,
        )

    def content_configuration(self, content_key=None, rules=None, variant_id='fers'):
        return {
            'variants': [{
                'variant_id': variant_id,
                'action': 'content',
                'content_key': content_key or self.block.key,
                'when': {
                    'any': [{
                        'all': rules if rules is not None else [{
                            'field': 'system.system_type',
                            'operator': 'equals',
                            'value': 'FERS',
                        }],
                    }],
                },
            }],
        }

    def make_version(self, slot, plan_year=2026, configuration=None):
        return ContentSlotVersion.objects.create(
            slot=slot,
            plan_year=plan_year,
            configuration=configuration or self.content_configuration(),
        )

    def publish_block(self, plan_year=2026):
        version = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=plan_year,
            body_html='<p>Published wording.</p>',
        )
        version.submit_for_review()
        version.publish()
        return version

    def test_creates_slot_and_configuration(self):
        slot = self.make_slot()
        version = self.make_version(slot)
        self.assertEqual(slot.key, 'pension.intro')
        self.assertEqual(slot.requirement, ContentSlot.REQUIREMENT_REQUIRED)
        self.assertEqual(version.status, ContentSlotVersion.STATUS_DRAFT)

    def test_slot_key_is_unique(self):
        self.make_slot()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_slot()

    def test_invalid_requirement_classification_is_rejected(self):
        slot = self.make_slot()
        slot.requirement = 'unrestricted'
        with self.assertRaises(ValidationError):
            slot.full_clean()

    def test_duplicate_variant_ids_are_rejected(self):
        slot = self.make_slot()
        variant = self.content_configuration()['variants'][0]
        configuration = {'variants': [variant, dict(variant)]}
        with self.assertRaises(ValidationError):
            self.make_version(slot, configuration=configuration).full_clean()

    def test_invalid_action_is_rejected(self):
        slot = self.make_slot()
        config = self.content_configuration()
        config['variants'][0]['action'] = 'execute'
        with self.assertRaises(ValidationError):
            self.make_version(slot, configuration=config).full_clean()

    def test_unknown_content_block_key_is_rejected(self):
        slot = self.make_slot()
        config = self.content_configuration(content_key='pension.does_not_exist')
        with self.assertRaises(ValidationError):
            self.make_version(slot, configuration=config).full_clean()

    def test_suppression_variant_is_valid_only_for_optional_slot(self):
        slot = self.make_slot(requirement=ContentSlot.REQUIREMENT_OPTIONAL)
        config = {
            'variants': [{
                'variant_id': 'not_applicable',
                'action': 'suppress',
                'when': {'any': [{'all': []}]},
            }],
        }
        self.make_version(slot, configuration=config).full_clean()

        required_slot = self.make_slot(key='pension.required')
        invalid = self.make_version(required_slot, configuration=config)
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_calculation_driven_slot_accepts_empty_configuration_without_block_publication(self):
        slot = self.make_slot(requirement=ContentSlot.REQUIREMENT_CALCULATION_DRIVEN)
        version = self.make_version(slot, configuration={'variants': []})
        version.full_clean()
        version.validate_publishable()

    def test_calculation_driven_slot_rejects_content_and_suppression_variants(self):
        slot = self.make_slot(requirement=ContentSlot.REQUIREMENT_CALCULATION_DRIVEN)
        content_version = self.make_version(slot)
        with self.assertRaises(ValidationError):
            content_version.full_clean()

        suppression_config = {
            'variants': [{
                'variant_id': 'not_applicable',
                'action': 'suppress',
                'when': {'any': [{'all': []}]},
            }],
        }
        suppression_version = self.make_version(slot, configuration=suppression_config)
        with self.assertRaises(ValidationError):
            suppression_version.full_clean()

    def test_optional_slot_still_accepts_content_variant(self):
        slot = self.make_slot(requirement=ContentSlot.REQUIREMENT_OPTIONAL)
        self.make_version(slot).full_clean()

    def test_invalid_condition_field_and_value_are_rejected(self):
        slot = self.make_slot()
        invalid_rules = [
            {'field': 'employee.salary', 'operator': 'equals', 'value': 'high'},
        ]
        with self.assertRaises(ValidationError):
            self.make_version(
                slot,
                configuration=self.content_configuration(rules=invalid_rules),
            ).full_clean()

    def test_invalid_operator_and_value_type_are_rejected(self):
        slot = self.make_slot()
        invalid_rules = [
            {'field': 'system.system_type', 'operator': 'contains', 'value': 'FERS'},
        ]
        with self.assertRaises(ValidationError):
            self.make_version(
                slot,
                configuration=self.content_configuration(rules=invalid_rules),
            ).full_clean()

        invalid_rules = [
            {'field': 'computed_flags.is_special_provision', 'operator': 'equals', 'value': 'true'},
        ]
        with self.assertRaises(ValidationError):
            self.make_version(
                slot,
                configuration=self.content_configuration(rules=invalid_rules),
            ).full_clean()

    def test_content_requires_published_version_for_requested_plan_year(self):
        slot = self.make_slot()
        config = self.content_configuration()
        version = self.make_version(slot, configuration=config)
        with self.assertRaises(ValidationError):
            version.validate_publishable()

        self.publish_block(2025)
        with self.assertRaises(ValidationError):
            version.validate_publishable()

    def test_draft_review_publish_and_supersession_are_transactional(self):
        slot = self.make_slot()
        self.publish_block()
        prior = self.make_version(slot)
        prior.submit_for_review()
        prior.publish()
        prior.refresh_from_db()
        self.assertEqual(prior.status, ContentSlotVersion.STATUS_PUBLISHED)

        newer = self.make_version(slot)
        newer.submit_for_review()
        newer.publish()
        prior.refresh_from_db()
        newer.refresh_from_db()
        self.assertEqual(prior.status, ContentSlotVersion.STATUS_SUPERSEDED)
        self.assertEqual(newer.status, ContentSlotVersion.STATUS_PUBLISHED)

    def test_publish_requires_review_state(self):
        slot = self.make_slot()
        self.publish_block()
        with self.assertRaises(ValidationError):
            self.make_version(slot).publish()

    def test_failed_publish_does_not_supersede_existing_configuration(self):
        slot = self.make_slot()
        self.publish_block()
        existing = self.make_version(slot)
        existing.submit_for_review()
        existing.publish()

        unpublishable = self.make_version(slot, plan_year=2027)
        unpublishable.submit_for_review()
        with self.assertRaises(ValidationError):
            unpublishable.publish()

        existing.refresh_from_db()
        self.assertEqual(existing.status, ContentSlotVersion.STATUS_PUBLISHED)

    def test_published_configurations_are_isolated_by_plan_year(self):
        slot = self.make_slot()
        self.publish_block(2025)
        self.publish_block(2026)
        for year in (2025, 2026):
            version = self.make_version(slot, plan_year=year)
            version.submit_for_review()
            version.publish()

        self.assertEqual(
            ContentSlotVersion.objects.filter(
                slot=slot,
                status=ContentSlotVersion.STATUS_PUBLISHED,
            ).count(),
            2,
        )

    def test_database_allows_at_most_one_published_configuration_per_slot_year(self):
        slot = self.make_slot()
        first = self.make_version(slot, configuration={'variants': []})
        first.status = ContentSlotVersion.STATUS_PUBLISHED
        first.save()
        second = self.make_version(slot, configuration={'variants': []})
        second.status = ContentSlotVersion.STATUS_PUBLISHED
        with self.assertRaises(IntegrityError), transaction.atomic():
            second.save()

    def test_configuration_publication_does_not_change_block_publication(self):
        slot = self.make_slot()
        block_version = self.publish_block()
        config = self.make_version(slot)
        config.submit_for_review()
        config.publish()

        block_version.refresh_from_db()
        self.assertEqual(block_version.status, ContentBlockVersion.STATUS_PUBLISHED)
