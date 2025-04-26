from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Div, Row, Column, Submit
from crispy_forms.bootstrap import InlineField, AppendedText, PrependedText, PrependedAppendedText, InlineRadios

import json

from . import calibration

class PhotometryForm(forms.Form):
    target = forms.CharField(max_length=100, required=True, label="Target")
    sr = forms.FloatField(initial=3, min_value=0, required=True, label="Radius, arcsec")
    filter = forms.ChoiceField(
        choices=[('','All')] + [(_,calibration.supported_filters[_]['name']) for _ in calibration.supported_filters.keys()],
        required=False, label="Filter"
    )
    bv = forms.FloatField(required=False, label="B-V (optional)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('target', css_class="col-md"),
                Column('sr', css_class="col-md-auto"),
                Column('filter', css_class="col-md-auto"),
                Column('bv', css_class="col-md-auto"),
                Column(
                    Submit('search', 'Search', css_class='btn-primary mb-3'),
                    css_class="col-md-auto"
                ),
                css_class='align-items-end'
            )
        )
