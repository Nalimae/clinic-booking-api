Clinic Appointment Booking API

1.	Project Overview
The Clinic Appointment Booking API is a RESTful backend application that is designed for a small clinic with five doctors. 
The API system helps patients to view available appointment slots for a doctor on a particular date, book appointments in 30-minute intervals, cancel appointments with a reason, and also reschedule existing appointments. 
In this system, it must validate the working hours of doctors, prevent bookings in the past, and prevent multiple patients from booking overlapping appointments with the same doctor. 
The initial implementation leverages Django and Django REST Framework, with PostgreSQL as the required production database. The design of the system considers correctness, maintainability, and the ability to support future growth. 
2.	 Technology Stack
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


3.	 System Architecture
The application will adopt a modular monolithic architecture. This means that the API, business logic, and data models will stay in one Django project while still separated by responsibility. 
API Layer
The Django REST Framework views will accept HTTP requests, trigger right business logic, and return responses with correct HTTP status codes. 
URL Routing
The Django URL configurations will map API endpoints to their corresponding views. 
Serialization and Validation
Serializers will be used to validate request data including doctor and patient identifiers, appointment dates, cancellation reasons and times. The business-specific validation will be managed by the booking service. 
Business Logic Layer
A dedicated booking service will execute appointment creation, availability checks, cancellation, and rescheduling. Shared validation rules will help uphold consistency across endpoints. 
Data Layer
Django models and the Django ORM will represent and manage the application’s data. Django migrations help track database schema changes. 
Database Layer
PostgreSQL will store application records and enforce data-integrity constraints. Database transactions and conflict-prevention constraints will safeguard against simultaneous booking attempts. 

4. Data Models
The initial design identifies four core models.
4.1 Doctor
Represents a doctor working at the clinic.
Fields:
•	id: Primary key.
•	name: Doctor's name.
•	email: Unique email address.
•	is_active: Indicates whether the doctor can accept appointments.
Relationships:
•	One doctor can have multiple working-hour records.
•	One doctor can have multiple appointments.
4.2 Patient
Represents a patient using the booking system.
Fields:
•	id: Primary key.
•	name: Patient's name.
•	email: Contact email.
•	phone: Contact phone number.
Relationships:
One patient can have multiple appointments.
4.3 Working Hours
Details a doctor’s recurring working schedule.
Fields:
•	id: Primary key.
•	doctor: Foreign key referencing Doctor.
•	weekday: Day of the week.
•	start_time: Beginning of the working period.
•	end_time: End of the working period.
The working hours will be stored separately from appointments so that doctors may have different schedules.
4.4 Appointment
Represents a patient's reservation with a doctor.
Fields:
•	id: Primary key.
•	doctor: Foreign key referencing Doctor.
•	patient: Foreign key referencing Patient.
•	start_at: Appointment start timestamp.
•	end_at: Appointment end timestamp.
•	status: Either booked or cancelled.
•	cancellation_reason: Optional reason for cancellation.
•	created_at: Record creation timestamp.
•	updated_at: Last modification timestamp.
Each appointment will last exactly 30 minutes. Appointment timestamps will be timezone-aware, and clinic’s timezone will be useful when interpreting working hours. 
Cancelled appointments will be kept for historical purposes but will not block their former time slots. 
5. Relationships Between Models
•	A Doctor has many WorkingHours records.
•	A Doctor has many Appointments.
•	A Patient has many Appointments.
•	Each Appointment belongs to one Doctor and one Patient.
•	Each WorkingHours record belongs to one Doctor.
The design separates patient information, doctor schedules, and appointment records to eliminate duplication and make the system easier to maintain. 
6. Business Rules
i.	Only active doctors can accept new appointments.
ii.	Each appointment must start at a valid 30-minute slot boundary.
iii.	Appointments must fall entirely within the doctor's working hours.
iv.	Appointments must not be in the past.
v.	The bonus requirement will prevent bookings starting less than one hour from the current time.
vi.	A doctor cannot have overlapping active appointments.
vii.	Cancelling an appointment makes its slot available again.
viii.	Attempting to cancel an already cancelled appointment returns a conflict response.
ix.	Cancelled appointments cannot be rescheduled.
x.	Rescheduling must validate the new slot using the same rules as a new booking.
xi.	A failed rescheduling operation must leave the original appointment unchanged.
xii.	Upcoming patient appointments must be returned in ascending order of start time.
7. API Design
Book an appointment
POST /appointments
Validates the doctor, patient, appointment time, working hours, and availability before creating a booking.
Check doctor availability
GET /doctors/{id}/availability?date=YYYY-MM-DD
Returns available 30-minute appointment slots for the selected doctor and date.
Cancel an appointment
PATCH /appointments/{id}/cancel
Accepts a cancellation reason, marks the appointment as cancelled, and releases the slot.
Reschedule an appointment
PATCH /appointments/{id}/reschedule
Validates a replacement slot and updates the existing appointment. The operation must be atomic so that a failed reschedule does not lose the original booking.
Retrieve upcoming patient appointments
GET /patients/{id}/appointments
Returns upcoming active appointments ordered by start time. 

8. Concurrency and Double-Booking Prevention
Checking whether a slot is available before saving a booking is not sufficient because two requests may attempt to reserve the same time simultaneously.
The implementation will use database transactions and a PostgreSQL constraint that prevents overlapping active appointment time ranges for the same doctor.
The right approach is a PostgreSQL range exclusion constraint combined with the doctor identifier, using the btree_gist extension where required.
Conflicts of database will be handled gracefully and translated into meaningful API error responses. This will ensure that the booking integrity does not rely only on application-level availability checks. 
9. Error Handling
The API will return meaningful error messages with appropriate HTTP status codes.
•	200 OK: Successful retrieval, cancellation, or rescheduling.
•	201 Created: Appointment successfully booked.
•	400 Bad Request: Invalid business parameters.
•	404 Not Found: Requested doctor, patient, or appointment does not exist.
•	409 Conflict: Appointment slot is occupied or an appointment is already cancelled.
•	500 Internal Server Error: Unexpected server-side failure.
Request-schema validation errors will use the status codes configured by Django REST Framework. Internal exception details and sensitive configuration values will not be exposed to API clients.
10. Testing Phase
Automated tests will verify:
•	Successful appointment booking.
•	Booking outside working hours.
•	Booking in the past and within the one-hour restriction.
•	Booking an already occupied slot.
•	Availability before and after booking.
•	Concurrent attempts to book overlapping slots.
•	Successful cancellation and reuse of the released slot.
•	Attempting to cancel an already cancelled appointment.
•	Successful rescheduling.
•	Rescheduling into an occupied or invalid slot.
•	Attempting to reschedule a cancelled appointment.
•	Upcoming patient appointments returned in the correct order.
•	Tests will use an isolated test database and controlled timestamps wherever practical.
11. Key Design Decisions and Trade-offs
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

12. Deployment and CI/CD Plan
The application will be deployed to a cloud hosting provider with PostgreSQL configured through environment variables. 
GitHub Actions will run automated tests on pull requests targeting the designated deployment branch. After approved changes are merged and required checks pass, deployment will be triggered automatically.
13. AI Reflection
AI usage: Describe how AI tools were used during system design, implementation, testing, and documentation.
Helpful AI suggestion: Provide an actual prompt, describe the suggestion, and explain how it improved the implementation.
Incorrect or incomplete AI output: Describe a real example, how it was identified, and how the solution was corrected.
Independent decisions: Identify two decisions made independently and explain the technical reasoning behind them.
