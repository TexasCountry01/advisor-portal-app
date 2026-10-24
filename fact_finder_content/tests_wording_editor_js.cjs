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
        'body_html', 'newDraftForm', 'save-draft-btn', 'save-publish-btn',
        'editor_ready', 'editor-error',
        'draft_version_id', 'source_version_id', 'plan_year', 'editing-year', 'draft-editor-mode',
        'editorConfirmationModal', 'editorConfirmationTitle', 'editorConfirmationMessage',
        'editorConfirmationConfirm', 'editorConfirmationCancel', 'editor-confirmation-error',
    ]) {
        elements[id] = {
            value: '', textContent: '', hidden: true, disabled: true, listeners: {},
            addEventListener(event, callback) { this.listeners[event] = callback; },
            scrollIntoView() {},
            getAttribute(name) { return this.attributes && this.attributes[name]; },
        };
    }
    elements.body_html.value = '<p>Stored wording</p>';
    elements['save-publish-btn'].attributes = {
        'data-confirm-title': 'Publish report wording?',
        'data-confirm-message': 'Section: Wording safety. Plan year: 2026. The previous published wording will remain available in Version History.',
        'data-confirm-label': 'Publish Changes',
    };
    let modalShown = false;
    let submitted = false;
    const documentListeners = {};
    const form = elements.newDraftForm;
    form.requestSubmit = function(submitter) {
        const event = {
            target: form, submitter, prevented: false,
            preventDefault() { this.prevented = true; },
        };
        documentListeners.submit(event);
        if (!event.prevented) {
            form.listeners.submit(event);
            submitted = !event.prevented;
        }
    };
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
        addEventListener(event, callback, capture) {
            if (event === 'DOMContentLoaded') { callback(); }
            else { documentListeners[event] = callback; }
        },
    };
    const context = {
        document,
        window: {
            bootstrap: {
                Modal: {
                    getOrCreateInstance() {
                        return {
                            show() { modalShown = true; },
                            hide() { modalShown = false; },
                        };
                    },
                },
            },
        },
    };
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
        get modalShown() { return modalShown; },
        get submitted() { return submitted; },
        submit(submitter = elements['save-draft-btn']) {
            const event = {
                target: form, submitter, prevented: false,
                preventDefault() { this.prevented = true; },
            };
            documentListeners.submit(event);
            if (!event.prevented) { form.listeners.submit(event); }
            return event;
        },
        confirm() { elements.editorConfirmationConfirm.listeners.click(); },
        cancel() { elements.editorConfirmationCancel.listeners.click(); },
    };
}

for (const mode of ['missing', 'throws', 'rejected', 'pending', 'removed', 'unsynchronized']) {
    test(`blocks ${mode} editor without submitting empty hidden wording`, () => {
        const page = mount(mode);
        assert.equal(page.submit().prevented, true);
        assert.equal(page.elements.editor_ready.value, '');
        assert.equal(page.elements['save-draft-btn'].disabled, true);
        assert.equal(page.elements['save-publish-btn'].disabled, true);
        assert.equal(page.elements.body_html.value, '<p>Stored wording</p>');
        assert.equal(page.elements['editor-error'].hidden, false);
    });
}

test('synchronizes the named textarea at submission', () => {
    const page = mount();
    assert.equal(page.elements['save-draft-btn'].disabled, false);
    assert.equal(page.elements['save-publish-btn'].disabled, false);
    assert.equal(page.submit().prevented, false);
    assert.equal(page.elements.body_html.value, '<p>Edited wording</p>');
    assert.equal(page.elements.editor_ready.value, 'ready');
});

test('Save & Publish waits for confirmation and synchronizes before submission', () => {
    const page = mount();
    const submitEvent = page.submit(page.elements['save-publish-btn']);
    assert.equal(submitEvent.prevented, true);
    assert.equal(page.modalShown, true);
    assert.equal(page.elements.editorConfirmationTitle.textContent, 'Publish report wording?');
    assert.match(page.elements.editorConfirmationMessage.textContent, /Section: Wording safety/);
    assert.match(page.elements.editorConfirmationMessage.textContent, /Plan year: 2026/);
    assert.match(page.elements.editorConfirmationMessage.textContent, /Version History/);
    assert.equal(page.elements.editorConfirmationConfirm.textContent, 'Publish Changes');
    assert.equal(page.submitted, false);
    page.confirm();
    assert.equal(page.elements.body_html.value, '<p>Edited wording</p>');
    assert.equal(page.elements.editor_ready.value, 'ready');
    assert.equal(page.submitted, true);
});

test('cancelling Save & Publish leaves the form untouched', () => {
    const page = mount();
    page.submit(page.elements['save-publish-btn']);
    page.cancel();
    assert.equal(page.submitted, false);
    assert.equal(page.elements.editor_ready.value, '');
    assert.equal(page.elements.body_html.value, '<p>Stored wording</p>');
});

test('blocks empty editor content', () => {
    const page = mount();
    page.editor.content = '   ';
    assert.equal(page.submit().prevented, true);
    assert.equal(page.elements.editor_ready.value, '');
});

test('loading a historical draft asks for confirmation, then sets its source, year and update ID', () => {
    const page = mount();
    page.loadButton.click();
    assert.equal(page.modalShown, true);
    assert.equal(page.elements.editorConfirmationTitle.textContent, 'Load saved wording?');
    page.confirm();
    assert.equal(page.elements.plan_year.value, '2025');
    assert.equal(page.elements['editing-year'].textContent, '2025');
    assert.equal(page.elements.draft_version_id.value, '7');
    assert.equal(page.elements.source_version_id.value, '7');
    assert.equal(page.elements.body_html.value, '<p>Historical wording</p>');
});

test('loading published history creates a draft only in that source year after confirmation', () => {
    const page = mount();
    page.loadButton.values['data-version-status'] = 'published';
    page.loadButton.click();
    page.confirm();
    assert.equal(page.elements.draft_version_id.value, '');
    assert.equal(page.elements.source_version_id.value, '7');
    assert.equal(page.elements.plan_year.value, '2025');
});
