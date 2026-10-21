
from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,OpenApiExample
)

from .models import Appointment, Doctor, Patient, WorkingHours
from .serializers import (
    AppointmentSerializer,
    BookingSerializer,
    CancellationSerializer,
    RescheduleSerializer,
    AvailabilityResponseSerializer,
)


from .services import (
    create_appointment,
    cancel_appointment,
    reschedule_appointment,
)



@extend_schema(
    request=BookingSerializer,
    responses={201: AppointmentSerializer},
    description="Book a 30-minute appointment with a doctor.",
    examples=[
        OpenApiExample(
            name="Appointment in Nairobi time",
            value={
                "doctor": 1,
                "patient": 1,
                "start_at": "2026-10-22T13:00:00+03:00",
                "end_at": "2026-10-22T13:30:00+03:00",
            },
            request_only=True,
        ),
    ],
)
@api_view(["POST"])
def book_appointment(request):
    serializer = BookingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    appointment = create_appointment(**serializer.validated_data)

    return Response(
        AppointmentSerializer(appointment).data,
        status=status.HTTP_201_CREATED,
    )

#Check doctor availability
@extend_schema(
    parameters=[
        OpenApiParameter(
            name="date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Date to check, in YYYY-MM-DD format.",
        )
    ],
    responses={200: AvailabilityResponseSerializer},
    description="List available 30-minute slots for a doctor on a given date.",
)
@api_view(["GET"])
def doctor_availability(request, doctor_id):
    doctor = get_object_or_404(
        Doctor,
        id=doctor_id,
        is_active=True,
    )

    date_string = request.query_params.get("date")

    if not date_string:
        return Response(
            {"date": "This query parameter is required (YYYY-MM-DD)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        requested_date = datetime.strptime(
            date_string, "%Y-%m-%d"
        ).date()
    except ValueError:
        return Response(
            {"date": "Use the YYYY-MM-DD format."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if requested_date < timezone.localdate():
        return Response(
            {"date": "Availability cannot be requested for a past date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    weekday = requested_date.weekday()
    schedules = WorkingHours.objects.filter(
        doctor=doctor,
        weekday=weekday,
    )

    now = timezone.now()
    minimum_start = now + timedelta(hours=1)
    available_slots = []

    for schedule in schedules:
        slot_start = datetime.combine(
            requested_date,
            schedule.start_time,
        )

        while slot_start + timedelta(minutes=30) <= datetime.combine(
    requested_date,
    schedule.end_time,
):
                       
            slot_end = slot_start + timedelta(minutes=30)

            aware_start = timezone.make_aware(
                slot_start,
                timezone.get_current_timezone(),
            )
            aware_end = timezone.make_aware(
                slot_end,
                timezone.get_current_timezone(),
            )

            if aware_start >= minimum_start:
                is_taken = Appointment.objects.filter(
                    doctor=doctor,
                    status=Appointment.Status.BOOKED,
                    start_at__lt=aware_end,
                    end_at__gt=aware_start,
                ).exists()

                if not is_taken:
                    available_slots.append({
                        "start_at": aware_start.isoformat(),
                        "end_at": aware_end.isoformat(),
                    })

            slot_start = slot_end

    return Response({
        "doctor_id": doctor.id,
        "date": requested_date.isoformat(),
        "available_slots": available_slots,
    })

#Cancel an appointment
@extend_schema(
    request=CancellationSerializer,
    responses={200: AppointmentSerializer},
    description="Cancel an appointment and record the cancellation reason.",
)
@api_view(["PATCH"])
def cancel_appointment_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
    )

    serializer = CancellationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    appointment = cancel_appointment(
        appointment_id=appointment.id,
        reason=serializer.validated_data["reason"],
    )

    return Response(AppointmentSerializer(appointment).data)


#Reschedule an appointment
@extend_schema(
    request=RescheduleSerializer,
    responses={200: AppointmentSerializer},
    description="Reschedule an existing appointment to an available slot.",
    examples=[
        OpenApiExample(
            name="Reschedule in Nairobi time",
            value={
                "start_at": "2026-10-22T14:00:00+03:00",
                "end_at": "2026-10-22T14:30:00+03:00",
            },
            request_only=True,
        ),
    ],
)
@api_view(["PATCH"])
def reschedule_appointment_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
    )

    serializer = RescheduleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    appointment = reschedule_appointment(
        appointment_id=appointment.id,
        **serializer.validated_data,
    )

    return Response(AppointmentSerializer(appointment).data)

#List a patient's upcoming appointments
@extend_schema(
    responses={200: AppointmentSerializer(many=True)},
    description="List a patient's upcoming booked appointments, ordered by start time.",
)
@api_view(["GET"])
def patient_upcoming_appointments(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    appointments = Appointment.objects.filter(
        patient=patient,
        status=Appointment.Status.BOOKED,
        start_at__gte=timezone.now(),
    ).select_related("doctor", "patient").order_by("start_at")

    return Response(AppointmentSerializer(
        appointments, many=True
    ).data)
