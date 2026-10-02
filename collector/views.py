import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.db import DatabaseError, IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .exports import csv_response
from .forms import DUPLICATE_MESSAGE, FillForm
from .models import Form
from .utils import is_rate_limited

logger = logging.getLogger(__name__)


def _error_page(request, title, message, status):
    return render(
        request,
        "collector/error.html",
        {"title": title, "message": message},
        status=status,
    )


def home(request):
    return render(request, "collector/home.html")


@require_http_methods(["GET", "HEAD", "POST"])
def fill(request, slug):
    form_obj = get_object_or_404(Form, slug=slug)

    if not form_obj.is_open:
        return render(request, "collector/closed.html", {"form_obj": form_obj})

    if request.method == "POST":
        if is_rate_limited():
            return _error_page(
                request,
                "Too many attempts",
                "The form is very busy right now. Please wait a minute and try again.",
                429,
            )

        form = FillForm(form_obj, request.POST)
        if form.is_valid():
            if form.cleaned_data.get("website"):
                return redirect("done", slug=slug)  # honeypot tripped; pretend it worked

            response = form.build_response()
            try:
                with transaction.atomic():
                    response.save()
            except IntegrityError:
                # Same answer arrived between the check and the insert.
                form.add_error(form.unique_field_name, DUPLICATE_MESSAGE)
            except DatabaseError:
                logger.exception("Database error while saving a response")
                form.add_error(
                    None,
                    "Something went wrong on our side. Please try again in a moment.",
                )
            else:
                return redirect("done", slug=slug)
    else:
        form = FillForm(form_obj)

    return render(request, "collector/form.html", {"form_obj": form_obj, "form": form})


def done(request, slug):
    form_obj = get_object_or_404(Form, slug=slug)
    return render(request, "collector/done.html", {"form_obj": form_obj})


@staff_member_required
def export_csv(request, slug):
    form_obj = get_object_or_404(Form, slug=slug)
    return csv_response(form_obj, form_obj.responses.all())


def csrf_failure(request, reason=""):
    return _error_page(
        request,
        "Please try again",
        "Your form session expired. Reload the form page and submit again.",
        403,
    )
