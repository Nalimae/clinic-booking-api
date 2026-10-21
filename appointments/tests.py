
from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Appointment, Doctor, Patient, WorkingHours


class AppointmentAPITests(TestCase):
    def setUp(self):
        # Create reusable test records for each test.
        self.client = APIClient()

        self.doctor = Doctor.objects.create(
            name="Dr. Test",
            email="doctor@example.com",
            is_active=True,
        )

        self.patient = Patient.objects.create(
            name="Test Patient",
            email="patient@example.com",
            phone="0700000000",
        )

        # Give the doctor working hours for the test date.
        self.booking_date = timezone.localdate() + timedelta(days=2)

        WorkingHours.objects.create(
            doctor=self.doctor,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        # Choose a slot at 10:00 local time.
        naive_start = datetime.combine(
            self.booking_date,
            time(10, 0),
        )
        self.start_at = timezone.make_aware(
            naive_start,
            timezone.get_current_timezone(),
        )
        self.end_at = self.start_at + timedelta(minutes=30)

    def booking_payload(self, start_at=None, end_at=None):
        # Format timestamps as ISO 8601 for the REST API.
        return {
            "doctor": self.doctor.id,
            "patient": self.patient.id,
            "start_at": (start_at or self.start_at).isoformat(),
            "end_at": (end_at or self.end_at).isoformat(),
        }

    def test_successful_booking(self):
        response = self.client.post(
            "/api/appointments/",
            self.booking_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(
            response.data["status"],
            Appointment.Status.BOOKED,
        )

    def test_rejects_appointment_within_one_hour(self):
        start_at = timezone.now() + timedelta(minutes=30)
        end_at = start_at + timedelta(minutes=30)

        response = self.client.post(
            "/api/appointments/",
            self.booking_payload(start_at, end_at),
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_rejects_overlapping_booking(self):
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        response = self.client.post(
            "/api/appointments/",
            self.booking_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_cancellation_requires_reason(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        response = self.client.patch(
            f"/api/appointments/{appointment.id}/cancel/",
            {"reason": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_cancelled_appointment_cannot_be_rescheduled(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=self.start_at,
            end_at=self.end_at,
            status=Appointment.Status.CANCELLED,
            cancellation_reason="Patient unavailable",
        )

        new_start = self.start_at + timedelta(hours=1)
        new_end = new_start + timedelta(minutes=30)

        response = self.client.patch(
            f"/api/appointments/{appointment.id}/reschedule/",
            {
                "start_at": new_start.isoformat(),
                "end_at": new_end.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_availability_returns_slots(self):
        response = self.client.get(
            f"/api/doctors/{self.doctor.id}/availability/",
            {"date": self.booking_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            len(response.data["available_slots"]) > 0
        )

    def test_rejects_booking_outside_working_hours(self):
        # 17:00 is the end of the doctor's working day.
        start_at = timezone.make_aware(
            datetime.combine(
                self.booking_date,
                time(17, 0),
            ),
            timezone.get_current_timezone(),
        )
        end_at = start_at + timedelta(minutes=30)

        response = self.client.post(
            "/api/appointments/",
            self.booking_payload(start_at, end_at),
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_successful_cancellation(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        response = self.client.patch(
            f"/api/appointments/{appointment.id}/cancel/",
            {"reason": "Patient requested cancellation"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        appointment.refresh_from_db()
        self.assertEqual(
            appointment.status,
            Appointment.Status.CANCELLED,
        )
        self.assertEqual(
            appointment.cancellation_reason,
            "Patient requested cancellation",
        )

    def test_successful_rescheduling(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        # Move the appointment from 10:00 to 11:00.
        new_start = self.start_at + timedelta(hours=1)
        new_end = new_start + timedelta(minutes=30)

        response = self.client.patch(
            f"/api/appointments/{appointment.id}/reschedule/",
            {
                "start_at": new_start.isoformat(),
                "end_at": new_end.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        appointment.refresh_from_db()
        self.assertEqual(appointment.start_at, new_start)
        self.assertEqual(appointment.end_at, new_end)
        self.assertEqual(
            appointment.status,
            Appointment.Status.BOOKED,
        )

    def test_cannot_cancel_appointment_twice(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        first_response = self.client.patch(
            f"/api/appointments/{appointment.id}/cancel/",
            {"reason": "Patient requested cancellation"},
            format="json",
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.patch(
            f"/api/appointments/{appointment.id}/cancel/",
            {"reason": "Trying to cancel again"},
            format="json",
        )
        self.assertEqual(second_response.status_code, 400)

    def test_rejects_rescheduling_to_occupied_slot(self):
        appointment_one = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        occupied_start = self.start_at + timedelta(hours=1)
        occupied_end = occupied_start + timedelta(minutes=30)

        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=occupied_start,
            end_at=occupied_end,
        )

        response = self.client.patch(
            f"/api/appointments/{appointment_one.id}/reschedule/",
            {
                "start_at": occupied_start.isoformat(),
                "end_at": occupied_end.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_rescheduling_frees_original_slot(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        new_start = self.start_at + timedelta(hours=1)
        new_end = new_start + timedelta(minutes=30)

        response = self.client.patch(
            f"/api/appointments/{appointment.id}/reschedule/",
            {
                "start_at": new_start.isoformat(),
                "end_at": new_end.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        availability_response = self.client.get(
            f"/api/doctors/{self.doctor.id}/availability/",
            {"date": self.booking_date.isoformat()},
        )

        self.assertEqual(availability_response.status_code, 200)

        available_slots = {
            (
                datetime.fromisoformat(slot)
                if isinstance(slot, str)
                else slot
                )
                for slot in availability_response.data["available_slots"]
                }
        self.assertIn(self.start_at, available_slots)
        self.assertNotIn(new_start, available_slots)
