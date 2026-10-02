import csv
from datetime import timezone

from django.http import HttpResponse


def _safe(value):
    # Stop spreadsheet apps from running cells that start with a formula character.
    value = str(value)
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def csv_response(form_obj, queryset):
    questions = list(form_obj.questions.all())
    include_ip = (
        form_obj.collect_ip or queryset.exclude(ip_address__isnull=True).exists()
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{form_obj.slug}-responses.csv"'
    )
    writer = csv.writer(response)

    header = ["Submitted at (UTC)"]
    if include_ip:
        header.append("IP address")
    header += [_safe(q.label) for q in questions]
    writer.writerow(header)

    for r in queryset.order_by("submitted_at"):
        row = [r.submitted_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")]
        if include_ip:
            row.append(r.ip_address or "")
        for q in questions:
            value = r.data.get(str(q.pk), "")
            if isinstance(value, list):
                value = "; ".join(value)
            row.append(_safe(value))
        writer.writerow(row)
    return response
