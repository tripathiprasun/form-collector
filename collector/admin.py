from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.forms import BaseInlineFormSet
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .exports import csv_response
from .models import Form, Question, Response


class FormAdminForm(forms.ModelForm):
    class Meta:
        model = Form
        fields = "__all__"
        labels = {
            "title": "Form title",
            "slug": "Link name",
            "description": "Intro text",
            "confirmation_message": "Message after submitting",
            "is_open": "Accepting responses",
        }
        help_texts = {
            "slug": "Used in the link: /f/<link name>/. Changing it breaks links you already sent.",
            "description": "Shown above the questions. Optional.",
            "is_open": "Untick to close the form. People opening the link will see that it is closed.",
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"
        labels = {
            "order": "Order",
            "label": "Question",
            "kind": "Type",
            "required": "Required",
            "hint": "Small hint under the question",
            "choices_text": "Options (one per line)",
            "no_duplicates": "No duplicates",
        }
        help_texts = {
            "order": "Lowest number shows first.",
            "choices_text": "Only for dropdown, multiple choice and checkboxes.",
            "no_duplicates": "Only one response per distinct answer (e.g. one per email). One question per form.",
        }
        widgets = {
            "label": forms.TextInput(attrs={"size": 32}),
            "hint": forms.TextInput(attrs={"size": 24}),
            "choices_text": forms.Textarea(attrs={"rows": 3, "cols": 24}),
            "order": forms.NumberInput(attrs={"style": "width: 4em;"}),
        }


class QuestionInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        count = 0
        for f in self.forms:
            data = getattr(f, "cleaned_data", None)
            if not data or data.get("DELETE") or not data.get("label"):
                continue
            if data.get("no_duplicates"):
                count += 1
        if count > 1:
            raise ValidationError(
                "Only one question per form can have 'No duplicates' ticked."
            )


class QuestionInline(admin.TabularInline):
    model = Question
    form = QuestionForm
    formset = QuestionInlineFormSet
    extra = 3
    fields = ("order", "label", "kind", "required", "choices_text", "no_duplicates", "hint")


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    form = FormAdminForm
    inlines = [QuestionInline]
    list_display = ("title", "share_link", "is_open", "response_count", "created_at", "export_link")
    list_filter = ("is_open",)
    search_fields = ("title", "slug")
    readonly_fields = ("share_link", "responses_link")
    fieldsets = (
        (None, {"fields": ("title", "description", "slug", "share_link", "confirmation_message")}),
        ("Settings", {"fields": ("is_open", "responses_link")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_response_count=Count("responses"))

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Link to share")
    def share_link(self, obj):
        if not obj.pk:
            return "Save the form to get its link."
        url = settings.SITE_URL + reverse("fill", args=[obj.slug])
        return format_html('<a href="{0}" target="_blank" rel="noopener">{0}</a>', url)

    @admin.display(description="Responses", ordering="_response_count")
    def response_count(self, obj):
        return obj._response_count

    @admin.display(description="CSV")
    def export_link(self, obj):
        return format_html(
            '<a href="{}">Download</a>', reverse("export_csv", args=[obj.slug])
        )

    @admin.display(description="Responses")
    def responses_link(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin:collector_response_changelist") + f"?form__id__exact={obj.pk}"
        return format_html('<a href="{}">View responses</a>', url)


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "form", "preview", "submitted")
    list_filter = ("form", "submitted_at")
    search_fields = ("dedupe_key", "form__title")
    date_hierarchy = "submitted_at"
    ordering = ("-submitted_at",)
    fields = ("form", "answers_table", "submitted")
    readonly_fields = fields
    actions = ["export_selected_csv"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("form")
            .prefetch_related("form__questions")
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # responses are read-only (they can still be deleted)

    @admin.display(description="Answers")
    def preview(self, obj):
        parts = [str(v) for _, v in obj.answers()[:2]]
        return " | ".join(parts)[:80]

    @admin.display(description="Answers")
    def answers_table(self, obj):
        rows = format_html_join(
            "",
            '<tr><th style="text-align:left;vertical-align:top">{}</th>'
            '<td style="white-space:pre-wrap">{}</td></tr>',
            obj.answers(),
        )
        return format_html("<table>{}</table>", rows)

    @admin.display(description="Submitted", ordering="submitted_at")
    def submitted(self, obj):
        return timezone.localtime(obj.submitted_at).strftime("%d %b %Y, %H:%M:%S %Z")

    @admin.action(description="Download selected responses as CSV")
    def export_selected_csv(self, request, queryset):
        form_ids = set(queryset.values_list("form_id", flat=True))
        if len(form_ids) != 1:
            self.message_user(
                request, "Select responses from one form at a time.", messages.ERROR
            )
            return None
        form_obj = Form.objects.get(pk=form_ids.pop())
        return csv_response(form_obj, queryset)
