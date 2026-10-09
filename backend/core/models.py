
from django.db import models


class Users(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(unique=True, max_length=50)
    email = models.CharField(unique=True, max_length=120)
    password_hash = models.CharField(max_length=255)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    role = models.CharField(max_length=20)
    account_status = models.CharField(max_length=20)
    terms_accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "users"


class Facilities(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=150)
    facility_type = models.CharField(max_length=30)
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=10)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "facilities"
        unique_together = (("name", "postal_code"),)


class DonorProfiles(models.Model):
    user = models.OneToOneField(
        Users,
        models.DB_CASCADE,
        primary_key=True,
    )
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    blood_type = models.CharField(max_length=3)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=10)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    last_donation_date = models.DateField(blank=True, null=True)
    next_eligible_date = models.DateField(blank=True, null=True)
    emergency_available = models.BooleanField()
    country = models.CharField(max_length=80)

    class Meta:
        managed = False
        db_table = "donor_profiles"


class StaffProfiles(models.Model):
    user = models.OneToOneField(
        Users,
        models.DB_CASCADE,
        primary_key=True,
    )
    facility = models.ForeignKey(
        Facilities,
        models.DO_NOTHING,
    )
    authorization_declared_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "staff_profiles"
