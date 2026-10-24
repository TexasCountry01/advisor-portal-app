import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

from django.contrib.auth import get_user_model
from django.core.wsgi import get_wsgi_application
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from core.models import SystemSettings
from fact_finder_content.models import (
    ContentBlock,
    ContentBlockGroup,
    ContentBlockVersion,
)
from fact_finder_content.tests_api import _valid_data_contract


class QuietLoopbackRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


@override_settings(ALLOWED_HOSTS=['127.0.0.1', 'localhost', 'testserver'])
class FehbPublishedContentLoopbackIntegrationTests(TransactionTestCase):
    reset_sequences = True

    plan_year = 2026
    baseline_purpose = '<p>TEST ONLY: original FEHB purpose.</p>'
    revised_purpose = '<p>TEST ONLY: published FEHB purpose revision.</p>'

    def test_portal_publication_is_consumed_by_benefits_over_loopback(self):
        expected_database = Path(
            os.environ['FEHB_TEST_DATABASE_PATH']
        ).resolve()
        actual_database = Path(
            str(connection.settings_dict['NAME'])
        ).resolve()
        self.assertEqual(actual_database, expected_database)
        self.assertNotEqual(
            actual_database,
            Path(os.environ['FEHB_CONFIGURED_DATABASE_PATH']).resolve(),
        )

        settings_record = SystemSettings.get_settings()
        settings_record.benefits_software_api_key = 'fehb-loopback-test-key'
        settings_record.save()

        editor = get_user_model().objects.create_user(
            username='fehb_loopback_editor',
            role='administrator',
        )
        group = ContentBlockGroup.objects.create(key='fehb', label='FEHB test content')

        wording = {
            'fehb.purpose': self.baseline_purpose,
            'fehb.coverage_available': '<p>TEST ONLY: stable coverage wording.</p>',
            'fehb.taxes_on_premiums': '<p>TEST ONLY: stable premium tax wording.</p>',
            'fehb.eligibility_to_keep_in_retirement':
                '<p>TEST ONLY: stable eligibility wording.</p>',
            'fehb.dual_federal_couples': '<p>TEST ONLY: stable couples wording.</p>',
            'fehb.changes_in_retirement':
                '<p>TEST ONLY: stable retirement-change wording.</p>',
            'fehb.current_cost_intro':
                '<p>TEST ONLY: stable current-cost intro.</p>',
            'fehb.deferred_sentence': '<p>TEST ONLY: Deferred variant.</p>',
            'fehb.projection_intro_not_deferred':
                '<p>TEST ONLY: Non-Deferred variant.</p>',
        }
        conditions = {
            'fehb.deferred_sentence': {'rules': [{
                'field': 'system.retirement_type',
                'operator': 'equals',
                'value': 'Deferred',
            }]},
            'fehb.projection_intro_not_deferred': {'rules': [{
                'field': 'system.retirement_type',
                'operator': 'equals',
                'value': 'Regular',
            }]},
        }
        blocks = {}
        for key, body in wording.items():
            block = ContentBlock.objects.create(
                key=key,
                group=group,
                label=f'{key} (synthetic integration fixture)',
                display_condition=conditions.get(key, {}),
            )
            blocks[key] = block
            ContentBlockVersion.objects.create(
                block=block,
                plan_year=self.plan_year,
                body_html=body,
                status=ContentBlockVersion.STATUS_PUBLISHED,
                created_by=editor,
            )

        purpose_block = blocks['fehb.purpose']
        ContentBlockVersion.objects.create(
            block=purpose_block,
            plan_year=2025,
            body_html='<p>TEST ONLY: wrong-plan-year decoy.</p>',
            status=ContentBlockVersion.STATUS_PUBLISHED,
            created_by=editor,
        )
        source = purpose_block.versions.get(
            plan_year=self.plan_year,
            status=ContentBlockVersion.STATUS_PUBLISHED,
        )

        editor_client = self.client
        editor_client.force_login(editor)
        editor_url = reverse(
            'fact_finder_content:content_block_detail',
            args=[purpose_block.pk],
        )

        with tempfile.TemporaryDirectory(prefix='fehb-loopback-html-') as output_dir:
            server = make_server(
                '127.0.0.1',
                0,
                get_wsgi_application(),
                handler_class=QuietLoopbackRequestHandler,
            )
            port = server.server_port
            self.assertGreater(port, 0)
            server_thread = threading.Thread(
                target=server.serve_forever,
                name='fehb-disposable-loopback-server',
                daemon=True,
            )
            server_thread.start()
            print(f'Loopback HTTP server bound to 127.0.0.1:{port}')
            try:
                self._run_benefits_phase(
                    'baseline',
                    port,
                    output_dir,
                )

                draft_response = editor_client.post(editor_url, {
                    'action': 'create_draft',
                    'plan_year': self.plan_year,
                    'body_html': self.revised_purpose,
                    'source_version_id': source.pk,
                    'editor_ready': 'ready',
                })
                self.assertEqual(draft_response.status_code, 302)
                draft = purpose_block.versions.get(
                    plan_year=self.plan_year,
                    status=ContentBlockVersion.STATUS_DRAFT,
                )
                self.assertEqual(draft.body_html, self.revised_purpose)
                source.refresh_from_db()
                self.assertEqual(source.status, ContentBlockVersion.STATUS_PUBLISHED)

                self._run_benefits_phase('draft', port, output_dir)

                publish_response = editor_client.post(editor_url, {
                    'action': 'save_and_publish',
                    'plan_year': self.plan_year,
                    'body_html': self.revised_purpose,
                    'source_version_id': source.pk,
                    'editor_ready': 'ready',
                })
                self.assertEqual(publish_response.status_code, 302)
                source.refresh_from_db()
                self.assertEqual(source.status, ContentBlockVersion.STATUS_SUPERSEDED)
                self.assertEqual(source.body_html, self.baseline_purpose)
                published = purpose_block.versions.get(
                    plan_year=self.plan_year,
                    status=ContentBlockVersion.STATUS_PUBLISHED,
                )
                self.assertEqual(published.body_html, self.revised_purpose)
                self.assertEqual(
                    purpose_block.versions.filter(
                        plan_year=self.plan_year,
                        status=ContentBlockVersion.STATUS_DRAFT,
                        body_html=self.revised_purpose,
                    ).count(),
                    1,
                )

                self._run_benefits_phase('published', port, output_dir)
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=5)
                self.assertFalse(server_thread.is_alive())

    def _run_benefits_phase(self, phase, port, output_dir):
        workspace = Path(__file__).resolve().parents[2]
        benefits_root = workspace / 'benefits-software'
        phpunit = benefits_root / 'vendor' / 'bin' / 'phpunit'
        php = shutil.which('php')
        self.assertTrue(phpunit.is_file(), f'PHPUnit not found: {phpunit}')
        self.assertIsNotNone(php, 'PHP executable is not available on PATH.')

        contract = _valid_data_contract()
        environment = os.environ.copy()
        environment.update({
            'FEHB_INTEGRATION_BASE_URL': f'http://127.0.0.1:{port}',
            'FEHB_INTEGRATION_API_KEY': 'fehb-loopback-test-key',
            'FEHB_INTEGRATION_PLAN_YEAR': str(self.plan_year),
            'FEHB_INTEGRATION_DATA_CONTRACT': json.dumps(contract),
            'FEHB_INTEGRATION_PHASE': phase,
            'FEHB_INTEGRATION_OUTPUT_DIR': output_dir,
            'NO_PROXY': '127.0.0.1,localhost',
            'no_proxy': '127.0.0.1,localhost',
        })
        test_file = benefits_root / 'tests' / 'Unit' / 'FactFinderFehbBladeRenderingTest.php'
        command = [
            php,
            str(phpunit),
            '--no-configuration',
            str(test_file),
            '--filter',
            'testPublishedFehbPurposeIsConsumedAndRenderedOverLoopback',
        ]
        result = subprocess.run(
            command,
            cwd=str(benefits_root),
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        output = result.stdout + result.stderr
        self.assertEqual(
            result.returncode,
            0,
            f'Benefits PHPUnit loopback phase {phase!r} failed.\n'
            f'Command: {subprocess.list2cmdline(command)}\n{output}',
        )
        print(f'Benefits loopback phase {phase}:\n{output.strip()}')
