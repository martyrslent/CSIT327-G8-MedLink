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
# ADMIN AUTHENTICATION DECORATOR (Cleaned up)
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

        # Basic Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "register-admin.html")
        
        if not all([first_name, last_name, email, password]):
            messages.error(request, "All fields are required!")
            return render(request, "register-admin.html")

        table_name = "users"

        try:
            response = supabase.table(table_name).select("email").eq("email", email).execute()
            
            if response.data and len(response.data) > 0:
                messages.error(request, "Email already registered!")
                return render(request, "register-admin.html")

            hashed_password = make_password(password)

            response = supabase.table(table_name).insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": True 
            }).execute()

            if isinstance(response, dict) and 'error' in response:
                error_message = f"Supabase Error: {response['error'].get('message', 'Unknown error')}"
                print(f"DEBUG: Staff insertion failed - {error_message}")
                messages.error(request, error_message)
                return render(request, "register-admin.html")

            messages.success(request, f"New staff member {first_name} added successfully! They can now log in.")
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Critical error during admin registration: {str(e)}")
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-admin.html")

    return render(request, "register-admin.html")


# ============================================================
# SPRINT 3 FEATURE: EMAIL NOTIFICATION
# ============================================================
@admin_required
def register_appointment(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        appointment_date = request.POST.get("appointment_date")

        # --- NEW FIELDS FOR SPRINT 3 ---
        doctor_name = request.POST.get("doctor_name", "Your Doctor")
        user_email = request.POST.get("user_email")

        # --- Updated Validation ---
        if not all([first_name, last_name, appointment_date, doctor_name, user_email]):
            messages.error(request, "All fields (First Name, Last Name, Date, Doctor, Email) are required!")
            return render(request, "appointment_form.html")

        appointment_data = {
            "first_name": first_name,
            "last_name": last_name,
            "appointment_date": appointment_date,
            "doctor_name": doctor_name,
            "user_email": user_email
        }

        try:
            # --- 1. Save appointment to Supabase ---
            response = supabase.table("appointment").insert(appointment_data).execute()
            
            # Check for Supabase error (This part of your code is good)
            if isinstance(response, dict) and 'error' in response:
                error_message = f"Supabase Error: {response['error'].get('message', 'Unknown error')}"
                print(f"DEBUG: Supabase Insertion Failed - {error_message}")
                messages.error(request, error_message)
                return render(request, "appointment_form.html")

            # --- 2. Trigger Email Notification (NEW CODE BLOCK) ---
            try:
                full_name = f"{first_name} {last_name}"
                
                # NOTE: Your email_utils function needs 'appointment_time'. 
                # Since 'appointment_date' likely holds the full datetime, 
                # we'll pass the date and extract time if needed, or pass an empty string 
                # if you haven't implemented time yet. For now, we'll use a placeholder/split.
                
                # You should adapt this line based on how you handle time in the form/data:
                appointment_time = "Not specified" # <-- CHANGE THIS if you collect time separately
                
                send_appointment_confirmation_email(
                    user_name=full_name,
                    user_email=user_email,
                    doctor_name=doctor_name,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time # Pass the time variable
                )
            except Exception as e:
                # Don't crash the page if email fails. Just log it.
                print(f"CRITICAL: Email send failed after booking: {e}")
                messages.warning(request, "Appointment saved, but email notification failed. Please check server logs.")
            # --- End of Email Code ---

            messages.success(request, f"Appointment for {first_name} {last_name} on {appointment_date} successfully registered! A confirmation email has been sent.")
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Critical error during appointment registration: {str(e)}")
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return render(request, "appointment_form.html")

    return render(request, "appointment_form.html")


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
            response = supabase.table(table_name).select("email").eq("email", email).execute()
            if response.data:
                messages.error(request, "Email already registered!")
                return render(request, "register-student.html")

            hashed_password = make_password(password)

            response = supabase.table(table_name).insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": False
            }).execute()

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
        context = {
            "user_email": request.session.get("user_email"),
            "first_name": request.session.get("first_name", "User"),
        }
        return render(request, "user_dashboard.html", context)

    except Exception as e:
        print(f"CRITICAL ERROR IN USER DASHBOARD: {e}")
        return HttpResponse(f"User Dashboard Crash: {e}", status=500)


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
def delete_appointment(request, appointment_id):
    """Deletes an appointment record."""
    try:
        response = supabase.table("appointment").delete().eq("id", appointment_id).execute()
        
        if response.data:
            messages.success(request, f"Appointment #{appointment_id} deleted successfully.")
        else:
            messages.error(request, f"Could not find or delete appointment #{appointment_id}.")

    except Exception as e:
        print(f"DEBUG: Error deleting appointment {appointment_id}: {str(e)}")
        messages.error(request, f"An unexpected error occurred: {str(e)}")
    
    return redirect("appointment_list")