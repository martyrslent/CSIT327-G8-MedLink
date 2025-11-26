# ============================================================
# IMPORTS
# ============================================================
import os
import time # To generate unique filenames
from datetime import datetime, timedelta
from functools import wraps
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from .supabase_client import supabase 
from supabase import create_client, Client
from .email_utils import send_appointment_confirmation_email

# ============================================================
# ADMIN AUTHENTICATION DECORATOR
# ============================================================
def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.session.get("role") not in ["admin", "superadmin"]:
            messages.error(request, "Access denied. Please log in as an administrator.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.session.get("role") != "superadmin":
            messages.error(request, "Access denied. Superadmin privileges required.")
            return redirect("admin_dashboard")  # Or "login"
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ============================================================
# PUBLIC / BASIC VIEWS
# ============================================================
def hello_page(request):
    return HttpResponse("Hello, Django Page!")

def home_page(request):
    return render(request, "home.html")

def forgot_password_page(request):
    return render(request, "forgot-password.html")


# ============================================================
# AUTHENTICATION PAGES (LOGIN / LOGOUT)
# ============================================================
# --- LOGIN PAGE (Now complete with check_password) ---
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

            # Set session
            request.session["user_id"] = user["id"]
            request.session["user_email"] = user["email"]
            request.session["first_name"] = user.get("first_name", "User")

            # Only one role per user
            if user.get("is_superadmin", False):
                request.session["role"] = "superadmin"
                return redirect("admin_dashboard")
            elif user.get("is_admin", False):
                request.session["role"] = "admin"
                return redirect("admin_dashboard")
            else:
                request.session["role"] = "user"
                return redirect("user_dashboard")

        except Exception as e:
            print(f"DEBUG: Exception occurred: {str(e)}")
            messages.error(request, f"Unexpected error: {str(e)}")
            return render(request, "login-student.html")

    return render(request, "login-student.html")


def logout_page(request):
    request.session.flush()
    messages.success(request, "You have been logged out.") # Added message for better UX
    return redirect("login")


# ============================================================
# REGISTRATION PAGES
# ============================================================
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


# --- ADMIN REGISTRATION PAGE (Includes staff roles) ---
@superadmin_required
def register_admin_page(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        role = request.POST.get("role")  # NEW: Get the selected role
        
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
                "is_doctor": is_doctor_flag,
                "is_superadmin": False  # IMPORTANT: never create new superadmins from here
            }).execute()

            messages.success(
                request,
                f"New {role.capitalize()} {first_name} added successfully! They can now log in."
            )
            return redirect("admin_dashboard")

        except Exception as e:
            print(f"DEBUG: Critical error during admin registration: {str(e)}")
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-admin.html")

    return render(request, "register-admin.html")


# ============================================================
# PROFILE / USER SETTINGS
# ============================================================
# --- PROFILE PAGE (Updated to include profile_image) ---
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
            "age": user_data.get("age", ""), # Changed default to empty string for form
            "gender": user_data.get("gender", ""),
            "bio": user_data.get("bio", ""), # <--- NEW
            "profile_image": user_data.get("profile_image"), 
        }

        return render(request, "profile.html", context)

    except Exception as e:
        print(f"DEBUG: Error loading profile: {e}")
        messages.error(request, "Could not load profile data.")
        return redirect("user_dashboard")


# --- NEW: UPDATE PROFILE PICTURE ---
def update_profile_picture(request):
    if not request.session.get("user_id"):
        return redirect("login")
        
    if request.method == "POST" and request.FILES.get("profile_picture"):
        user_id = request.session.get("user_id")
        image_file = request.FILES["profile_picture"]
        
        try:
            # 1. Create a unique filename to prevent caching issues
            file_ext = image_file.name.split('.')[-1]
            file_path = f"user_{user_id}_{int(time.time())}.{file_ext}"
            
            # 2. Read file content
            file_content = image_file.read()
            
            # 3. Upload to Supabase Storage (Bucket: 'avatars')
            # Note: Ensure you created a public bucket named 'avatars' in Supabase
            supabase.storage.from_("avatars").upload(
                file=file_content,
                path=file_path,
                file_options={"content-type": image_file.content_type}
            )
            
            # 4. Get the Public URL
            public_url = supabase.storage.from_("avatars").get_public_url(file_path)
            
            # 5. Update the Users table
            supabase.table("users").update({"profile_image": public_url}).eq("id", user_id).execute()
            
            messages.success(request, "Profile picture updated successfully!")
            
        except Exception as e:
            print(f"Error uploading image: {e}")
            messages.error(request, "Failed to upload image. Please try again.")
            
    return redirect("user_profile")


# --- USER SETTINGS: CHANGE PASSWORD ---
def change_password(request):
    # 1. Security: Ensure user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        try:
            # Fetch current user data to get the real password hash
            response = supabase.table("users").select("*").eq("id", user_id).single().execute()
            user = response.data

            if not user:
                messages.error(request, "User not found.")
                return redirect("user_dashboard")

            # --- RULE 1: Verify Old Password ---
            if not check_password(old_password, user["password"]):
                messages.error(request, "Incorrect current password.")
                return render(request, "change_password.html")

            # --- RULE 2: Prevent Reuse (Old != New) ---
            if old_password == new_password:
                messages.error(request, "New password cannot be the same as the old password.")
                return render(request, "change_password.html")

            # --- RULE 3: Complexity (Caps + Number) ---
            if not any(char.isupper() for char in new_password):
                messages.error(request, "Password must contain at least one uppercase letter.")
                return render(request, "change_password.html")
            
            if not any(char.isdigit() for char in new_password):
                messages.error(request, "Password must contain at least one number.")
                return render(request, "change_password.html")

            # Basic Match Check
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return render(request, "change_password.html")

            # Validation passed: Hash and Update
            new_hashed_password = make_password(new_password)
            supabase.table("users").update({"password": new_hashed_password}).eq("id", user_id).execute()

            messages.success(request, "Password updated successfully! Please log in again.")
            # Optional: Force logout after password change for security
            request.session.flush()
            return redirect("login")

        except Exception as e:
            print(f"Error changing password: {e}")
            messages.error(request, "An unexpected error occurred.")

    return render(request, "change_password.html")


# --- USER SETTINGS: DELETE ACCOUNT ---
def delete_account(request):
    # 1. Security: Ensure user is logged in
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    if request.method == "POST":
        # Optional: Require password confirmation before deletion for extra safety
        password_confirmation = request.POST.get("password_confirmation")
        
        try:
            # Verify user exists and password matches (Safety check)
            response = supabase.table("users").select("*").eq("id", user_id).single().execute()
            user = response.data

            if user and check_password(password_confirmation, user["password"]):
                # DELETE ACTION
                supabase.table("users").delete().eq("id", user_id).execute()
                
                # Clear session
                request.session.flush()
                messages.success(request, "Your account has been successfully deleted.")
                return redirect("login")
            else:
                messages.error(request, "Incorrect password. Account deletion aborted.")
                return redirect("user_profile") # Or wherever the settings page is

        except Exception as e:
            print(f"Error deleting account: {e}")
            messages.error(request, "Could not delete account. Please try again.")

    return redirect("user_dashboard")


# --- USER SETTINGS: UPDATE PERSONAL INFO ---
def update_personal_info(request):
    if not request.session.get("user_id"):
        return redirect("login")

    if request.method == "POST":
        user_id = request.session.get("user_id")
        
        # Get data from form
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        age = request.POST.get("age")
        gender = request.POST.get("gender")
        bio = request.POST.get("bio")

        # Validate Age (Optional but good practice)
        if age and not age.isdigit():
            messages.error(request, "Age must be a valid number.")
            return redirect("user_profile")

        try:
            # Update Supabase
            update_data = {
                "first_name": first_name,
                "last_name": last_name,
                "age": int(age) if age else None,
                "gender": gender,
                "bio": bio
            }
            
            supabase.table("users").update(update_data).eq("id", user_id).execute()
            
            # Update Session data if name changed
            request.session["first_name"] = first_name
            
            messages.success(request, "Profile updated successfully!")

        except Exception as e:
            print(f"Error updating profile: {e}")
            messages.error(request, "An error occurred while updating profile.")

    return redirect("user_profile")


# ============================================================
# APPOINTMENT BOOKING & REGISTRATION (USER & ADMIN)
# ============================================================
def book_appointment(request):
    if not request.session.get("user_id"):
        return redirect("login")

    try:
        # Fetch all doctors including is_in status
        doctors_response = supabase.table("users").select("id, first_name, last_name, is_in").eq("is_doctor", True).execute()
        doctors = doctors_response.data or []
    except Exception as e:
        print(f"Error fetching doctors: {e}")
        doctors = []

    if request.method == "POST":
        appointment_date = request.POST.get("appointment_date")
        appointment_time = request.POST.get("appointment_time")
        doctor_name = request.POST.get("doctor_name")
        reason_for_visit = request.POST.get("reason_for_visit")

        if not all([appointment_date, appointment_time, doctor_name, reason_for_visit]):
            messages.error(request, "Please fill in all fields.")
            return render(request, "book_appointment.html", {"doctors": doctors})

        try:
            user_id = request.session.get("user_id")
            user_response = supabase.table("users").select("*").eq("id", user_id).single().execute()
            user = user_response.data

            if not user:
                messages.error(request, "User not found.")
                return redirect("login")

            # --- Validate that doctor is active ---
            active_doctors = [f"{d['first_name']} {d['last_name']}" for d in doctors if d.get("is_in", True)]
            if doctor_name not in active_doctors:
                messages.error(request, f"'{doctor_name}' is currently not available for booking.")
                return render(request, "book_appointment.html", {"doctors": doctors})

            # --- DOUBLE BOOKING CHECK ---
            existing_response = supabase.table("appointment").select("*") \
                .eq("doctor_name", doctor_name) \
                .eq("appointment_date", appointment_date) \
                .eq("appointment_time", appointment_time) \
                .execute()
            if existing_response.data:
                messages.error(request, "This doctor is already booked for the selected date and time.")
                return render(request, "book_appointment.html", {"doctors": doctors})

            # Insert appointment
            appointment_data = {
                "patient_id": user_id,
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "user_email": user.get("email"),
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "doctor_name": doctor_name,
                "reason_for_visit": reason_for_visit,
                "status": "Pending",
            }

            supabase.table("appointment").insert(appointment_data).execute()

            try:
                full_name = f"{user.get('first_name')} {user.get('last_name')}"
                send_appointment_confirmation_email(
                    user_name=full_name,
                    user_email=user.get("email"),
                    doctor_name=doctor_name,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time
                )
            except Exception as e:
                print(f"Email error: {e}")

            messages.success(request, "Appointment booked successfully!")
            return redirect("user_dashboard")

        except Exception as e:
            print(f"Error booking appointment: {e}")
            messages.error(request, "An unexpected error occurred. Please try again.")

    return render(request, "book_appointment.html", {"doctors": doctors})


# --- APPOINTMENT REGISTRATION (Includes doctor list fetch and record creation) ---
@admin_required
def register_appointment(request):
    doctors = []
    try:
        # Fetch all doctors with is_doctor=True and include is_in column
        doctors_response = supabase.table("users").select("id, first_name, last_name, is_in").eq("is_doctor", True).execute()
        doctors = doctors_response.data
    except Exception as e:
        print(f"DEBUG: Could not fetch list of doctors: {e}")
        messages.warning(request, "Could not load the list of available doctors due to a database error.")
    
    context = {"doctors": doctors}

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        appointment_date = request.POST.get("appointment_date")
        appointment_time = request.POST.get("appointment_time")
        doctor_name = request.POST.get("doctor_name") 
        user_email = request.POST.get("user_email")
        reason_for_visit = request.POST.get("reason_for_visit")

        if not all([first_name, last_name, appointment_date, appointment_time, doctor_name, user_email, reason_for_visit]):
            messages.error(request, "All required fields are needed to book an appointment.")
            return render(request, "appointment_form.html", context)
        
        # Only allow selection of doctors who are is_in=True
        valid_doctor_names = [f"{d['first_name']} {d['last_name']}" for d in doctors if d.get("is_in", True)]
        if doctor_name not in valid_doctor_names:
            messages.error(request, f"'{doctor_name}' is not available for booking. Please select a valid doctor from the list.")
            return render(request, "appointment_form.html", context)
        
        # Fetch patient_id if exists
        patient_id = None
        try:
            patient_response = supabase.table("users").select("id").eq("email", user_email).single().execute()
            if patient_response.data:
                patient_id = patient_response.data.get("id")
        except Exception:
            messages.error(request, "Patient with that email was not found in the users database. Appointment not booked.")
            return render(request, "appointment_form.html", context)

        # --- DOUBLE BOOKING CHECK ---
        try:
            existing_response = supabase.table("appointment").select("*") \
                .eq("doctor_name", doctor_name) \
                .eq("appointment_date", appointment_date) \
                .eq("appointment_time", appointment_time) \
                .execute()
            if existing_response.data:
                messages.error(request, f"This doctor is already booked at {appointment_time} on {appointment_date}. Please choose another time.")
                return render(request, "appointment_form.html", context)
        except Exception as e:
            print(f"DEBUG: Could not check for double booking: {e}")

        # Prepare appointment data
        appointment_data = {
            "first_name": first_name,
            "last_name": last_name,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "reason_for_visit": reason_for_visit,
            "status": "Pending",
            "doctor_name": doctor_name,
            "user_email": user_email,
            "patient_id": patient_id
        }

        try:
            # Insert into appointments
            response = supabase.table("appointment").insert(appointment_data).execute()
            new_appointment_data = response.data[0]
            new_appointment_id = new_appointment_data.get('id')

            # Insert into patient records
            patient_record_data = {
                "user_id": patient_id,
                "appointment_id": new_appointment_id,
                "record_date": appointment_date, 
                "successful_appointment_visit": False,
                "doctor_notes": "Appointment scheduled."
            }
            supabase.table("patient_records").insert(patient_record_data).execute()
            
            # Send email notification
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
            return redirect("appointment_list")

        except Exception as e:
            print(f"DEBUG: Critical error during appointment registration: {str(e)}")
            messages.error(request, f"An unexpected error occurred during booking: {str(e)}")
            return render(request, "appointment_form.html", context)

    return render(request, "appointment_form.html", context)


# ============================================================
# APPOINTMENT LIST & ADMIN ACTIONS
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


@admin_required
def approve_appointment(request, appointment_id):
    # Fetch the appointment from Supabase
    response = supabase.table("appointment").select("*").eq("id", appointment_id).execute()
    
    if response.data:
        appointment = response.data[0]
        if appointment["status"] == "Pending":
            # Update status to Approved
            supabase.table("appointment").update({"status": "Approved"}).eq("id", appointment_id).execute()
            messages.success(request, f"Appointment #{appointment_id} approved successfully!")
        else:
            messages.warning(request, f"Appointment #{appointment_id} is already approved.")
    else:
        messages.error(request, f"Appointment #{appointment_id} not found.")
    
    return redirect('appointment_list')


@admin_required
def decline_appointment(request, appointment_id):
    try:
        # Mark the appointment as declined
        supabase.table("appointment").update({"status": "declined"}).eq("id", appointment_id).execute()
        messages.success(request, f"Appointment #{appointment_id} declined.")
    except Exception as e:
        print(f"Error declining appointment: {e}")
        messages.error(request, "Failed to decline the appointment.")
    
    return redirect("appointment_list")


def cancel_appointment(request, appointment_id):
    if not request.session.get("role") in ["admin", "superadmin"]:
        messages.error(request, "Unauthorized action.")
        return redirect("appointment_list")

    try:
        # Update the appointment status to Cancelled
        supabase.table("appointment").update({"status": "Cancelled"}).eq("id", appointment_id).execute()
        messages.success(request, "Appointment has been cancelled successfully.")
    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        messages.error(request, "Failed to cancel the appointment. Please try again.")

    return redirect("appointment_list")


def reinstate_appointment(request, appointment_id):
    if not request.session.get("role") in ["admin", "superadmin"]:
        messages.error(request, "Unauthorized action.")
        return redirect("appointment_list")

    try:
        # Update the appointment status back to Approved
        supabase.table("appointment").update({"status": "Approved"}).eq("id", appointment_id).execute()
        messages.success(request, "Appointment has been reinstated successfully.")
    except Exception as e:
        print(f"Error reinstating appointment: {e}")
        messages.error(request, "Failed to reinstate the appointment. Please try again.")

    return redirect("appointment_list")


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


# ============================================================
# USER MANAGEMENT (ADMIN)
# ============================================================
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


@admin_required
def toggle_is_in(request, user_id):
    if request.method == "POST":
        try:
            # Fetch current value
            user_response = supabase.table("users").select("is_in").eq("id", user_id).single().execute()
            user = user_response.data
            if not user:
                messages.error(request, "User not found.")
                return redirect("user_management")

            current_is_in = user.get("is_in", True)  # default True if missing

            # Toggle the value
            new_is_in = not current_is_in
            supabase.table("users").update({"is_in": new_is_in}).eq("id", user_id).execute()

            status_text = "active/bookable" if new_is_in else "inactive/not bookable"
            messages.success(request, f"User is now marked as {status_text}.")

        except Exception as e:
            print(f"Error toggling is_in for user {user_id}: {e}")
            messages.error(request, "Failed to update user status. Check server logs.")

    return redirect("user_management")    


# ============================================================
# PATIENT RECORDS
# ============================================================
# --- PATIENT RECORDS LIST (New from your old version) ---
@admin_required
def patient_records_list_page(request):
    """Displays all patient records with optional search by patient name."""
    try:
        search_query = request.GET.get("search", "").strip()

        # Fetch all patient records with joined user name
        response = (
            supabase.table("patient_records")
            .select("*, user_id(first_name, last_name), appointment_id(doctor_name, appointment_date)")
            .order("record_date", desc=True)
            .execute()
        )

        records = response.data or []

        # 🔎 Apply search filter (local filtering)
        if search_query:
            query = search_query.lower()
            records = [
                r for r in records
                if query in r["user_id"]["first_name"].lower()
                or query in r["user_id"]["last_name"].lower()
            ]

        context = {
            "records": records,
            "search": search_query,   # so input box can remember the value
        }

        return render(request, "patient_records_list.html", context)

    except Exception as e:
        print(f"DEBUG: Error fetching patient records: {str(e)}")
        messages.error(request, f"Could not load patient records: {str(e)}")
        return render(request, "patient_records_list.html", {"records": [], "search": ""})


# ============================================================
# ADMIN DASHBOARD
# ============================================================
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
@admin_required
def appointment_list_page(request):
    """Displays all active appointments (hides Completed)."""
    try:
        # Filter OUT 'Completed' items
        response = supabase.table("appointment").select("*").neq("status", "Completed").order("appointment_date", desc=False).execute()
        appointments = response.data or []
        context = {"appointments": appointments}
        return render(request, "appointments.html", context)
    except Exception as e:
        print(f"DEBUG: Error fetching appointments: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, "appointments.html", {"appointments": []})
    
@admin_required
def complete_appointment(request, appointment_id):
    # Security check using your role system
    if request.session.get("role") not in ["admin", "superadmin"]:
        return redirect("login")

    try:
        # 1. Update Appointment Status (Makes it disappear from the main list)
        supabase.table("appointment").update({"status": "Completed"}).eq("id", appointment_id).execute()

        # 2. Update Patient Record (Logs the successful visit)
        # We try to find the record linked to this appointment_id
        response = supabase.table('patient_records').update({
            'successful_appointment_visit': True,
            'doctor_notes': 'Appointment completed and visit logged.'
        }).eq('appointment_id', appointment_id).execute()
        
        messages.success(request, "Appointment marked as Complete! It has been moved to Patient Records.")
            
    except Exception as e:
        print(f"DEBUG: Error completing appointment {appointment_id}: {str(e)}")
        messages.error(request, f"Failed to complete appointment: {str(e)}")
            
    return redirect("appointment_list")
    
    
def user_dashboard(request):
    if not request.session.get("user_id"):
        return redirect("login")

    try:
        user_email = request.session.get("user_email")
        first_name = request.session.get("first_name", "User")
        
        # Fetch all appointments
        response = supabase.table("appointment").select("*").eq("user_email", user_email).order("appointment_date", desc=False).execute()
        all_appointments = response.data or []

        today = datetime.now().date()
        reminder_threshold = today + timedelta(days=3)

        upcoming_appointments = []
        reminders = []

        for appt in all_appointments:
            try:
                appt_date = datetime.strptime(appt['appointment_date'], '%Y-%m-%d').date()
                
                # Show Future or Today
                if appt_date >= today and appt.get('status') != 'Completed':
                    upcoming_appointments.append(appt)
                    
                    # Create Reminder if Approved AND within 3 days
                    if appt_date <= reminder_threshold and appt.get('status') == 'Approved':
                        reminders.append(appt)
                        
            except ValueError:
                continue

        context = {
            "user_email": user_email,
            "first_name": first_name,
            "appointments": upcoming_appointments,
            "reminders": reminders, 
        }
        return render(request, "user-dashboard.html", context)

    except Exception as e:
        print(f"Error: {e}")
        return render(request, "user-dashboard.html", {"first_name": "User", "appointments": [], "reminders": []})
@admin_required
def patient_records_list_page(request):
    """Displays only COMPLETED patient records."""
    if request.session.get("role") not in ["admin", "superadmin"]:
        return redirect("login")

    try:
        search_query = request.GET.get("search", "").strip()

        # Fetch patient records. 
        # Ideally, we join with the appointment table or check the status if it's stored here.
        # Based on your structure, we can verify the status via the appointment link if needed, 
        # or rely on 'successful_appointment_visit' being True.
        
        response = (
            supabase.table("patient_records")
            .select("*, user_id(first_name, last_name), appointment_id(doctor_name, appointment_date)")
            .eq("successful_appointment_visit", True) # Fetch only successful/completed visits
            .order("record_date", desc=True)
            .execute()
        )

        records = response.data or []

        # Local search filter
        if search_query:
            query = search_query.lower()
            records = [
                r for r in records
                if query in r["user_id"]["first_name"].lower()
                or query in r["user_id"]["last_name"].lower()
            ]

        context = {
            "records": records,
            "search": search_query,
        }

        return render(request, "patient_records_list.html", context)

    except Exception as e:
        print(f"DEBUG: Error fetching records: {e}")
        messages.error(request, "Could not load patient records.")
        return render(request, "patient_records_list.html", {"records": []})

def appointment_history(request):
    if not request.session.get("user_id"):
        return redirect("login")
        
    try:
        user_email = request.session.get("user_email")
        
        # Fetch all appointments
        response = supabase.table("appointment").select("*").eq("user_email", user_email).order("appointment_date", desc=True).execute()
        all_appointments = response.data or []
        
        today = datetime.now().date()
        past_appointments = []

        for appt in all_appointments:
            try:
                appt_date = datetime.strptime(appt['appointment_date'], '%Y-%m-%d').date()
                
                # Condition: Is Past OR Is Completed
                if appt_date < today or appt.get('status') == 'Completed':
                    past_appointments.append(appt)
            except ValueError:
                continue

        return render(request, "appointment_history.html", {"history": past_appointments})

    except Exception as e:
        print(f"Error: {e}")
        return redirect("user_dashboard")