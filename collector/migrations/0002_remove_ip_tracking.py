from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("collector", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="response", name="ip_address"),
        migrations.RemoveField(model_name="form", name="collect_ip"),
    ]
