from django.db import models

from appointments.models import Appointments
from core.models import DonorProfiles


class EligibilityScreenings(models.Model):
    id = models.BigAutoField(primary_key=True)
    donor = models.ForeignKey(DonorProfiles, models.DB_CASCADE)
    screening_type = models.CharField(max_length=30)
    appointment = models.ForeignKey(
        Appointments,
        models.DB_SET_NULL,
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20)
    preliminary_result = models.CharField(max_length=30)
    rules_version = models.CharField(max_length=30)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    valid_until = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "eligibility_screenings"


class ScreeningQuestions(models.Model):
    id = models.BigAutoField(primary_key=True)
    question_code = models.CharField(unique=True, max_length=50)
    question_text = models.TextField()
    answer_type = models.CharField(max_length=20)
    is_required = models.BooleanField()
    is_active = models.BooleanField()
    display_order = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "screening_questions"


class ScreeningAnswers(models.Model):
    id = models.BigAutoField(primary_key=True)
    screening = models.ForeignKey(
        EligibilityScreenings,
        models.DB_CASCADE,
    )
    question = models.ForeignKey(
        ScreeningQuestions,
        models.DO_NOTHING,
    )
    answer_value = models.CharField(max_length=255)
    is_flagged = models.BooleanField()
    flag_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    answered_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "screening_answers"
        unique_together = (("screening", "question"),)