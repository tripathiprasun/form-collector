import collector.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Form",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("slug", models.SlugField(default=collector.models.generate_slug, max_length=64, unique=True)),
                ("description", models.TextField(blank=True)),
                ("confirmation_message", models.CharField(default="Your response has been recorded.", max_length=300)),
                ("is_open", models.BooleanField(default=True)),
                ("collect_ip", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=200)),
                ("kind", models.CharField(choices=[("text", "Short answer"), ("textarea", "Long answer"), ("email", "Email"), ("number", "Number"), ("date", "Date"), ("dropdown", "Dropdown"), ("radio", "Multiple choice (pick one)"), ("checkboxes", "Checkboxes (pick several)")], default="text", max_length=20)),
                ("required", models.BooleanField(default=True)),
                ("hint", models.CharField(blank=True, max_length=300)),
                ("choices_text", models.TextField(blank=True)),
                ("no_duplicates", models.BooleanField(default=False)),
                ("order", models.PositiveIntegerField(default=0)),
                ("form", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="collector.form")),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="Response",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.JSONField(default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("dedupe_key", models.CharField(blank=True, editable=False, max_length=320, null=True)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("form", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="responses", to="collector.form")),
            ],
            options={"ordering": ["-submitted_at"]},
        ),
        migrations.AddIndex(
            model_name="response",
            index=models.Index(fields=["form", "-submitted_at"], name="resp_form_time_idx"),
        ),
        migrations.AddConstraint(
            model_name="response",
            constraint=models.UniqueConstraint(
                condition=models.Q(("dedupe_key__isnull", False)),
                fields=("form", "dedupe_key"),
                name="unique_response_dedupe_per_form",
            ),
        ),
    ]
