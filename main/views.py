# --- NEW IMPORTS FOR SPRINT 3 ---
import os
from .email_utils import send_appointment_confirmation_email

# --- Existing Imports ---
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .supabase_client import supabase
from supabase import create_client, Client
from django.urls import reverse, NoReverseMatch
from functools import wraps


# ============================================================
# ADMIN AUTHENTICATION DECORATOR (Moved here to fix NameError)
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
            return redirect("login")  # Assumes your login URL is named 'login'
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ============================================================
# VIEWS
# ============================================================

def hello_page(request):
    return HttpResponse("Hello, Django Page!")

@admin_required
def register_admin_page(request):
    # Security check handled by decorator
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
        # is_admin is True for general staff, False for doctors (to keep them distinct)
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
            response = supabase.table(table_name).insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": is_admin_flag, 
                "is_doctor": is_doctor_flag  # Differentiating between roles
            }).execute()

            # Handle Supabase-specific errors if response structure includes it
            # Note: This check might need adjustment based on your Supabase client's error handling
            if isinstance(response, dict) and 'error' in response:
                error_message = f"Supabase Error: {response['error'].get('message', 'Unknown error')}"
                print(f"DEBUG: Staff insertion failed - {error_message}")
                messages.error(request, error_message)
                return render(request, "register-admin.html")

            messages.success(request, f"New {role.capitalize()} {first_name} added successfully! They can now log in.")
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Critical error during admin registration: {str(e)}")
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-admin.html")

    return render(request, "register-admin.html")


# ============================================================
# SPRINT 3 FEATURE: EMAIL NOTIFICATION
# ============================================================@admin_required
def register_appointment(request):
    # 1. Fetch list of verified doctors for the dropdown menu
    doctors = []
    try:
        # Fetching first_name and last_name, which will be concatenated for the dropdown
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

        # The doctor_name is now selected from the dropdown
        doctor_name = request.POST.get("doctor_name") 
        user_email = request.POST.get("user_email")
        appointment_time = request.POST.get("appointment_time", "Not specified")

        # --- Initial Validation ---
        if not all([first_name, last_name, appointment_date, doctor_name, user_email]):
            messages.error(request, "All required fields are needed to book an appointment.")
            return render(request, "appointment_form.html", context)
        
        # --- NEW DOCTOR VALIDATION ---
        # Ensure the selected doctor_name is actually in the list of verified doctors
        valid_doctor_names = [f"{d['first_name']} {d['last_name']}" for d in doctors]
        if doctor_name not in valid_doctor_names:
            messages.error(request, f"'{doctor_name}' is not a registered, verified doctor. Please select a valid doctor from the list.")
            return render(request, "appointment_form.html", context)
        
        # --- 1. Find Patient ID (Foreign Key) ---
        patient_id = None
        try:
            # Look up the patient's ID in the 'users' table using the email
            patient_response = supabase.table("users").select("id").eq("email", user_email).single().execute()
            if patient_response.data:
                patient_id = patient_response.data.get("id")
        except Exception:
            # If the user is not found, we can't link the record
            messages.error(request, "Patient with that email was not found in the users database. Appointment not booked.")
            return render(request, "appointment_form.html", context)

        
        appointment_data = {
            "first_name": first_name,
            "last_name": last_name,
            "appointment_date": appointment_date,
            "doctor_name": doctor_name,
            "user_email": user_email,
            "patient_id": patient_id # Link to the patient's user record
        }

        try:
            # --- 2. INSERT into Appointment Table ---
            response = supabase.table("appointment").insert(appointment_data).execute()
            
            # Assuming the Supabase client returns a dictionary with 'data' key upon successful insert
            new_appointment_data = response.data[0]
            new_appointment_id = new_appointment_data.get('id')

            # --- 3. INSERT into Patient Records Table ---
            patient_record_data = {
                "user_id": patient_id,
                "appointment_id": new_appointment_id,
                "record_date": appointment_date, 
                "successful_appointment_visit": False,
                "doctor_notes": "Appointment scheduled."
            }
            
            supabase.table("patient_records").insert(patient_record_data).execute()
            
            # --- 4. Trigger Email Notification (Your existing code) ---
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
            # --- End of Email Code ---

            messages.success(request, f"Appointment for {first_name} {last_name} on {appointment_date} successfully registered, and patient record created!")
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Critical error during appointment registration: {str(e)}")
            messages.error(request, f"An unexpected error occurred during booking: {str(e)}")
            return render(request, "appointment_form.html", context)

    # This handles the initial GET request to load the form
    return render(request, "appointment_form.html", context)

def login_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        print("DEBUG: Received POST request")
        print(f"DEBUG: email={email}, password={'*' * len(password) if password else None}")

        if not email or not password:
            messages.error(request, "Please fill in all fields!")
            return render(request, "login-student.html")

        try:
            response = supabase.table("users").select("*").eq("email", email).execute()

            if not response.data:
                messages.error(request, "Email not found!")
                return render(request, "login-student.html")

            user = response.data[0]

            if not check_password(password, user["password"]):
                messages.error(request, "Incorrect password!")
                return render(request, "login-student.html")

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


# ============================================================
# SPRINT 3 FEATURE: ADMIN PANEL UI
# ============================================================
@admin_required
def admin_dashboard(request):
    try:
        # Get Total Patients (using count for efficiency)
        user_response = supabase.table("users").select("id", count='exact').eq("is_admin", False).execute()
        total_patients = user_response.count if user_response.count is not None else 0
        
        # Get Total Appointments
        appt_response = supabase.table("appointment").select("id", count='exact').execute()
        total_appointments = appt_response.count if appt_response.count is not None else 0

        # Get recent patients
        # *** FIX APPLIED HERE: CHANGED "created_at" TO "id" ***
        recent_users_response = supabase.table("users").select("*").eq("is_admin", False).order("id", desc=True).limit(5).execute()
        # ******************************************************
        
        recent_activity = recent_users_response.data if recent_users_response.data else []

        context = {
            "total_patients": total_patients,
            "total_appointments": total_appointments, 
            "recent_activity": recent_activity, 
            "new_registrations": total_patients,
        }
        return render(request, "admin_dashboard.html", context)

    except Exception as e:
        # ... (rest of the error handling code is fine)
        print(f"CRITICAL ERROR IN ADMIN DASHBOARD: {e}")
        messages.error(request, f"Could not load dashboard data: {e}")
        return render(request, "admin_dashboard.html", {
            "total_patients": 0,
            "total_appointments": 0,
            "recent_activity": [],
            "new_registrations": 0,
        })

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

            # --- FIX: Explicitly set is_doctor to False ---
            response = supabase.table(table_name).insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": False, # General user/patient registration
                "is_doctor": False  # New users are NOT doctors by default
            }).execute()
            # --- END FIX ---

            messages.success(request, "Account created successfully! Please log in.")
            return redirect("login")

        except Exception as e:
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-student.html")

    return render(request, "register-student.html")

def forgot_password_page(request):
    return render(request, "forgot-password.html")


def home_page(request):
    return render(request, "home.html")


def logout_page(request):
    request.session.flush()
    return redirect("login")


def user_dashboard(request):
    if not request.session.get("user_id"):
        return redirect("login")

    try:
        user_email = request.session.get("user_email")
        first_name = request.session.get("first_name", "User")
        
        appointment_response = supabase.table("appointment").select("*").eq("user_email", user_email).order("appointment_date", desc=True).execute()
        appointments = appointment_response.data if appointment_response.data else []
        # --- END NEW ---

        context = {
            "user_email": user_email,
            "first_name": first_name,
            "appointments": appointments  # Pass the appointments to the template
        }
        # --- FIX #1 ---
        # We make the path more specific so Django can find it.
        return render(request, "user-dashboard.html", context)

    except Exception as e:
        print(f"--- DEBUG: USER DASHBOARD CRASH ---")
        print(f"Error type: {type(e)}")
        print(f"Error details: {e}")
        print(f"--- END DEBUG ---")
        # Add a message for the user even if things break
        messages.error(request, f"Could not load dashboard data: {e}")
        # --- FIX #2 ---
        # We also update the path here in the error case.
        return render(request, "user-dashboard.html", {
            "first_name": request.session.get("first_name", "User"),
            "appointments": [] # Send an empty list on error
        })


# ============================================================
# NEW ADMIN APPOINTMENT MANAGEMENT VIEWS
# ============================================================

@admin_required
def appointment_list_page(request):
    """Displays all appointments."""
    try:
        response = supabase.table("appointment").select("*").order("appointment_date", desc=False).execute()
        appointments = response.data if response.data else []
        context = {"appointments": appointments}
        return render(request, "appointments.html", context)
    except Exception as e:
        print(f"DEBUG: Error fetching appointments: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, "appointments.html", {"appointments": []})

@admin_required
def complete_appointment(request, appointment_id):
    """
    Marks an appointment as completed by setting successful_appointment_visit = True 
    in the corresponding record_logs entry.
    """
    # This action should only be processed via a POST request from the form/button
    if request.method == 'POST':
        try:
            # We target the 'record_logs' table (your renamed table)
            # using the appointment_id to find the related visit entry.
            response = supabase.table('patient_records').update({
                'successful_appointment_visit': True,
                'doctor_notes': 'Appointment completed and visit logged.' # Optional update
            }).eq('appointment_id', appointment_id).execute()
            
            if response.data:
                messages.success(request, f"Appointment #{appointment_id} successfully marked as completed.")
            else:
                # This catches cases where the log entry might be missing for some reason
                messages.warning(request, f"Appointment #{appointment_id} marked as completed, but the corresponding log entry was not found.")
                
        except Exception as e:
            print(f"DEBUG: Error completing appointment {appointment_id}: {str(e)}")
            messages.error(request, f"Failed to complete appointment. An unexpected error occurred: {str(e)}")
            
    return redirect("appointment_list")

#@admin_images
def edit_appointment(request, appointment_id):
    """Handles editing an appointment."""
    try:
        if request.method == "POST":
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            appointment_date = request.POST.get("appointment_date")
            
            # --- SPRINT 3: Also update the new fields ---
            doctor_name = request.POST.get("doctor_name")
            user_email = request.POST.get("user_email")

            if not all([first_name, last_name, appointment_date, doctor_name, user_email]):
                messages.error(request, "All fields are required!")
                # Re-fetch data for the form
                response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
                return render(request, "edit_appointment.html", {"appointment": response.data})

            update_data = {
                "first_name": first_name,
                "last_name": last_name,
                "appointment_date": appointment_date,
                "doctor_name": doctor_name, # Add this
                "user_email": user_email    # Add this
            }

            response = supabase.table("appointment").update(update_data).eq("id", appointment_id).execute()
            
            if response.data:
                messages.success(request, "Appointment updated successfully!")
                return redirect("appointment_list")
            else:
                messages.error(request, "Failed to update appointment. Please try again.")
                return render(request, "edit_appointment.html", {"appointment": update_data})

        else:
            # GET request
            response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
            if response.data:
                return render(request, "edit_appointment.html", {"appointment": response.data})
            else:
                messages.error(request, "Appointment not found.")
                return redirect("appointment_list")

    except Exception as e:
        print(f"DEBUG: Error editing appointment {appointment_id}: {str(e)}")
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect("appointment_list")
    
@admin_required
def edit_user_page(request, user_id):
    """
    Handles fetching user data for editing (GET) and updating user data (POST).
    """
    
    # --- GET REQUEST: Display the Edit Form ---
    if request.method == 'GET':
        try:
            # Fetch the specific user based on the provided user_id
            response = supabase.table("users").select("*").eq("id", user_id).single().execute()
            user_data = response.data
            
            context = {
                "user": user_data,
            }
            return render(request, "user_edit.html", context)
            
        except Exception as e:
            print(f"DEBUG: Error fetching user {user_id}: {e}")
            messages.error(request, f"Could not find user data. Error: {e}. Check if user_id is valid.")
            return redirect('user_management')
            
    # --- POST REQUEST: Process the Update ---
    elif request.method == 'POST':
        try:
            # Extract form data
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            # Checkbox returns 'on' if checked, otherwise it is absent from POST data. We convert it to a boolean.
            is_doctor = request.POST.get('is_doctor') == 'on'
            
            # Prepare data payload for Supabase
            update_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "is_doctor": is_doctor
            }
            
            # Perform the update where the ID matches
            supabase.table("users").update(update_data).eq("id", user_id).execute()
            
            messages.success(request, f"User {first_name} {last_name} (ID: {user_id}) updated successfully.")
            return redirect('user_management')
            
        except Exception as e:
            print(f"DEBUG: Error updating user {user_id}: {e}")
            messages.error(request, f"Failed to update user. Error: {e}. Please try again.")
            
            # If update fails, re-render the edit page with an error message
            # Re-fetch data to populate the form again
            try:
                response = supabase.table("users").select("*").eq("id", user_id).single().execute()
                user_data = response.data
                context = {"user": user_data}
                return render(request, "user_edit.html", context)
            except:
                return redirect('user_management')
            
@admin_required
def user_management_page(request):
    """Fetches all users, separates them into Doctors and Patients based on the is_doctor flag,
    and displays them in the management dashboard."""
    try:
        # Fetch all users, ordering by last name for a clean list
        response = supabase.table("users").select("*").order("last_name", desc=False).execute()
        all_users = response.data if response.data else []

        # Separate the lists based on the 'is_doctor' flag
        # NOTE: Supabase typically returns False/True, but sometimes None, so checking for True is safer for doctors.
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
        # Render the template with empty lists on error
        return render(request, "user_management.html", {"doctors": [], "patients": []})
    
    
    
@admin_required
def delete_appointment(request, appointment_id):
    """
    Deletes an appointment record, safely handling foreign key constraints
    by setting the reference in patient_records to NULL first.
    """
    try:
        # --- CRITICAL FIX: Handle Foreign Key Constraint ---
        # 1. Update all patient records that reference this appointment_id
        # and set their appointment_id column to NULL (None in Python).
        # This breaks the dependency and allows the appointment to be deleted.
        print(f"DEBUG: Clearing FK constraint for appointment ID: {appointment_id}")
        supabase.table('patient_records').update({'appointment_id': None}).eq('appointment_id', appointment_id).execute()
        
        # 2. Now, safely delete the appointment.
        response = supabase.table("appointment").delete().eq("id", appointment_id).execute()
        
        if response.data:
            messages.success(request, f"Appointment #{appointment_id} deleted successfully and patient links updated.")
        else:
            # If the response data is empty, the item might not have existed
            messages.error(request, f"Could not find or delete appointment #{appointment_id}.")

    except Exception as e:
        # This catches the original foreign key error and other potential issues
        error_message = str(e)
        print(f"DEBUG: Error deleting appointment {appointment_id}: {error_message}")
        
        # You can add logic here to check if the error is the specific FK error (code '23503') 
        # but the fix above should prevent it.
        messages.error(request, f"Failed to delete appointment. An unexpected error occurred: {error_message}")
    
    return redirect("appointment_list")

@admin_required
def patient_records_list_page(request):
    """Displays all patient records along with the patient's name."""
    try:
        # Fetch records and SELECT the related 'user_id' object,
        # specifying the columns you want from the related 'users' table.
        # We assume the user's name columns are 'first_name' and 'last_name'.
        
        response = supabase.table("patient_records").select("*, user_id(first_name, last_name)").order("record_date", desc=True).execute()
        
        records = response.data if response.data else []
        
        context = {"records": records}
        return render(request, "patient_records_list.html", context)
    
    except Exception as e:
        # ... (error handling remains the same)
        print(f"DEBUG: Error fetching patient records: {str(e)}")
        messages.error(request, f"Could not load patient records: {str(e)}")
        return render(request, "patient_records_list.html", {"records": []})
    

    