
from django.db import migrations, models
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField
from django.contrib.postgres.fields.ranges import RangeOperators
from django.db.models import F, Func, Q, Value


def add_postgresql_constraints(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    schema_editor.execute("""
        ALTER TABLE appointments_appointment
        ADD CONSTRAINT no_overlapping_doctor_appointments
        EXCLUDE USING GIST (
            doctor_id WITH =,
            TSTZRANGE(start_at, end_at, '[)') WITH &&
        )
        WHERE (status = 'booked')
    """)

    schema_editor.execute("""
        ALTER TABLE appointments_appointment
        ADD CONSTRAINT no_overlapping_patient_appointments
        EXCLUDE USING GIST (
            patient_id WITH =,
            TSTZRANGE(start_at, end_at, '[)') WITH &&
        )
        WHERE (status = 'booked')
    """)


def remove_postgresql_constraints(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute("""
        ALTER TABLE appointments_appointment
        DROP CONSTRAINT IF EXISTS no_overlapping_patient_appointments
    """)

    schema_editor.execute("""
        ALTER TABLE appointments_appointment
        DROP CONSTRAINT IF EXISTS no_overlapping_doctor_appointments
    """)


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_postgresql_constraints,
                    remove_postgresql_constraints,
                ),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="appointment",
                    constraint=ExclusionConstraint(
                        name="no_overlapping_doctor_appointments",
                        expressions=[
                            ("doctor", RangeOperators.EQUAL),
                            (
                                Func(
                                    F("start_at"),
                                    F("end_at"),
                                    Value("[)"),
                                    function="TSTZRANGE",
                                    output_field=DateTimeRangeField(),
                                ),
                                RangeOperators.OVERLAPS,
                            ),
                        ],
                        condition=Q(status="booked"),
                    ),
                ),
                migrations.AddConstraint(
                    model_name="appointment",
                    constraint=ExclusionConstraint(
                        name="no_overlapping_patient_appointments",
                        expressions=[
                            ("patient", RangeOperators.EQUAL),
                            (
                                Func(
                                    F("start_at"),
                                    F("end_at"),
                                    Value("[)"),
                                    function="TSTZRANGE",
                                    output_field=DateTimeRangeField(),
                                ),
                                RangeOperators.OVERLAPS,
                            ),
                        ],
                        condition=Q(status="booked"),
                    ),
                ),
            ],
        ),
    ]
