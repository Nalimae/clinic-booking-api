
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Doctor(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Patient(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name


class WorkingHours(models.Model):
    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="working_hours",
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "weekday", "start_time"],
                name="unique_doctor_workday_start",
            ),
        ]

    def __str__(self):
        return (
            f"{self.doctor.name} - "
            f"{self.get_weekday_display()} "
            f"{self.start_time}-{self.end_time}"
        )

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(
                "Working hours must end after they start."
            )


class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.BOOKED,
    )
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(
                fields=["doctor", "start_at", "end_at"],
                name="appt_doctor_time_idx",
            ),
            models.Index(
                fields=["patient", "start_at"],
                name="appt_patient_time_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.doctor.name} - "
            f"{self.patient.name} - {self.start_at}"
        )

    def clean(self):
        if self.start_at >= self.end_at:
            raise ValidationError(
                "Appointment end time must be after start time."
            )

        if self.start_at <= timezone.now():
            raise ValidationError(
                "Appointments must be scheduled in the future."
            )

        if self.status == self.Status.CANCELLED:
            if not self.cancellation_reason.strip():
                raise ValidationError(
                    "A cancellation reason is required."
                )
