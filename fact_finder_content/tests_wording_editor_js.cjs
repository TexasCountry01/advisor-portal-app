const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const template = fs.readFileSync(
    path.join(__dirname, 'templates', 'fact_finder_content', 'content_block_detail.html'), 'utf8'
);
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace('{{ field_value_options_json|safe }}', '{}');

function mount(mode = 'ready') {
    const elements = {};
    for (const id of [
        'body_html', 'newDraftForm', 'save-draft-btn', 'editor_ready', 'editor-error',
        'draft_version_id', 'source_version_id', 'plan_year', 'editing-year', 'draft-editor-mode',
    ]) {
        elements[id] = {
            value: '', textContent: '', hidden: true, disabled: true, listeners: {},
            addEventListener(event, callback) { this.listeners[event] = callback; },
            scrollIntoView() {},
        };
    }
    elements.body_html.value = '<p>Stored wording</p>';
    const loadButton = {
        values: {
            'data-body-html': '<p>Historical wording</p>',
            'data-version-id': '7', 'data-version-status': 'draft', 'data-plan-year': '2025',
        },
        getAttribute(name) { return this.values[name]; },
        addEventListener(event, callback) { this[event] = callback; },
    };
    const editor = {
        content: '<p>Edited wording</p>',
        on(event, callback) {
            if (event === 'init' && mode !== 'pending') { callback(); }
        },
        getContent() {
            if (mode === 'unsynchronized') { throw new Error('Editor disconnected'); }
            return this.content;
        },
        setContent(content) { this.content = content; },
    };
    const document = {
        getElementById(id) { return elements[id] || null; },
        querySelectorAll() { return [loadButton]; },
        addEventListener(event, callback) { callback(); },
    };
    const context = { document, window: { confirm: () => true } };
    if (mode !== 'missing') {
        context.tinymce = {
            get() { return mode === 'removed' ? null : editor; },
            init(options) {
                if (mode === 'throws') { throw new Error('Initialization failed'); }
                if (mode !== 'rejected') { options.setup(editor); }
                return { catch(callback) { if (mode === 'rejected') { callback(); } } };
            },
        };
    }
    vm.runInNewContext(script, context);
    return {
        elements, loadButton, editor,
        submit() {
            const event = { prevented: false, preventDefault() { this.prevented = true; } };
            elements.newDraftForm.listeners.submit(event);
            return event;
        },
    };
}

for (const mode of ['missing', 'throws', 'rejected', 'pending', 'removed', 'unsynchronized']) {
    test(`blocks ${mode} editor without submitting empty hidden wording`, () => {
        const page = mount(mode);
        assert.equal(page.submit().prevented, true);
        assert.equal(page.elements.editor_ready.value, '');
        assert.equal(page.elements['save-draft-btn'].disabled, true);
        assert.equal(page.elements.body_html.value, '<p>Stored wording</p>');
        assert.equal(page.elements['editor-error'].hidden, false);
    });
}

test('synchronizes the named textarea at submission', () => {
    const page = mount();
    assert.equal(page.elements['save-draft-btn'].disabled, false);
    assert.equal(page.submit().prevented, false);
    assert.equal(page.elements.body_html.value, '<p>Edited wording</p>');
    assert.equal(page.elements.editor_ready.value, 'ready');
});

test('blocks empty editor content', () => {
    const page = mount();
    page.editor.content = '   ';
    assert.equal(page.submit().prevented, true);
    assert.equal(page.elements.editor_ready.value, '');
});

test('loading a historical draft sets its source, year and update ID', () => {
    const page = mount();
    page.loadButton.click();
    assert.equal(page.elements.plan_year.value, '2025');
    assert.equal(page.elements['editing-year'].textContent, '2025');
    assert.equal(page.elements.draft_version_id.value, '7');
    assert.equal(page.elements.source_version_id.value, '7');
    assert.equal(page.elements.body_html.value, '<p>Historical wording</p>');
});

test('loading published history creates a draft only in that source year', () => {
    const page = mount();
    page.loadButton.values['data-version-status'] = 'published';
    page.loadButton.click();
    assert.equal(page.elements.draft_version_id.value, '');
    assert.equal(page.elements.source_version_id.value, '7');
    assert.equal(page.elements.plan_year.value, '2025');
});
