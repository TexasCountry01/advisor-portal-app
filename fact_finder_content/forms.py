from django import forms


class WordingDraftForm(forms.Form):
    plan_year = forms.IntegerField(min_value=1, max_value=9999)
    version_id = forms.IntegerField(required=False, min_value=1)
    source_version_id = forms.IntegerField(required=False, min_value=1)
    body_html = forms.CharField(
        strip=False,
        error_messages={'required': 'Enter report wording before saving.'},
    )
    editor_ready = forms.ChoiceField(
        choices=[('ready', 'Ready')],
        error_messages={
            'required': 'The wording editor is not ready. Keep your text and reload the page before saving.',
            'invalid_choice': 'The wording editor could not synchronize. Keep your text and reload the page.',
        },
    )
