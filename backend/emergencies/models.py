from django.db import models

from core.models import DonorProfiles, StaffProfiles, Facilities, Users


class EmergencyRequests(models.Model):
    id = models.BigAutoField(primary_key=True)
    facility = models.ForeignKey(Facilities, models.DO_NOTHING)
    created_by = models.ForeignKey(
        StaffProfiles,
        models.DO_NOTHING,
        db_column="created_by",
    )
    required_blood_type = models.CharField(max_length=3)
    component_type = models.CharField(max_length=30)
    units_required = models.IntegerField()
    urgency = models.CharField(max_length=20)
    radius_km = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    fulfilled_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "emergency_requests"


class RequestMatches(models.Model):
    id = models.BigAutoField(primary_key=True)
    request = models.ForeignKey(EmergencyRequests, models.DB_CASCADE)
    donor = models.ForeignKey(DonorProfiles, models.DB_CASCADE)
    distance_km = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        blank=True,
        null=True,
    )
    match_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        blank=True,
        null=True,
    )
    notification_status = models.CharField(max_length=20)
    response_status = models.CharField(max_length=20)
    matched_at = models.DateTimeField()
    notified_at = models.DateTimeField(blank=True, null=True)
    viewed_at = models.DateTimeField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "request_matches"
        unique_together = (("request", "donor"),)


class Notifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(Users, models.DB_CASCADE)
    emergency_request = models.ForeignKey(
        EmergencyRequests,
        models.DB_CASCADE,
        blank=True,
        null=True,
    )
    request_match = models.ForeignKey(
        RequestMatches,
        models.DB_CASCADE,
        blank=True,
        null=True,
    )
    notification_type = models.CharField(max_length=30)
    title = models.CharField(max_length=150)
    message = models.TextField()
    delivery_channel = models.CharField(max_length=20)
    delivery_status = models.CharField(max_length=20)
    retry_count = models.IntegerField()
    is_read = models.BooleanField()
    created_at = models.DateTimeField()
    sent_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "notifications"