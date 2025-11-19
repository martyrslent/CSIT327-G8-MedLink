# ============================================================
# IMPORTS
# ============================================================
import os
from functools import wraps
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
# Note: You need to ensure 'supabase_client' provides the initialized Supabase client
from .supabase_client import supabase 
from supabase import create_client, Client # Included for completeness, often imported in supabase_client.py
from .email_utils import send_appointment_confirmation_email
# from django.urls import reverse, NoReverseMatch # Not used in these views, so removed for cleanup

# ============================================================
# ADMIN AUTHENTICATION DECORATOR
# ============================================================
def admin_required(view_func):
    """
    Decorator to restrict access to admin-only views.
    If the current session does not belong to an admin,
    redirects to login with an error message.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get("is_admin"):
            messages.error(request, "Access denied. Please log in as an administrator.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ============================================================
# CORE VIEWS
# ============================================================

def hello_page(request):
    return HttpResponse("Hello, Django Page!")

# --- ADMIN REGISTRATION PAGE (Includes staff roles) ---
@admin_required
def register_admin_page(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        role = request.POST.get("role") # NEW: Get the selected role
        
        # Basic Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "register-admin.html")
        
        if not all([first_name, last_name, email, password, role]):
            messages.error(request, "All fields (including Staff Role) are required!")
            return render(request, "register-admin.html")

        # Determine Boolean Flags based on Role
        is_doctor_flag = (role == "doctor")
        is_admin_flag = (role == "staff")
        
        table_name = "users"

        try:
            # Check for existing email
            response = supabase.table(table_name).select("email").eq("email", email).execute()
            
            if response.data and len(response.data) > 0:
                messages.error(request, "Email already registered!")
                return render(request, "register-admin.html")

            hashed_password = make_password(password)

            # Insert new user with calculated role flags
            supabase.table(table_name).insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": is_admin_flag, 
                "is_doctor": is_doctor_flag
            }).execute()

            messages.success(request, f"New {role.capitalize()} {first_name} added successfully! They can now log in.")
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Critical error during admin registration: {str(e)}")
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-admin.html")

    return render(request, "register-admin.html")


# --- APPOINTMENT REGISTRATION (Includes doctor list fetch and record creation) ---
@admin_required
def register_appointment(request):
    # 1. Fetch list of verified doctors for the dropdown menu
    doctors = []
    try:
        doctors_response = supabase.table("users").select("first_name, last_name").eq("is_doctor", True).execute()
        doctors = doctors_response.data
    except Exception as e:
        print(f"DEBUG: Could not fetch list of doctors: {e}")
        messages.warning(request, "Could not load the list of available doctors due to a database error.")
    
    context = {"doctors": doctors}

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        appointment_date = request.POST.get("appointment_date")
        doctor_name = request.POST.get("doctor_name") 
        user_email = request.POST.get("user_email")
        appointment_time = request.POST.get("appointment_time", "Not specified")

        # --- Initial Validation ---
        if not all([first_name, last_name, appointment_date, doctor_name, user_email]):
            messages.error(request, "All required fields are needed to book an appointment.")
            return render(request, "appointment_form.html", context)
        
        # --- DOCTOR VALIDATION ---
        valid_doctor_names = [f"{d['first_name']} {d['last_name']}" for d in doctors]
        if doctor_name not in valid_doctor_names:
            messages.error(request, f"'{doctor_name}' is not a registered, verified doctor. Please select a valid doctor from the list.")
            return render(request, "appointment_form.html", context)
        
        # --- 2. Find Patient ID (Foreign Key) ---
        patient_id = None
        try:
            patient_response = supabase.table("users").select("id").eq("email", user_email).single().execute()
            if patient_response.data:
                patient_id = patient_response.data.get("id")
        except Exception:
            messages.error(request, "Patient with that email was not found in the users database. Appointment not booked.")
            return render(request, "appointment_form.html", context)

        
        appointment_data = {
            "first_name": first_name,
            "last_name": last_name,
            "appointment_date": appointment_date,
            "doctor_name": doctor_name,
            "user_email": user_email,
            "patient_id": patient_id 
        }

        try:
            # --- 3. INSERT into Appointment Table ---
            response = supabase.table("appointment").insert(appointment_data).execute()
            new_appointment_data = response.data[0]
            new_appointment_id = new_appointment_data.get('id')

            # --- 4. INSERT into Patient Records Table ---
            patient_record_data = {
                "user_id": patient_id,
                "appointment_id": new_appointment_id,
                "record_date": appointment_date, 
                "successful_appointment_visit": False,
                "doctor_notes": "Appointment scheduled."
            }
            supabase.table("patient_records").insert(patient_record_data).execute()
            
            # --- 5. Trigger Email Notification ---
            try:
                full_name = f"{first_name} {last_name}"
                send_appointment_confirmation_email(
                    user_name=full_name,
                    user_email=user_email,
                    doctor_name=doctor_name,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time
                )
            except Exception as e:
                print(f"CRITICAL: Email send failed after booking: {e}")
                messages.warning(request, "Appointment saved, but email notification failed. Please check server logs.")

            messages.success(request, f"Appointment for {first_name} {last_name} on {appointment_date} successfully registered, and patient record created!")
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Critical error during appointment registration: {str(e)}")
            messages.error(request, f"An unexpected error occurred during booking: {str(e)}")
            return render(request, "appointment_form.html", context)

    return render(request, "appointment_form.html", context)

# --- LOGIN PAGE (Now complete with check_password) ---
def login_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not email or not password:
            messages.error(request, "Please fill in all fields!")
            return render(request, "login-student.html")

        try:
            # Fetch user
            response = supabase.table("users").select("*").eq("email", email).execute()

            if not response.data:
                messages.error(request, "Email not found!")
                return render(request, "login-student.html")

            user = response.data[0]

            # Check password
            if not check_password(password, user["password"]):
                messages.error(request, "Incorrect password!")
                return render(request, "login-student.html")

            # Set session
            request.session["user_id"] = user["id"]
            request.session["user_email"] = user["email"]
            request.session["is_admin"] = user.get("is_admin", False)
            request.session["first_name"] = user.get("first_name", "User")

            if user.get("is_admin", False):
                return redirect("admin_dashboard")
            else:
                return redirect("user_dashboard")

        except Exception as e:
            print(f"DEBUG: Exception occurred: {str(e)}")
            messages.error(request, f"Unexpected error: {str(e)}")
            return render(request, "login-student.html")

    return render(request, "login-student.html")


# --- ADMIN DASHBOARD ---
@admin_required
def admin_dashboard(request):
    try:
        # Get Total Patients
        user_response = supabase.table("users").select("id", count='exact').eq("is_admin", False).execute()
        total_patients = user_response.count or 0
        
        # Get Total Appointments
        appt_response = supabase.table("appointment").select("id", count='exact').execute()
        total_appointments = appt_response.count or 0

        # Get recent patients
        recent_users_response = supabase.table("users").select("*").eq("is_admin", False).order("id", desc=True).limit(5).execute()
        recent_activity = recent_users_response.data or []

        context = {
            "total_patients": total_patients,
            "total_appointments": total_appointments, 
            "recent_activity": recent_activity, 
            "new_registrations": total_patients,
        }
        return render(request, "admin_dashboard.html", context)

    except Exception as e:
        print(f"CRITICAL ERROR IN ADMIN DASHBOARD: {e}")
        messages.error(request, f"Could not load dashboard data: {e}")
        return render(request, "admin_dashboard.html", {
            "total_patients": 0,
            "total_appointments": 0,
            "recent_activity": [],
            "new_registrations": 0,
        })

# --- USER REGISTRATION (Explicitly sets is_doctor: False) ---
def register_page(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "register-student.html")

        table_name = "users"

        try:
            # Check if email already exists
            response = supabase.table(table_name).select("email").eq("email", email).execute()
            if response.data:
                messages.error(request, "Email already registered!")
                return render(request, "register-student.html")

            hashed_password = make_password(password)

            # Insert new user with explicit False flags
            supabase.table(table_name).insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": False,
                "is_doctor": False
            }).execute()

            messages.success(request, "Account created successfully! Please log in.")
            return redirect("login")

        except Exception as e:
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-student.html")

    return render(request, "register-student.html")

# --- MISC PAGES ---
def forgot_password_page(request):
    return render(request, "forgot-password.html")

def home_page(request):
    return render(request, "home.html")

def logout_page(request):
    request.session.flush()
    messages.success(request, "You have been logged out.") # Added message for better UX
    return redirect("login")


# --- USER DASHBOARD ---
def user_dashboard(request):
    if not request.session.get("user_id"):
        return redirect("login")

    try:
        user_email = request.session.get("user_email")
        first_name = request.session.get("first_name", "User")
        
        # Fetch user's appointments
        appointment_response = supabase.table("appointment").select("*").eq("user_email", user_email).order("appointment_date", desc=True).execute()
        appointments = appointment_response.data or []

        context = {
            "user_email": user_email,
            "first_name": first_name,
            "appointments": appointments
        }
        return render(request, "user-dashboard.html", context)

    except Exception as e:
        print(f"--- DEBUG: USER DASHBOARD CRASH ---")
        print(f"Error details: {e}")
        messages.error(request, f"Could not load dashboard data: {e}")
        return render(request, "user-dashboard.html", {
            "first_name": request.session.get("first_name", "User"),
            "appointments": []
        })

# --- PROFILE PAGE (New from your friend's diff) ---
def profile_page(request):
    if not request.session.get("user_id"):
        return redirect("login")

    user_email = request.session.get("user_email")

    try:
        response = supabase.table("users").select("*").eq("email", user_email).single().execute()
        user_data = response.data or {}

        full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()

        context = {
            "full_name": full_name,
            "email": user_data.get("email"),
            "age": user_data.get("age", "Not Specified"),
            "gender": user_data.get("gender", "Not Specified"),
        }

        return render(request, "profile.html", context)

    except Exception as e:
        print(f"DEBUG: Error loading profile: {e}")
        messages.error(request, "Could not load profile data.")
        return redirect("user_dashboard")


# ============================================================
# ADMIN APPOINTMENT & USER MANAGEMENT
# ============================================================

# --- APPOINTMENT LIST ---
@admin_required
def appointment_list_page(request):
    """Displays all appointments."""
    try:
        response = supabase.table("appointment").select("*").order("appointment_date", desc=False).execute()
        appointments = response.data or []
        context = {"appointments": appointments}
        return render(request, "appointments.html", context)
    except Exception as e:
        print(f"DEBUG: Error fetching appointments: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, "appointments.html", {"appointments": []})

# --- MARK APPOINTMENT COMPLETE (New from your old version) ---
@admin_required
def complete_appointment(request, appointment_id):
    if request.method == 'POST':
        try:
            # Update the 'patient_records' table
            response = supabase.table('patient_records').update({
                'successful_appointment_visit': True,
                'doctor_notes': 'Appointment completed and visit logged.'
            }).eq('appointment_id', appointment_id).execute()
            
            if response.data:
                messages.success(request, f"Appointment #{appointment_id} successfully marked as completed.")
            else:
                messages.warning(request, f"Appointment #{appointment_id} marked as completed, but the corresponding log entry was not found.")
                
        except Exception as e:
            print(f"DEBUG: Error completing appointment {appointment_id}: {str(e)}")
            messages.error(request, f"Failed to complete appointment. An unexpected error occurred: {str(e)}")
            
    return redirect("appointment_list")

# --- EDIT APPOINTMENT ---
@admin_required # Added decorator based on context
def edit_appointment(request, appointment_id):
    # Fetch list of verified doctors for the form dropdown
    doctors = []
    try:
        doctors_response = supabase.table("users").select("first_name, last_name").eq("is_doctor", True).execute()
        doctors = doctors_response.data
    except Exception as e:
        print(f"DEBUG: Could not fetch list of doctors for edit form: {e}")
    context = {"doctors": doctors}
    
    try:
        if request.method == "POST":
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            appointment_date = request.POST.get("appointment_date")
            doctor_name = request.POST.get("doctor_name")
            user_email = request.POST.get("user_email")

            if not all([first_name, last_name, appointment_date, doctor_name, user_email]):
                messages.error(request, "All fields are required!")
                # Re-fetch data for the form
                response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
                context["appointment"] = response.data
                return render(request, "edit_appointment.html", context)

            update_data = {
                "first_name": first_name,
                "last_name": last_name,
                "appointment_date": appointment_date,
                "doctor_name": doctor_name,
                "user_email": user_email
            }

            supabase.table("appointment").update(update_data).eq("id", appointment_id).execute()
            
            messages.success(request, "Appointment updated successfully!")
            return redirect("appointment_list")
        
        else:
            # GET request: Fetch existing appointment data
            response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
            if response.data:
                context["appointment"] = response.data
                return render(request, "edit_appointment.html", context)
            else:
                messages.error(request, "Appointment not found.")
                return redirect("appointment_list")

    except Exception as e:
        print(f"DEBUG: Error editing appointment {appointment_id}: {str(e)}")
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect("appointment_list")

# --- USER MANAGEMENT LIST (New from your old version) ---
@admin_required
def user_management_page(request):
    """Fetches all users, separates them into Doctors and Patients."""
    try:
        response = supabase.table("users").select("*").order("last_name", desc=False).execute()
        all_users = response.data or []

        doctors = [u for u in all_users if u.get('is_doctor') == True]
        patients = [u for u in all_users if u.get('is_doctor') == False]

        context = {
            "doctors": doctors,
            "patients": patients,
            "total_users": len(all_users)
        }
        return render(request, "user_management.html", context)
    except Exception as e:
        print(f"DEBUG: Error loading user management data: {e}")
        messages.error(request, f"Error loading user data: {e}")
        return render(request, "user_management.html", {"doctors": [], "patients": []})

# --- EDIT USER (New from your old version) ---
@admin_required
def edit_user_page(request, user_id):
    """Handles fetching user data for editing (GET) and updating user data (POST)."""
    
    # --- GET REQUEST: Display the Edit Form ---
    if request.method == 'GET':
        try:
            response = supabase.table("users").select("*").eq("id", user_id).single().execute()
            user_data = response.data
            context = {"user": user_data}
            return render(request, "user_edit.html", context)
            
        except Exception as e:
            print(f"DEBUG: Error fetching user {user_id}: {e}")
            messages.error(request, f"Could not find user data. Error: {e}. Check if user_id is valid.")
            return redirect('user_management')
            
    # --- POST REQUEST: Process the Update ---
    elif request.method == 'POST':
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            is_doctor = request.POST.get('is_doctor') == 'on'
            
            update_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "is_doctor": is_doctor
            }
            
            supabase.table("users").update(update_data).eq("id", user_id).execute()
            
            messages.success(request, f"User {first_name} {last_name} (ID: {user_id}) updated successfully.")
            return redirect('user_management')
            
        except Exception as e:
            print(f"DEBUG: Error updating user {user_id}: {e}")
            messages.error(request, f"Failed to update user. Error: {e}. Please try again.")
            
            # Re-render the edit page with an error message
            try:
                response = supabase.table("users").select("*").eq("id", user_id).single().execute()
                user_data = response.data
                context = {"user": user_data}
                return render(request, "user_edit.html", context)
            except:
                return redirect('user_management')

# --- DELETE APPOINTMENT (Includes Foreign Key fix) ---
@admin_required
def delete_appointment(request, appointment_id):
    """
    Deletes an appointment record, safely handling foreign key constraints
    by setting the reference in patient_records to NULL first.
    """
    try:
        # 1. Update patient records referencing this appointment_id to NULL
        print(f"DEBUG: Clearing FK constraint for appointment ID: {appointment_id}")
        supabase.table('patient_records').update({'appointment_id': None}).eq('appointment_id', appointment_id).execute()
        
        # 2. Safely delete the appointment.
        response = supabase.table("appointment").delete().eq("id", appointment_id).execute()
        
        if response.data:
            messages.success(request, f"Appointment #{appointment_id} deleted successfully and patient links updated.")
        else:
            messages.error(request, f"Could not find or delete appointment #{appointment_id}.")

    except Exception as e:
        error_message = str(e)
        print(f"DEBUG: Error deleting appointment {appointment_id}: {error_message}")
        messages.error(request, f"Failed to delete appointment. An unexpected error occurred: {error_message}")
    
    return redirect("appointment_list")


def book_appointment(request):
    # Security check
    if not request.session.get("user_id"):
        return redirect("login")

    if request.method == "POST":
        appointment_date = request.POST.get("appointment_date")

        if not appointment_date:
            messages.error(request, "Please select a date for your appointment.")
            return render(request, "book_appointment.html")

        try:
            user_id = request.session.get("user_id")

            user_response = supabase.table("users").select("*").eq("id", user_id).single().execute()
            user = user_response.data

            if not user:
                messages.error(request, "User not found.")
                return redirect("login")

            doctor_name = "General Practitioner"

            appointment_data = {
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "user_email": user.get("email"),
                "appointment_date": appointment_date,
                "doctor_name": doctor_name,
            }

            supabase.table("appointment").insert(appointment_data).execute()

            try:
                full_name = f"{user.get('first_name')} {user.get('last_name')}"
                send_appointment_confirmation_email(
                    user_name=full_name,
                    user_email=user.get("email"),
                    doctor_name=doctor_name,
                    appointment_date=appointment_date,
                    appointment_time="09:00 AM"
                )
            except Exception as e:
                print(f"Email error: {e}")

            messages.success(request, "Appointment booked successfully!")
            return redirect("user_dashboard")

        except Exception as e:
            print(f"Error booking appointment: {e}")
            messages.error(request, "An unexpected error occurred. Please try again.")
            return render(request, "book_appointment.html")

    return render(request, "book_appointment.html")

# --- PATIENT RECORDS LIST (New from your old version) ---
@admin_required
def patient_records_list_page(request):
    """Displays all patient records along with the patient's name using Supabase foreign key join."""
    try:
        # Use Supabase Foreign Key Join syntax: "*, user_id(first_name, last_name)"
        response = supabase.table("patient_records").select("*, user_id(first_name, last_name)").order("record_date", desc=True).execute()
        
        records = response.data or []
        
        context = {"records": records}
        return render(request, "patient_records_list.html", context)
    
    except Exception as e:
        print(f"DEBUG: Error fetching patient records: {str(e)}")
        messages.error(request, f"Could not load patient records: {str(e)}")
        return render(request, "patient_records_list.html", {"records": []})