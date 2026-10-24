"""I-05 structured-content publication, API, and sanitizer contract tests."""

import json
from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.test import TestCase, SimpleTestCase
from django.urls import reverse

from core.models import SystemSettings
from fact_finder_content.models import (
    ContentBlock,
    ContentBlockGroup,
    ContentBlockVersion,
)
from fact_finder_content.sanitize import sanitize_body_html
from fact_finder_content.tests_api import _valid_data_contract


I05_TABLES = {
    'pension.high3_pay_included_table': (
        1, (3,), ('', 'Pay included', 'Pay NOT included'),
    ),
    'sbp.levels_fers_transfers': (3, (2, 2, 2), ('Level', 'Details')),
    'sbp.levels_csrs': (4, (2, 2, 2, 2), ('Level', 'Details')),
    'fegli.coverage_available': (5, (2, 2, 2, 2, 2), ('Coverage', 'Description')),
    'fegli.choices_in_retirement_table': (5, (2, 2, 2, 2, 2), ('Coverage', 'Election')),
    'fltcip.coverage_available_intro': (6, (1, 2, 2, 2, 2, 2), ()),
    'tsp.five_funds_available': (6, (4, 4, 4, 4, 4, 4), ('Fund', 'Description', 'Index', 'Rate')),
}

I05_LISTS = {
    'checklist.topics_before_srs': (2, 3, 2),
    'checklist.srs_topic': (2, 1, 1),
    'checklist.topics_after_srs': (2, 2, 1),
}

I05_KEYS = tuple(I05_TABLES) + tuple(I05_LISTS)
REQUIRED_TOKENS = {
    'fltcip.coverage_available_intro': (
        'fltcip.daily_benefit_amount',
        'fltcip.benefit_period',
        'fltcip.waiting_period',
        'fltcip.inflation_protection',
    ),
    'tsp.five_funds_available': (
        'tsp.gfund_rate',
        'tsp.ffund_rate',
        'tsp.cfund_rate',
        'tsp.sfund_rate',
        'tsp.ifund_rate',
    ),
}

LIST_STYLE_OUTER = 'img|svg|3|3|images/rectangle.svg'
LIST_STYLE_INNER = 'img|svg|3|3|images/circle.svg'


class HtmlStructure(HTMLParser):
    """Collect only the structural facts needed by the I-05 fixtures."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ul_depth = 0
        self.max_ul_depth = 0
        self.list_item_count = 0
        self.rows = []
        self.current_row = None
        self.headers = []
        self.current_cell_tag = None
        self.current_cell_text = []
        self.attributes_by_tag = {}

    def handle_starttag(self, tag, attrs):
        self.attributes_by_tag.setdefault(tag, []).append(dict(attrs))
        if tag == 'ul':
            self.ul_depth += 1
            self.max_ul_depth = max(self.max_ul_depth, self.ul_depth)
        elif tag == 'li':
            self.list_item_count += 1
        elif tag == 'tr':
            self.current_row = 0
        elif tag in ('td', 'th') and self.current_row is not None:
            self.current_row += 1
            self.current_cell_tag = tag
            self.current_cell_text = []

    def handle_data(self, data):
        if self.current_cell_tag == 'th':
            self.current_cell_text.append(data)

    def handle_endtag(self, tag):
        if tag == 'ul':
            self.ul_depth -= 1
        elif tag in ('td', 'th') and self.current_cell_tag == tag:
            if tag == 'th':
                self.headers.append(''.join(self.current_cell_text).strip())
            self.current_cell_tag = None
            self.current_cell_text = []
        elif tag == 'tr' and self.current_row is not None:
            self.rows.append(self.current_row)
            self.current_row = None


def _table_html(key, year):
    rows, columns_per_row, headings = I05_TABLES[key]
    header_count = 0 if key == 'pension.high3_pay_included_table' else len(headings)
    rendered = [
        '<table cellpadding="3" style="font-family:Arial, sans-serif; font-size:9px;">',
    ]
    if key == 'pension.high3_pay_included_table':
        rendered.append('<tbody><tr>')
        for heading in headings:
            rendered.append(f'<th width="33%">{heading}</th>')
        rendered.append('</tr></tbody></table>')
        return ''.join(rendered)
    if header_count:
        rendered.append('<thead><tr>')
        for heading in headings:
            rendered.append(f'<th width="50%" style="font-weight: bold;">{heading}</th>')
        rendered.append('</tr></thead>')
        first_data_row = 1
    else:
        first_data_row = 0
    rendered.append('<tbody>')
    for row_index in range(first_data_row, rows):
        columns = columns_per_row[row_index]
        rendered.append('<tr>')
        for column in range(columns):
            if key == 'tsp.five_funds_available' and row_index > 0 and column == 3:
                value = f'[[tsp.{"gfund ffund cfund sfund ifund".split()[row_index - 1]}_rate]]%'
            elif key == 'fltcip.coverage_available_intro' and row_index > 1 and column == 1:
                value = f'[[fltcip.{"daily_benefit_amount benefit_period waiting_period inflation_protection".split()[row_index - 2]}]]'
            else:
                value = f'{key}:{year}:row{row_index}:column{column}'
            rendered.append(f'<td width="50%">{value}</td>')
        rendered.append('</tr>')
    rendered.append('</tbody></table>')
    return ''.join(rendered)


def _list_html(key, year):
    _, top_level_items, nested_lists = I05_LISTS[key]
    body = [
        f'<ul style="list-style-type:{LIST_STYLE_OUTER}; font-size:10px;">',
    ]
    for index in range(top_level_items):
        body.append(f'<li>Published {year} {key} topic {index + 1}')
        if index < nested_lists:
            body.append(f'<ul style="list-style-type:{LIST_STYLE_INNER};">')
            body.append(f'<li><em>Nested question for {key} {index + 1}</em></li></ul>')
        body.append('</li>')
    body.append('</ul>')
    return ''.join(body)


def _body_html(key, year):
    return _table_html(key, year) if key in I05_TABLES else _list_html(key, year)


class I05StructuredContentApiTests(TestCase):
    """Verify exact v1 bodies, plan-year selection, and version-state isolation."""

    def setUp(self):
        settings_obj = SystemSettings.get_settings()
        settings_obj.benefits_software_api_key = 'test-shared-secret'
        settings_obj.save()
        self.url = reverse('fact_finder_resolve_content')
        self.auth = {'HTTP_AUTHORIZATION': 'Bearer test-shared-secret'}
        self.versions = {}
        for index, key in enumerate(I05_KEYS, start=1):
            group_key = key.split('.', 1)[0]
            group, _ = ContentBlockGroup.objects.get_or_create(
                key=group_key,
                defaults={'label': group_key, 'display_order': index},
            )
            group.display_order = index
            group.save(update_fields=['display_order'])
            conditions = {
                'sbp.levels_fers_transfers': [
                    ('computed_flags.is_fers_or_transfers', True),
                ],
                'sbp.levels_csrs': [
                    ('computed_flags.is_csrs_or_csrs_offset', True),
                ],
                'checklist.srs_topic': [
                    ('computed_flags.is_fers_or_transfers', True),
                ],
            }.get(key, [])
            block = ContentBlock.objects.create(
                key=key,
                group=group,
                label=key,
                required_placeholders=list(REQUIRED_TOKENS.get(key, ())),
                display_condition={
                    'rules': [
                        {
                            'field': field,
                            'operator': 'equals',
                            'value': value,
                        }
                        for field, value in conditions
                    ],
                },
            )
            active_2025 = self._publish(block, 2025, _body_html(key, 2025))
            active_2026 = self._publish(block, 2026, _body_html(key, 2026))
            draft = ContentBlockVersion.objects.create(
                block=block,
                plan_year=2026,
                body_html=_body_html(key, 2026).replace('Published 2026', 'DRAFT ONLY'),
            )
            review = ContentBlockVersion.objects.create(
                block=block,
                plan_year=2026,
                body_html=_body_html(key, 2026).replace('Published 2026', 'REVIEW ONLY'),
            )
            review.submit_for_review()
            self.versions[key] = (block, active_2025, active_2026, draft, review)

    def _publish(self, block, year, body):
        version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=year,
            body_html=body,
        )
        version.submit_for_review()
        version.publish()
        return version

    def _contract(self, system_type='FERS'):
        contract = _valid_data_contract()
        contract['system']['system_type'] = system_type
        contract['tsp'].update({
            'gfund_rate': '2.4',
            'ffund_rate': '1.5',
            'cfund_rate': '12.3',
            'sfund_rate': '8.6',
            'ifund_rate': '5.7',
        })
        contract['fltcip'] = {
            'daily_benefit_amount': '$333/day',
            'benefit_period': '4 years',
            'waiting_period': '60 days',
            'inflation_protection': 'Automatic 5%',
        }
        flags = contract['computed_flags']
        flags['is_fers_or_transfers'] = system_type in ('FERS', 'Transfers')
        flags['is_csrs_or_csrs_offset'] = system_type in ('CSRS', 'CSRS Offset')
        return contract

    def _post(self, year, system_type='FERS'):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'plan_year': year,
                'data_contract': self._contract(system_type),
            }),
            content_type='application/json',
            **self.auth,
        )
        self.assertEqual(response.status_code, 200)
        return response.json()['blocks']

    def _expected_keys(self, system_type):
        excluded = set()
        if system_type not in ('FERS', 'Transfers'):
            excluded.update((
                'sbp.levels_fers_transfers',
                'checklist.srs_topic',
            ))
        if system_type not in ('CSRS', 'CSRS Offset'):
            excluded.add('sbp.levels_csrs')
        return [key for key in I05_KEYS if key not in excluded]

    def test_exact_v1_response_selects_plan_year_and_excludes_drafts_and_reviews(self):
        self.assertEqual(len(I05_KEYS), 10)
        self.assertEqual(len(set(I05_KEYS)), 10)
        for year in (2025, 2026):
            for system_type in ('FERS', 'CSRS'):
                with self.subTest(year=year, system_type=system_type):
                    blocks = self._post(year, system_type)
                    expected = [
                        {
                            'key': key,
                            'html': sanitize_body_html(_body_html(key, year)),
                            'order': index,
                        }
                        for index, key in enumerate(self._expected_keys(system_type), start=1)
                    ]
                    self.assertEqual(blocks, expected)
                    self.assertTrue(all(
                        'DRAFT ONLY' not in item['html']
                        and 'REVIEW ONLY' not in item['html']
                        for item in blocks
                    ))
                    for item in blocks:
                        parser = HtmlStructure()
                        parser.feed(item['html'])
                        if item['key'] in I05_TABLES:
                            self.assertEqual(len(parser.rows), I05_TABLES[item['key']][0])
                            self.assertEqual(
                                tuple(parser.rows),
                                I05_TABLES[item['key']][1],
                            )
                            self.assertEqual(
                                tuple(parser.headers),
                                I05_TABLES[item['key']][2],
                            )
                            self.assertEqual(
                                parser.attributes_by_tag['table'][0]['cellpadding'],
                                '3',
                            )
                            self.assertIn(
                                'width',
                                parser.attributes_by_tag['th'][0]
                                if parser.attributes_by_tag.get('th')
                                else parser.attributes_by_tag['td'][0],
                            )
                        else:
                            _, expected_items, expected_nested = I05_LISTS[item['key']]
                            self.assertEqual(parser.max_ul_depth, 2)
                            self.assertEqual(parser.list_item_count, expected_items + expected_nested)
                            self.assertIn(
                                LIST_STYLE_OUTER,
                                parser.attributes_by_tag['ul'][0]['style'],
                            )

        self.assertEqual(self._post(2024, 'FERS'), [])
        for key, (block, v2025, v2026, draft, review) in self.versions.items():
            with self.subTest(key=key, state='stored versions'):
                self.assertEqual(v2025.status, ContentBlockVersion.STATUS_PUBLISHED)
                self.assertEqual(v2026.status, ContentBlockVersion.STATUS_PUBLISHED)
                self.assertEqual(draft.status, ContentBlockVersion.STATUS_DRAFT)
                self.assertEqual(review.status, ContentBlockVersion.STATUS_IN_REVIEW)
                self.assertEqual(block.published_version_for(2026).pk, v2026.pk)

    def test_dynamic_table_tokens_are_required_and_round_trip_through_v1(self):
        for key, tokens in REQUIRED_TOKENS.items():
            with self.subTest(key=key):
                block = self.versions[key][0]
                body = _body_html(key, 2026)
                version = ContentBlockVersion.objects.create(
                    block=block,
                    plan_year=2027,
                    body_html=body.replace(f'[[{tokens[0]}]]', 'STATIC EDITOR VALUE'),
                )
                with self.assertRaises(ValidationError):
                    version.validate_publishable()

                response = self._post(2026, 'FERS')
                body_response = next(item['html'] for item in response if item['key'] == key)
                self.assertTrue(all(f'[[{token}]]' in body_response for token in tokens))


class I05SanitizerTests(SimpleTestCase):
    """Exercise the unchanged sanitizer allow-list on representative structures."""

    def test_safe_table_and_nested_list_structure_and_formatting_are_preserved(self):
        table = (
            '<table cellpadding="3" style="font-family:Arial, sans-serif; font-size:9px;">'
            '<thead><tr><th width="30%" style="font-weight:bold;">Header</th>'
            '<th width="70%">Value</th></tr></thead><tbody>'
            '<tr><td width="30%">Row</td><td width="70%"><strong>Cell</strong></td></tr>'
            '</tbody></table>'
        )
        nested = (
            f'<ul style="list-style-type:{LIST_STYLE_OUTER};"><li>Topic'
            f'<ul style="list-style-type:{LIST_STYLE_INNER};"><li><em>Question</em></li>'
            '</ul></li></ul>'
        )
        table_result = sanitize_body_html(table)
        list_result = sanitize_body_html(nested)
        self.assertIn('<thead>', table_result)
        self.assertIn('<tbody>', table_result)
        self.assertIn('<th width="30%"', table_result)
        self.assertIn('<td width="70%">', table_result)
        self.assertIn('<strong>Cell</strong>', table_result)
        self.assertIn(f'list-style-type:{LIST_STYLE_OUTER}', list_result)
        self.assertIn(f'list-style-type:{LIST_STYLE_INNER}', list_result)
        self.assertIn('<ul', list_result)
        self.assertEqual(list_result.count('<li>'), 2)
        self.assertIn('<em>Question</em>', list_result)

    def test_malformed_and_unsupported_markup_is_neutralized_without_changing_policy(self):
        dirty = (
            '<table onclick="run()"><tr><td width="9999" '
            'style="position:fixed; background-image:url(x)">Visible'
            '<img src="file:///secret" onerror="run()"><script>run()</script>'
            '</td></tr>'
        )
        cleaned = sanitize_body_html(dirty)
        self.assertNotIn('<script', cleaned)
        self.assertNotIn('<img', cleaned)
        self.assertNotIn('onclick', cleaned)
        self.assertNotIn('onerror', cleaned)
        self.assertNotIn('file://', cleaned)
        self.assertNotIn('position:', cleaned)
        self.assertNotIn('background-image:', cleaned)
        self.assertNotIn('width="9999"', cleaned)
        self.assertIn('Visible', cleaned)
