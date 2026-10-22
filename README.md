# Clinic Appointment Booking API


## Project Overview

The Clinic Appointment Booking API is a RESTful backend application that is designed for a small clinic with five doctors.

The API system helps patients to view available appointment slots for a doctor on a particular date, book appointments in 30-minute intervals, cancel appointments with a reason, and also reschedule existing appointments.

In this system, it must validate the working hours of doctors, prevent bookings in the past, and prevent multiple patients from booking overlapping appointments with the same doctor.

The initial implementation leverages Django and Django REST Framework, with PostgreSQL as the required production database. The design of the system considers correctness, maintainability, and the ability to support future growth.


## Technology Stack

Backend framework: Django

REST API framework: Django REST Framework

Database: PostgreSQL

Database access: Django ORM

Database migrations: Django migrations

Testing: Django TestCase and Django REST Framework API testing utilities

API documentation: drf-spectacular

Version control: Git and GitHub

Deployment: Render or another suitable cloud provider

CI/CD: GitHub Actions


## System Architecture

The application will adopt a modular monolithic architecture. This means that the API, business logic, and data models will stay in one Django project while still separated by responsibility.


### API Layer

The Django REST Framework views will accept HTTP requests, trigger right business logic, and return responses with correct HTTP status codes.


### URL Routing

The Django URL configurations will map API endpoints to their corresponding views.


### Serialization and Validation

Serializers will be used to validate request data including doctor and patient identifiers, appointment dates, cancellation reasons and times. The business-specific validation will be managed by the booking service.


### Business Logic Layer

A dedicated booking service will execute appointment creation, availability checks, cancellation, and rescheduling. Shared validation rules will help uphold consistency across endpoints.


### Data Layer

Django models and the Django ORM will represent and manage the application’s data. Django migrations help track database schema changes.


### Database Layer

PostgreSQL will store application records and enforce data-integrity constraints. Database transactions and conflict-prevention constraints will safeguard against simultaneous booking attempts.


## 4. Data Models

The initial design identifies four core models.


### 4.1 Doctor

Represents a doctor working at the clinic.

Fields:

- id: Primary key.

- name: Doctor's name.

- email: Unique email address.

- is_active: Indicates whether the doctor can accept appointments.

Relationships:

- One doctor can have multiple working-hour records.

- One doctor can have multiple appointments.


### 4.2 Patient

Represents a patient using the booking system.

Fields:

- id: Primary key.

- name: Patient's name.

- email: Contact email.

- phone: Contact phone number.

Relationships:

One patient can have multiple appointments.


### 4.3 Working Hours

Details a doctor’s recurring working schedule.

Fields:

- id: Primary key.

- doctor: Foreign key referencing Doctor.

- weekday: Day of the week.

- start_time: Beginning of the working period.

- end_time: End of the working period.

The working hours will be stored separately from appointments so that doctors may have different schedules.


### 4.4 Appointment

Represents a patient's reservation with a doctor.

Fields:

- id: Primary key.

- doctor: Foreign key referencing Doctor.

- patient: Foreign key referencing Patient.

- start_at: Appointment start timestamp.

- end_at: Appointment end timestamp.

- status: Either booked or cancelled.

- cancellation_reason: Optional reason for cancellation.

- created_at: Record creation timestamp.

- updated_at: Last modification timestamp.

Each appointment will last exactly 30 minutes. Appointment timestamps will be timezone-aware, and clinic’s timezone will be useful when interpreting working hours.

Cancelled appointments will be kept for historical purposes but will not block their former time slots.


## 5. Relationships Between Models

- A Doctor has many WorkingHours records.

- A Doctor has many Appointments.

- A Patient has many Appointments.

- Each Appointment belongs to one Doctor and one Patient.

- Each WorkingHours record belongs to one Doctor.

The design separates patient information, doctor schedules, and appointment records to eliminate duplication and make the system easier to maintain.


## 6. Business Rules

- Only active doctors can accept new appointments.

- Each appointment must start at a valid 30-minute slot boundary.

- Appointments must fall entirely within the doctor's working hours.

- Appointments must not be in the past.

- The bonus requirement will prevent bookings starting less than one hour from the current time.

- A doctor cannot have overlapping active appointments.

- Cancelling an appointment makes its slot available again.

- Attempting to cancel an already cancelled appointment returns a conflict response.

- Cancelled appointments cannot be rescheduled.

- Rescheduling must validate the new slot using the same rules as a new booking.

- A failed rescheduling operation must leave the original appointment unchanged.

- Upcoming patient appointments must be returned in ascending order of start time.


## 7. API Design


### Book an appointment

POST /appointments

Validates the doctor, patient, appointment time, working hours, and availability before creating a booking.


### Check doctor availability

GET /doctors/{id}/availability?date=YYYY-MM-DD

Returns available 30-minute appointment slots for the selected doctor and date.


### Cancel an appointment

PATCH /appointments/{id}/cancel

Accepts a cancellation reason, marks the appointment as cancelled, and releases the slot.


### Reschedule an appointment

PATCH /appointments/{id}/reschedule

Validates a replacement slot and updates the existing appointment. The operation must be atomic so that a failed reschedule does not lose the original booking.


### Retrieve upcoming patient appointments

GET /patients/{id}/appointments

Returns upcoming active appointments ordered by start time.


### Application components

- Models (appointments/models.py): Define database entities, relationships, indexes, and database-level constraints.

- Serializers: Validate incoming API data and format API responses.

- Views (appointments/views.py): Handle HTTP requests, validate request payloads, and return responses.

- Services (appointments/services.py): Encapsulate appointment booking, cancellation, rescheduling, and business validation.

- URLs (appointments/urls.py and config/urls.py): Route API requests and expose the API documentation.

- Migrations (appointments/migrations/): Track and apply database schema changes.

- Automated tests (appointments/tests.py): Verify appointment functionality and business rules.

The live Swagger documentation to inspect the exact request schemas, parameters, and response formats: https://clinic-booking-api-zt56.onrender.com/api/docs/


### Example: Book an appointment

```text
POST /api/appointments/
```

Example request body:

```json
{
"doctor": 1,
"patient": 1,
"start_at": "2026-10-23T14:00:00+03:00",
"end_at": "2026-10-23T14:30:00+03:00"
}
```

The doctor and patient IDs must exist, and the requested slot must satisfy all booking rules.

A successful booking returns HTTP 201 Created.


### Example: Cancel an appointment

```text
PATCH /api/appointments/1/cancel/
```

Example request body:

```json
{
"reason": "Patient requested cancellation"
}
```

A successful cancellation updates the appointment status and records the reason. Cancelled appointments remain in the database for history and auditing.


### Example: Reschedule an appointment

```text
PATCH /api/appointments/1/reschedule/
```

Example request body:

```json
{
"start_at": "2026-10-23T15:00:00+03:00",
"end_at": "2026-10-23T15:30:00+03:00"
}
```

The requested time is validated using the same core rules as a new booking. The original appointment time is excluded from overlap checks so an appointment can be rescheduled without conflicting with itself.

8. Concurrency and Double-Booking Prevention

Checking whether a slot is available before saving a booking is not sufficient because two requests may attempt to reserve the same time simultaneously.

The implementation will use database transactions and a PostgreSQL constraint that prevents overlapping active appointment time ranges for the same doctor.

The right approach is a PostgreSQL range exclusion constraint combined with the doctor identifier, using the btree_gist extension where required.

Conflicts of database will be handled gracefully and translated into meaningful API error responses. This will ensure that the booking integrity does not rely only on application-level availability checks.


## 9. Error Handling

The API will return meaningful error messages with appropriate HTTP status codes.

- 200 OK: Successful retrieval, cancellation, or rescheduling.

- 201 Created: Appointment successfully booked.

- 400 Bad Request: Invalid business parameters.

- 404 Not Found: Requested doctor, patient, or appointment does not exist.

- 409 Conflict: Appointment slot is occupied or an appointment is already cancelled.

- 500 Internal Server Error: Unexpected server-side failure.

Request-schema validation errors will use the status codes configured by Django REST Framework. Internal exception details and sensitive configuration values will not be exposed to API clients.


## 10. Testing Phase

Automated tests will verify:

- Successful appointment booking.

- Booking outside working hours.

- Booking in the past and within the one-hour restriction.

- Booking an already occupied slot.

- Availability before and after booking.

- Concurrent attempts to book overlapping slots.

- Successful cancellation and reuse of the released slot.

- Attempting to cancel an already cancelled appointment.

- Successful rescheduling.

- Rescheduling into an occupied or invalid slot.

- Attempting to reschedule a cancelled appointment.

- Upcoming patient appointments returned in the correct order.

- Tests will use an isolated test database and controlled timestamps wherever practical.


## 11. Key Design Decisions and Trade-offs

Django REST Framework

I selected the Django REST Framework because it integrates easily with the Django’s ORM, serializers, migrations, and testing ecosystem. FastAPI is an ideal choice, but Django offers a cohesive structure for this application.

PostgreSQL

I chose PostgreSQL for production because it supports transactions and complex constraints for preventing conflicting appointments. SQLite is ideal for local development but does not offer the same PostgreSQL-specific protections.

Retaining Cancelled Appointments

Cancelled appointments will be stored in the database to maintain history and aid auditing. The trade-off is that queries must explicitly exclude cancelled appointments when computing availability.

Dynamic Availability Calculation

Availability will be determined from working hours and existing active appointments instead of being stored on a different availability table. This will help avoid redundant data, and availability queries may need to be optimized as usage increases.

Modular Monolith

The application will be a one Django project with separate responsibilities. This will help reduce deployment and maintenance challenges compared with microservices, which are not necessary for the initial clinic size.

Database-Level Conflict Prevention

Database constraints will protect against conflicting bookings even when simultaneous requests pass the initial application checks. While this may increase implementation complexity, it is great for reliable appointment scheduling.


## Database and Migrations

Django ORM manages database access and schema changes.

Apply migrations with:

```powershell
python manage.py migrate
```

The production database uses PostgreSQL. The migration for overlap protection creates the required PostgreSQL constraints and skips those database-specific operations on other database engines.


## Local Setup


### Prerequisites

Python 3.12 or a compatible Python version supported by the dependencies

Git

A PostgreSQL database for PostgreSQL-specific testing, or a locally configured database supported by the project settings

1. Clone the repository

```powershell
git clone https://github.com/Nalimae/clinic-booking-api.git
cd clinic-booking-api
```

2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Configure environment variables

Create a local .env file using the variable names expected by config/settings.py.

Configure the Django secret key, debug setting, allowed hosts, and database connection as required by the project settings. Use local development values for local development and production values in the hosting provider's environment configuration.

Never commit .env, production credentials, or secret keys to GitHub.

5. Apply migrations

```powershell
python manage.py migrate
```

6. Run the application

```powershell
python manage.py runserver
```

Open the local API documentation:

```text
http://127.0.0.1:8000/api/docs/
```


## Testing

Run the automated test suite with:

```powershell
python manage.py test appointments
```

Run Django's configuration checks with:

```powershell
python manage.py check
```

Check that model changes have corresponding migrations:

```powershell
python manage.py makemigrations --check --dry-run
```

The test suite has completed successfully with 12 passing tests during development.

Testing covers appointment API behavior and business rules. The live deployment and PostgreSQL overlap constraints were also checked during development.


## 12. Deployment and CI/CD Plan


### GitHub Actions

The repository uses GitHub Actions to install dependencies and run automated checks and tests.

Workflow configuration:

```text
.github/workflows/tests.yml
```

The workflow is meant to identify regressions before changes are accepted.


### Render deployment

The application is deployed as a public web service on Render.

Public URL: https://clinic-booking-api-zt56.onrender.com/

API documentation: https://clinic-booking-api-zt56.onrender.com/api/docs/


## Security Considerations

- Secrets are configured through environment variables rather than source code.

- Database constraints protect appointment consistency.

- Input validation enforces booking rules.

- Cancellation history is retained instead of deleting appointment records.

- The deployment should use HTTPS and appropriately configured allowed hosts.

- Authentication and role-based authorization should be implemented before exposing patient-specific data for unrestricted real-world use.


## 13. AI Reflection


### 1. What did you use AI for across the four sections?

I have used AI as a development assistant in the whole assessment, while maintaining the responsibility for implementing decisions, testing and verification.

In Section 1, I used AI to discuss Django REST Framework structure, serializers, endpoint, service layer and appointment validation rules.

In Section 2, I used AI to understand booking conflicts, appointment cancellations, rescheduling, working-hour validation, and preventing overlapping appointments.

In Section 3, I used to perform automated test failures, review GitHub Actions, and Render deployment issues, and look at PostgreSQL-specific behavior, and improve project documentation.

I considered the AI generated output as a recommendation instead of an final answer. I conducted a review of the proposed changes, applied automated tests, verified the deployed application, and monitored database behavior before trusting the results.


### 2. An example where an AI suggestion improved your work. What did you prompt it with?

A useful example where AI suggestion improved the work is in the appointment conflict protection. The initial availability check identified an existing booking, but concurrent requests could not maintain the same slot before either request is completed. AI was used to enhance this design through PostgreSQL exclusion constraints, transactions, and appropriate conflict handling.

Example prompt:

"How can I prevent overlapping appointments for the same doctor and patient in a Django REST Framework API, including concurrent booking requests? Explain how PostgreSQL exclusion constraints, transactions, and API conflict responses can work together.

The suggestion by the AI allowed me to apply data-base level overlap protection besides the application-level validation. I confirmed that the deployed PostgreSQL database contained the expected constraints and ran the automated test suite.


### 3. Give one example where AI output was wrong or incomplete and how you caught it.

This happened when dealing with database-specific constraints and migrations. A migration that works with PostgreSQL exclusion constraints cannot be assumed that it will work identically with SQLite, which does not offer equivalent exclusion-constraint functionality.

By running Django checks and tests locally, checking the status of migration, and verifying constraints against the deployed PostgreSQL database, it allowed me to confirm this. This revealed the need to explain the differences between the development and production database engines.

So to fix this issue, I made the migration’s database operations conditional on the active database engine while maintaining the corresponding Django migration state. Then confirmed that the migrations were updated, and verified the presence of two overlap constraints in production PostgreSQL database.


### Name two decisions you made without AI. Why did you trust your own judgment there?

- I decided to maintain cancelled appointments instead of deleting them.

I made this decision because it is important to have history, and also supports traceability. The cancelled appointments are excluded from the overlap checks, and this allows the time slots to become available again. I believe that a cancellation represents a business event, and is not a reason to delete the record.

- I decided to verify production database constraints directly.

I checked the deployed PostgreSQL database independently to confirm that the doctor and patient overlap constraints existed. I did not depend on a successful deployment message. I believed in this approach because deployment success does not mean that each migration or database protection has been correctly applied. By Querying PostgreSQL, it generated direct evidence that the intended constraints existed.
