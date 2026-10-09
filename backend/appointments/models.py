
from django.db import models

from core.models import DonorProfiles, Facilities, StaffProfiles


class FacilityHours(models.Model):
    id = models.BigAutoField(primary_key=True)

    facility = models.ForeignKey(
        Facilities,
        models.DB_CASCADE,
    )

    day_of_week = models.SmallIntegerField()
    open_time = models.TimeField(blank=True, null=True)
    close_time = models.TimeField(blank=True, null=True)
    is_closed = models.BooleanField()

    class Meta:
        managed = False
        db_table = "facility_hours"
        unique_together = (("facility", "day_of_week"),)


class Appointments(models.Model):
    id = models.BigAutoField(primary_key=True)

    donor = models.ForeignKey(
        DonorProfiles,
        models.DB_CASCADE,
    )

    facility = models.ForeignKey(
        Facilities,
        models.DO_NOTHING,
    )

    request_match = models.OneToOneField(
        "emergencies.RequestMatches",
        models.DB_SET_NULL,
        blank=True,
        null=True,
    )

    donation_type = models.CharField(max_length=30)
    appointment_source = models.CharField(max_length=20)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20)

    confirmed_by = models.ForeignKey(
        StaffProfiles,
        models.DO_NOTHING,
        db_column="confirmed_by",
        blank=True,
        null=True,
    )

    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    cancelled_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "appointments"
        unique_together = (("donor", "scheduled_at"),)


class Donations(models.Model):
    id = models.BigAutoField(primary_key=True)

    appointment = models.OneToOneField(
        Appointments,
        models.DO_NOTHING,
    )

    actual_component_type = models.CharField(max_length=30)

    recorded_by = models.ForeignKey(
        StaffProfiles,
        models.DO_NOTHING,
        db_column="recorded_by",
        blank=True,
        null=True,
    )

    completed_at = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    quantity_units = models.IntegerField()

    class Meta:
        managed = False
        db_table = "donations"
