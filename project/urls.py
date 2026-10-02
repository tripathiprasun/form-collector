from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Form Collector"
admin.site.site_title = "Form Collector"
admin.site.index_title = "Forms and responses"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("collector.urls")),
]
