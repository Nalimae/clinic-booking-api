
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Appointment, WorkingHours


SLOT_DURATION = timedelta(minutes=30)
MINIMUM_BOOKING_NOTICE = timedelta(hours=1)


def validate_appointment_time(start_at, end_at):
    now = timezone.now()

    if start_at <= now:
        raise ValidationError({
            "start_at": "Appointment must be scheduled in the future."
        })

    if start_at < now + MINIMUM_BOOKING_NOTICE:
        raise ValidationError({
            "start_at": "Appointments must be booked at least one hour ahead."
        })

    if end_at - start_at != SLOT_DURATION:
        raise ValidationError({
            "end_at": "Appointments must be exactly 30 minutes long."
        })

    if start_at.second or start_at.microsecond:
        raise ValidationError({
            "start_at": "Appointment must start on a whole-minute boundary."
        })

    if start_at.minute not in (0, 30):
        raise ValidationError({
            "start_at": "Appointments must start on the hour or half-hour."
        })


def validate_doctor_working_hours(doctor, start_at, end_at):
    if not doctor.is_active:
        raise ValidationError({
            "doctor": "This doctor is not currently accepting appointments."
        })

    local_start = timezone.localtime(start_at)
    local_end = timezone.localtime(end_at)

    if local_start.date() != local_end.date():
        raise ValidationError({
            "end_at": "An appointment must end on the same local date it starts."
        })

    working_hours = WorkingHours.objects.filter(
        doctor=doctor,
        weekday=local_start.weekday(),
    )

    fits_working_hours = any(
        hours.start_time <= local_start.time().replace(tzinfo=None)
        and local_end.time().replace(tzinfo=None) <= hours.end_time
        for hours in working_hours
    )

    if not fits_working_hours:
        raise ValidationError({
            "start_at": "The appointment must fall within the doctor's working hours."
        })


def validate_no_overlap(doctor, start_at, end_at, exclude_appointment_id=None):
    appointments = Appointment.objects.filter(
        doctor=doctor,
        status=Appointment.Status.BOOKED,
        start_at__lt=end_at,
        end_at__gt=start_at,
    )

    if exclude_appointment_id is not None:
        appointments = appointments.exclude(id=exclude_appointment_id)

    if appointments.exists():
        raise ValidationError({
            "start_at": "This appointment slot is already taken."
        })


@transaction.atomic
def create_appointment(*, doctor, patient, start_at, end_at):
    validate_appointment_time(start_at, end_at)
    validate_doctor_working_hours(doctor, start_at, end_at)
    validate_no_overlap(doctor, start_at, end_at)

    return Appointment.objects.create(
        doctor=doctor,
        patient=patient,
        start_at=start_at,
        end_at=end_at,
    )


@transaction.atomic
def cancel_appointment(*, appointment_id, reason):
    appointment = Appointment.objects.select_for_update().get(
        id=appointment_id
    )

    if appointment.status == Appointment.Status.CANCELLED:
        raise ValidationError({
            "status": "This appointment has already been cancelled."
        })

    appointment.status = Appointment.Status.CANCELLED
    appointment.cancellation_reason = reason.strip()
    appointment.save(
        update_fields=[
            "status",
            "cancellation_reason",
            "updated_at",
        ]
    )

    return appointment


@transaction.atomic
def reschedule_appointment(
    *,
    appointment_id,
    start_at,
    end_at,
):
    appointment = Appointment.objects.select_for_update().get(
        id=appointment_id
    )

    if appointment.status == Appointment.Status.CANCELLED:
        raise ValidationError({
            "status": "A cancelled appointment cannot be rescheduled."
        })

    validate_appointment_time(start_at, end_at)
    validate_doctor_working_hours(
        appointment.doctor,
        start_at,
        end_at,
    )
    validate_no_overlap(
        appointment.doctor,
        start_at,
        end_at,
        exclude_appointment_id=appointment.id,
    )

    appointment.start_at = start_at
    appointment.end_at = end_at
    appointment.save(update_fields=["start_at", "end_at", "updated_at"])

    return appointment
