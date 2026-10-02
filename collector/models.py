import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

KIND_CHOICES = [
    ("text", "Short answer"),
    ("textarea", "Long answer"),
    ("email", "Email"),
    ("number", "Number"),
    ("date", "Date"),
    ("dropdown", "Dropdown"),
    ("radio", "Multiple choice (pick one)"),
    ("checkboxes", "Checkboxes (pick several)"),
]
CHOICE_KINDS = {"dropdown", "radio", "checkboxes"}
NO_DUPLICATE_KINDS = {"text", "email", "number", "date", "dropdown", "radio"}


def generate_slug():
    return secrets.token_urlsafe(6)


class Form(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=64, unique=True, default=generate_slug)
    description = models.TextField(blank=True)
    confirmation_message = models.CharField(
        max_length=300, default="Your response has been recorded."
    )
    is_open = models.BooleanField(default=True)
    collect_ip = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Question(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="questions")
    label = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="text")
    required = models.BooleanField(default=True)
    hint = models.CharField(max_length=300, blank=True)
    choices_text = models.TextField(blank=True)
    no_duplicates = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label

    @property
    def key(self):
        return f"q_{self.pk}"

    def choice_list(self):
        seen = []
        for line in self.choices_text.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.append(line)
        return seen

    def clean(self):
        if self.kind in CHOICE_KINDS and len(self.choice_list()) < 2:
            raise ValidationError(
                {"choices_text": "Add at least two options, one per line."}
            )
        if self.no_duplicates and self.kind not in NO_DUPLICATE_KINDS:
            raise ValidationError(
                {"no_duplicates": "Not available for this question type."}
            )


class Response(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="responses")
    data = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    dedupe_key = models.CharField(max_length=320, null=True, blank=True, editable=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["form", "-submitted_at"], name="resp_form_time_idx"),
        ]
        constraints = [
            # One response per distinct answer to the form's "no duplicates" question.
            models.UniqueConstraint(
                fields=["form", "dedupe_key"],
                condition=models.Q(dedupe_key__isnull=False),
                name="unique_response_dedupe_per_form",
            ),
        ]

    def __str__(self):
        return f"Response #{self.pk} to {self.form}"

    def answers(self):
        """List of (question label, answer text) in the form's current question order."""
        out = []
        for q in self.form.questions.all():
            value = self.data.get(str(q.pk), "")
            if isinstance(value, list):
                value = "; ".join(value)
            out.append((q.label, value))
        return out
