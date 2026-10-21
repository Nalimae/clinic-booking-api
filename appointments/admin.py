from django.contrib import admin
from .models import Doctor, Patient, WorkingHours, Appointment


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "is_active")
    search_fields = ("name", "email")
    list_filter = ("is_active",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone")
    search_fields = ("name", "email")


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ("doctor", "weekday", "start_time", "end_time")
    list_filter = ("weekday", "doctor")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "patient",
        "start_at",
        "end_at",
        "status",
    )
    list_filter = ("status", "doctor")
    search_fields = ("doctor__name", "patient__name")