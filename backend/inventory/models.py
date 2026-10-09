
from django.db import models


class BloodInventory(models.Model):
    id = models.BigAutoField(primary_key=True)

    facility = models.ForeignKey(
        "core.Facilities",
        models.DB_CASCADE
    )

    blood_type = models.CharField(max_length=3)
    component_type = models.CharField(max_length=30)
    units_available = models.IntegerField()
    low_threshold = models.IntegerField()
    critical_threshold = models.IntegerField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "blood_inventory"
        unique_together = (("facility", "blood_type", "component_type"),)


class InventoryTransactions(models.Model):
    id = models.BigAutoField(primary_key=True)

    inventory = models.ForeignKey(
        BloodInventory,
        models.DB_CASCADE
    )

    changed_by = models.ForeignKey(
        "core.StaffProfiles",
        models.DO_NOTHING,
        db_column="changed_by",
        blank=True,
        null=True
    )

    transaction_type = models.CharField(max_length=30)
    units_change = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True, null=True)

    donation = models.ForeignKey(
        "appointments.Donations",
        models.DO_NOTHING,
        blank=True,
        null=True
    )

    emergency_request = models.ForeignKey(
        "emergencies.EmergencyRequests",
        models.DO_NOTHING,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "inventory_transactions"
