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
# ADMIN AUTHENTICATION DECORATOR
# ============================================================
def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get("is_admin"):
            messages.error(request, "Access denied. Please log in as an administrator.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ============================================================
# BASIC PAGE
# ============================================================
def hello_page(request):
    return HttpResponse("Hello, Django Page!")


# ============================================================
# ADMIN REGISTRATION PAGE
# ============================================================
@admin_required
def register_admin_page(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "register-admin.html")
        
        if not all([first_name, last_name, email, password]):
            messages.error(request, "All fields are required!")
            return render(request, "register-admin.html")

        try:
            response = supabase.table("users").select("email").eq("email", email).execute()
            
            if response.data and len(response.data) > 0:
                messages.error(request, "Email already registered!")
                return render(request, "register-admin.html")

            hashed_password = make_password(password)

            supabase.table("users").insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": True
            }).execute()

            messages.success(request, f"New staff member {first_name} added successfully!")
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Critical error during admin registration: {str(e)}")
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-admin.html")

    return render(request, "register-admin.html")


# ============================================================
# APPOINTMENT REGISTRATION + EMAIL (ADMIN)
# ============================================================
@admin_required
def register_appointment(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        appointment_date = request.POST.get("appointment_date")
        doctor_name = request.POST.get("doctor_name", "Your Doctor")
        user_email = request.POST.get("user_email")

        if not all([first_name, last_name, appointment_date, doctor_name, user_email]):
            messages.error(request, "All fields are required!")
            return render(request, "appointment_form.html")

        appointment_data = {
            "first_name": first_name,
            "last_name": last_name,
            "appointment_date": appointment_date,
            "doctor_name": doctor_name,
            "user_email": user_email
        }

        try:
            supabase.table("appointment").insert(appointment_data).execute()

            try:
                full_name = f"{first_name} {last_name}"
                send_appointment_confirmation_email(
                    user_name=full_name,
                    user_email=user_email,
                    doctor_name=doctor_name,
                    appointment_date=appointment_date,
                    appointment_time="Not specified"
                )
            except Exception as e:
                print(f"CRITICAL: Email send failed: {e}")
                messages.warning(request, "Appointment saved, but email failed to send.")

            messages.success(request, f"Appointment for {first_name} saved successfully!")
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Error during appointment registration: {e}")
            messages.error(request, f"Unexpected error: {e}")
            return render(request, "appointment_form.html")

    return render(request, "appointment_form.html")


# ============================================================
# LOGIN PAGE
# ============================================================
def login_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

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
            print(f"DEBUG: Exception occurred: {e}")
            messages.error(request, f"Unexpected error: {e}")
            return render(request, "login-student.html")

    return render(request, "login-student.html")


# ============================================================
# ADMIN DASHBOARD
# ============================================================
@admin_required
def admin_dashboard(request):
    try:
        total_patients = supabase.table("users").select("id", count='exact').eq("is_admin", False).execute().count or 0
        total_appointments = supabase.table("appointment").select("id", count='exact').execute().count or 0

        recent_users = supabase.table("users").select("*").eq("is_admin", False).order("id", desc=True).limit(5).execute()
        recent_activity = recent_users.data or []

        return render(request, "admin_dashboard.html", {
            "total_patients": total_patients,
            "total_appointments": total_appointments,
            "recent_activity": recent_activity,
            "new_registrations": total_patients,
        })

    except Exception as e:
        print(f"CRITICAL ERROR IN DASHBOARD: {e}")
        messages.error(request, f"Could not load dashboard data: {e}")
        return render(request, "admin_dashboard.html", {
            "total_patients": 0,
            "total_appointments": 0,
            "recent_activity": [],
            "new_registrations": 0,
        })


# ============================================================
# USER REGISTRATION
# ============================================================
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

        try:
            response = supabase.table("users").select("email").eq("email", email).execute()
            if response.data:
                messages.error(request, "Email already registered!")
                return render(request, "register-student.html")

            hashed_password = make_password(password)

            supabase.table("users").insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": False
            }).execute()

            messages.success(request, "Account created successfully!")
            return redirect("login")

        except Exception as e:
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-student.html")

    return render(request, "register-student.html")


# ============================================================
# SIMPLE PAGES
# ============================================================
def forgot_password_page(request):
    return render(request, "forgot-password.html")


def home_page(request):
    return render(request, "home.html")


def logout_page(request):
    request.session.flush()
    return redirect("login")


# ============================================================
# USER DASHBOARD
# ============================================================
def user_dashboard(request):
    if not request.session.get("user_id"):
        return redirect("login")

    try:
        user_email = request.session.get("user_email")
        first_name = request.session.get("first_name", "User")
        
        appointment_response = supabase.table("appointment").select("*").eq("user_email", user_email).order("appointment_date", desc=True).execute()
        appointments = appointment_response.data if appointment_response.data else []

        return render(request, "user-dashboard.html", {
            "user_email": user_email,
            "first_name": first_name,
            "appointments": appointments
        })

    except Exception as e:
        print(f"DEBUG: USER DASHBOARD ERROR: {e}")
        messages.error(request, f"Could not load dashboard data: {e}")
        return render(request, "user-dashboard.html", {
            "first_name": request.session.get("first_name", "User"),
            "appointments": []
        })


# ============================================================
# USER: BOOK APPOINTMENT 
# ============================================================
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


# ============================================================
# PROFILE PAGE
# ============================================================
def profile_page(request):
    if not request.session.get("user_id"):
        return redirect("login")

    user_email = request.session.get("user_email")

    try:
        response = supabase.table("users").select("*").eq("email", user_email).single().execute()
        user_data = response.data if response.data else {}

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
# ADMIN: APPOINTMENT LIST
# ============================================================
@admin_required
def appointment_list_page(request):
    try:
        response = supabase.table("appointment").select("*").order("appointment_date", desc=False).execute()
        appointments = response.data if response.data else []
        return render(request, "appointments.html", {"appointments": appointments})
    except Exception as e:
        print(f"DEBUG: Error fetching appointments: {e}")
        messages.error(request, f"An error occurred: {e}")
        return render(request, "appointments.html", {"appointments": []})


# ============================================================
# ADMIN: EDIT APPOINTMENT
# ============================================================
def edit_appointment(request, appointment_id):
    try:
        if request.method == "POST":
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            appointment_date = request.POST.get("appointment_date")
            doctor_name = request.POST.get("doctor_name")
            user_email = request.POST.get("user_email")

            if not all([first_name, last_name, appointment_date, doctor_name, user_email]):
                messages.error(request, "All fields are required!")
                response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
                return render(request, "edit_appointment.html", {"appointment": response.data})

            update_data = {
                "first_name": first_name,
                "last_name": last_name,
                "appointment_date": appointment_date,
                "doctor_name": doctor_name,
                "user_email": user_email
            }

            response = supabase.table("appointment").update(update_data).eq("id", appointment_id).execute()

            if response.data:
                messages.success(request, "Appointment updated successfully!")
                return redirect("appointment_list")
            else:
                messages.error(request, "Failed to update appointment.")
                return render(request, "edit_appointment.html", {"appointment": update_data})

        else:
            response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
            if response.data:
                return render(request, "edit_appointment.html", {"appointment": response.data})
            else:
                messages.error(request, "Appointment not found.")
                return redirect("appointment_list")

    except Exception as e:
        print(f"DEBUG: Error editing appointment {appointment_id}: {e}")
        messages.error(request, f"An unexpected error occurred: {e}")
        return redirect("appointment_list")


# ============================================================
# ADMIN: DELETE APPOINTMENT
# ============================================================
@admin_required
def delete_appointment(request, appointment_id):
    try:
        response = supabase.table("appointment").delete().eq("id", appointment_id).execute()
        
        if response.data:
            messages.success(request, f"Appointment #{appointment_id} deleted successfully.")
        else:
            messages.error(request, f"Could not delete appointment #{appointment_id}.")
    except Exception as e:
        print(f"DEBUG: Error deleting appointment {appointment_id}: {e}")
        messages.error(request, f"An unexpected error occurred: {e}")

    return redirect("appointment_list")
