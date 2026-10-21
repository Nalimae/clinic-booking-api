
from django.urls import path

from . import views

urlpatterns = [
    path(
        "appointments/",
        views.book_appointment,
        name="book-appointment",
    ),
    path(
        "appointments/<int:appointment_id>/cancel/",
        views.cancel_appointment_view,
        name="cancel-appointment",
    ),
    path(
        "appointments/<int:appointment_id>/reschedule/",
        views.reschedule_appointment_view,
        name="reschedule-appointment",
    ),
    path(
        "doctors/<int:doctor_id>/availability/",
        views.doctor_availability,
        name="doctor-availability",
    ),
    path(
        "patients/<int:patient_id>/appointments/",
        views.patient_upcoming_appointments,
        name="patient-upcoming-appointments",
    ),
]
