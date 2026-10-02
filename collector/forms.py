from datetime import date
from decimal import Decimal

from django import forms

from .models import Response

HONEYPOT = "website"
DUPLICATE_MESSAGE = (
    "A response with this answer has already been submitted. "
    "If you think this is a mistake, tell whoever sent you this form."
)


def serialize(value):
    """Turn a cleaned form value into something JSON-safe and readable."""
    if value is None:
        return ""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def build_field(q):
    msgs = {"required": "This question is required."}
    common = {"label": q.label, "required": q.required, "help_text": q.hint}
    kind = q.kind

    if kind == "textarea":
        return forms.CharField(
            max_length=5000,
            widget=forms.Textarea(attrs={"rows": 5}),
            error_messages=msgs,
            **common,
        )
    if kind == "email":
        msgs["invalid"] = "That doesn't look like a valid email address."
        return forms.EmailField(max_length=254, error_messages=msgs, **common)
    if kind == "number":
        msgs["invalid"] = "Please enter a number."
        return forms.DecimalField(
            max_digits=30, decimal_places=10, error_messages=msgs, **common
        )
    if kind == "date":
        msgs["invalid"] = "Please enter a valid date."
        return forms.DateField(
            widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            error_messages=msgs,
            **common,
        )

    options = [(c, c) for c in q.choice_list()]
    msgs["invalid_choice"] = "Please pick one of the available options."
    if kind == "dropdown":
        return forms.ChoiceField(
            choices=[("", "Choose one...")] + options, error_messages=msgs, **common
        )
    if kind == "radio":
        return forms.ChoiceField(
            choices=options, widget=forms.RadioSelect, error_messages=msgs, **common
        )
    if kind == "checkboxes":
        return forms.MultipleChoiceField(
            choices=options,
            widget=forms.CheckboxSelectMultiple,
            error_messages=msgs,
            **common,
        )
    return forms.CharField(max_length=300, error_messages=msgs, **common)


class FillForm(forms.Form):
    # Honeypot: hidden from people, bots tend to fill it in.
    website = forms.CharField(
        required=False,
        label="Leave this field empty",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    def __init__(self, form_obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_obj = form_obj
        self.questions = list(form_obj.questions.all())
        self.unique_question = None
        for q in self.questions:
            self.fields[q.key] = build_field(q)
            if q.no_duplicates:
                self.unique_question = q
        self.order_fields([q.key for q in self.questions] + [HONEYPOT])

    @property
    def unique_field_name(self):
        return self.unique_question.key if self.unique_question else None

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["aria-invalid"] = "true"

    def clean(self):
        cleaned = super().clean()
        uq = self.unique_question
        if uq and uq.key in cleaned:
            key = serialize(cleaned[uq.key]).strip().lower()
            if key and Response.objects.filter(
                form=self.form_obj, dedupe_key=key
            ).exists():
                self.add_error(uq.key, DUPLICATE_MESSAGE)
        return cleaned

    def build_response(self, ip):
        data = {}
        dedupe_key = None
        for q in self.questions:
            value = serialize(self.cleaned_data.get(q.key))
            data[str(q.pk)] = value
            if q is self.unique_question and isinstance(value, str) and value.strip():
                dedupe_key = value.strip().lower()
        return Response(
            form=self.form_obj,
            data=data,
            ip_address=ip if self.form_obj.collect_ip else None,
            dedupe_key=dedupe_key,
        )
