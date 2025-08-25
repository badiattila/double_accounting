from django.contrib import admin
from django.conf import settings

admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Admin")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Admin")
