from django.db import models
import json


class ETLRunAudit(models.Model):
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"
    STATUS_DRY_RUN = "DRY_RUN"
    STATUS_RUNNING = "RUNNING"

    STATUS_CHOICES = (
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_DRY_RUN, "Dry run"),
        (STATUS_RUNNING, "Running"),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    source_rows = models.PositiveIntegerField(default=0)
    deleted_rows = models.PositiveIntegerField(default=0)
    inserted_rows = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    status_message = models.CharField(max_length=255, default="Iniciando...")
    progress_percent = models.PositiveIntegerField(default=0)
    is_running = models.BooleanField(default=False)
    batch_size = models.PositiveIntegerField(default=1000)
    dry_run = models.BooleanField(default=False)
    summary_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"ETL {self.id} - {self.status} ({self.start_date} to {self.end_date})"
    
    def get_summary(self):
        """Get parsed summary data."""
        if isinstance(self.summary_json, str):
            return json.loads(self.summary_json)
        return self.summary_json or {}
