from django.contrib import admin

from .models import ETLRunAudit


@admin.register(ETLRunAudit)
class ETLRunAuditAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "started_at",
        "ended_at",
        "start_date",
        "end_date",
        "source_rows",
        "deleted_rows",
        "inserted_rows",
    )
    list_filter = ("status", "started_at")
    search_fields = ("error_message",)
