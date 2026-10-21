
from rest_framework import serializers

from .models import Appointment, Doctor, Patient, WorkingHours


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ["id", "name", "email", "is_active"]


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ["id", "name", "email", "phone"]


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source="doctor.name",
        read_only=True,
    )
    patient_name = serializers.CharField(
        source="patient.name",
        read_only=True,
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "patient",
            "patient_name",
            "start_at",
            "end_at",
            "status",
            "cancellation_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "cancellation_reason",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        if attrs["start_at"] >= attrs["end_at"]:
            raise serializers.ValidationError({
                "end_at": "End time must be after start time."
            })

        return attrs


class BookingSerializer(serializers.Serializer):
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.filter(is_active=True)
    )
    patient = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all()
    )
    start_at = serializers.DateTimeField(
    input_formats=["iso-8601"],
    format="iso-8601",
    help_text="ISO 8601 timestamp with timezone offset, e.g. 2026-10-22T13:00:00+03:00",
)
    end_at = serializers.DateTimeField(
    input_formats=["iso-8601"],
    format="iso-8601",
    help_text="ISO 8601 timestamp with timezone offset, e.g. 2026-10-22T13:30:00+03:00",
)


class CancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(
        max_length=1000,
        allow_blank=False,
        trim_whitespace=True,
    )
    def validate_reason(self, value):
        if value.lower() == "string":
            raise serializers.ValidationError(
                "Please provide a meaningful cancellation reason."
            )
        return value


class RescheduleSerializer(serializers.Serializer):
    start_at = serializers.DateTimeField(
    input_formats=["iso-8601"],
    format="iso-8601",
    help_text="ISO 8601 timestamp with timezone offset, e.g. 2026-10-22T13:00:00+03:00",
)
    end_at = serializers.DateTimeField(
    input_formats=["iso-8601"],
    format="iso-8601",
    help_text="ISO 8601 timestamp with timezone offset, e.g. 2026-10-22T13:30:00+03:00",
)
    

class WorkingHoursSerializer(serializers.ModelSerializer):
    weekday_name = serializers.CharField(
        source="get_weekday_display",
        read_only=True,
    )

    class Meta:
        model = WorkingHours
        fields = [
            "id",
            "doctor",
            "weekday",
            "weekday_name",
            "start_time",
            "end_time",
        ]

class AvailabilityResponseSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    date = serializers.DateField()
    available_slots = serializers.ListField(
        child=serializers.DateTimeField()
    )