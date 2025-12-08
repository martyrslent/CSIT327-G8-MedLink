# ============================================================
# IMPORTS
# ============================================================
import os
import time # To generate unique filenames
from datetime import datetime, timedelta, date
from functools import wraps
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from .supabase_client import supabase 
from supabase import create_client, Client
from .email_utils import send_appointment_confirmation_email
today = date.today().isoformat()
from django.core.paginator import Paginator
from django.http import JsonResponse

# ============================================================
# ADMIN AUTHENTICATION DECORATOR
# ============================================================
def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # [FIX] Added "doctor" to the allowed list
        if request.session.get("role") not in ["admin", "superadmin", "doctor"]:
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

# [NEW] DOCTOR AUTHENTICATION DECORATOR
def doctor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # We check the session flag we set during login
        if not request.session.get("is_doctor"):
            messages.error(request, "Access denied. Only doctors can view this patient data.")
            return redirect("user_dashboard") 
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# [NEW] THE VIEW
@doctor_required
def view_patient_health(request, patient_id):
    try:
        # Fetch patient data
        response = supabase.table("users").select("*").eq("id", patient_id).single().execute()
        patient = response.data
        
        if not patient:
            messages.error(request, "Patient not found.")
            return redirect("appointment_list")

        # [CHANGED] 1. Handle Reason for Visit via GET parameter
        appointment_id = request.GET.get('appt_id')
        current_appointment = None
        
        if appointment_id:
            appt_response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
            current_appointment = appt_response.data

        # [NOTE] Medical History fetch removed as requested

        context = {
            "patient": patient,
            "current_appointment": current_appointment, 
        }
        return render(request, "doctor_patient_view.html", context)

    except Exception as e:
        print(f"Error fetching patient health view: {e}")
        messages.error(request, "Could not load patient details.")
        return redirect("appointment_list")


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
# --- LOGIN PAGE ---
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
            request.session["is_doctor"] = user.get("is_doctor", False)

            # [FIXED] Redirect Logic - Distinguish Superadmin from Admin
            if user.get("is_superadmin", False):
                request.session["role"] = "superadmin"  # <--- Crucial Fix!
                return redirect("admin_dashboard")
            
            elif user.get("is_admin", False):
                request.session["role"] = "admin"
                return redirect("admin_dashboard")
            
            elif user.get("is_doctor", False):
                request.session["role"] = "doctor"
                return redirect("admin_dashboard") 
            
            else:
                request.session["role"] = "user"
                return redirect("user_dashboard")

        # [FIX] Added the missing except block here
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
        role = request.POST.get("role")
        specialization = request.POST.get("specialization")  # NEW FIELD

        # Basic validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "register-admin.html")

        if not all([first_name, last_name, email, password, role]):
            messages.error(request, "All fields are required!")
            return render(request, "register-admin.html")

        # Specialization required only if doctor selected
        if role == "doctor" and not specialization:
            messages.error(request, "Please enter a specialization for the doctor.")
            return render(request, "register-admin.html")

        is_doctor_flag = (role == "doctor")
        is_admin_flag = (role == "staff")

        try:
            # Check if email exists
            response = supabase.table("users").select("email").eq("email", email).execute()
            if response.data:
                messages.error(request, "Email already registered!")
                return render(request, "register-admin.html")

            hashed_password = make_password(password)

            # Insert into users table
            user_insert = supabase.table("users").insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": is_admin_flag,
                "is_doctor": is_doctor_flag,
                "is_superadmin": False
            }).execute()

            # Get newly inserted user ID
            user_id = user_insert.data[0]["id"]

            # If doctor → insert into doctors table
            if is_doctor_flag:
                supabase.table("doctors").insert({
                    "doctor_id": user_id,
                    "specialization": specialization
                }).execute()

            messages.success(request, f"{role.capitalize()} {first_name} added successfully!")
            return redirect("user_management")

        except Exception as e:
            print("DEBUG ERROR:", e)
            messages.error(request, f"Unexpected error: {e}")
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
            "age": user_data.get("age", ""),
            "gender": user_data.get("gender", ""),
            "bio": user_data.get("bio", ""),
            "allergies": user_data.get("allergies", ""),           # NEW
            "medical_conditions": user_data.get("medical_conditions", ""),   # NEW
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

        allergies = request.POST.get("allergies")
        medical_conditions = request.POST.get("medical_conditions")  # Correct column name

        # Validate Age
        if age and not age.isdigit():
            messages.error(request, "Age must be a valid number.")
            return redirect("user_profile")

        try:
            update_data = {
                "first_name": first_name,
                "last_name": last_name,
                "age": int(age) if age else None,
                "gender": gender,
                "bio": bio,
                "allergies": allergies,
                "medical_conditions": medical_conditions,  # Updated
            }
            
            supabase.table("users").update(update_data).eq("id", user_id).execute()
            
            request.session["first_name"] = first_name
            messages.success(request, "Profile updated successfully!")

        except Exception as e:
            print(f"Error updating profile: {e}")
            messages.error(request, "An error occurred while updating profile.")

    return redirect("user_profile")




# ... (imports and other views remain same)

def book_appointment(request):
    if not request.session.get("user_id"):
        return redirect("login")

    today = date.today().isoformat()

    # ======================================================
    # FETCH DOCTORS + SPECIALIZATION
    # ======================================================
    try:
        doctors_response = supabase.table("users").select(
            "id, first_name, last_name, is_in, doctors(specialization)"
        ).eq("is_doctor", True).execute()

        all_doctors_data = []

        for d in doctors_response.data or []:
            if d.get("doctors") and isinstance(d["doctors"], list) and d["doctors"]:
                specialization = d["doctors"][0].get("specialization")
            elif d.get("doctors") and isinstance(d["doctors"], dict):
                specialization = d["doctors"].get("specialization")
            else:
                specialization = None

            if specialization:
                all_doctors_data.append({
                    "id": d["id"],
                    "first_name": d["first_name"],
                    "last_name": d["last_name"],
                    "is_in": d.get("is_in", True),
                    "specialization": specialization
                })

    except Exception as e:
        print("Error fetching doctors:", e)
        all_doctors_data = []

    specializations = sorted(list(set(d["specialization"] for d in all_doctors_data)))

    context = {
        "doctors": all_doctors_data,
        "specializations": ["All"] + specializations,
        "today": today
    }

    # ======================================================
    # POST: BOOK APPOINTMENT
    # ======================================================
    if request.method == "POST":
        appointment_date = request.POST.get("appointment_date")
        appointment_time = request.POST.get("appointment_time")
        doctor_name = request.POST.get("doctor_name")
        reason_for_visit = request.POST.get("reason_for_visit")

        if not all([appointment_date, appointment_time, doctor_name, reason_for_visit]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, "book_appointment.html", context)

        user_id = request.session.get("user_id")

        # Fetch user data INCLUDING stored medical info
        user_response = supabase.table("users").select(
            "first_name, last_name, email, allergies, medical_conditions"
        ).eq("id", user_id).single().execute()

        user = user_response.data
        if not user:
            messages.error(request, "User not found.")
            return redirect("login")

        # Validate doctor availability
        active_doctors = {
            f"{d['first_name']} {d['last_name']}"
            for d in all_doctors_data if d.get("is_in", True)
        }

        if doctor_name not in active_doctors:
            messages.error(request, f"{doctor_name} is unavailable.")
            return render(request, "book_appointment.html", context)

        # Check if timeslot is already booked
        existing_response = supabase.table("appointment").select("*") \
            .eq("doctor_name", doctor_name) \
            .eq("appointment_date", appointment_date) \
            .eq("appointment_time", appointment_time) \
            .execute()

        if existing_response.data:
            messages.error(request, "This timeslot is already booked.")
            return render(request, "book_appointment.html", context)

        # ======================================================
        # 100% AUTOMATIC HEALTH INFO FROM PROFILE
        # ======================================================
        allergies = user.get("allergies") or "None"
        conditions = user.get("medical_conditions") or "None"

        full_reason = (
            f"{reason_for_visit}\n\n"
            f"[HEALTH INFO]\n"
            f"Allergies: {allergies}\n"
            f"Conditions: {conditions}"
        )

        appointment_data = {
            "patient_id": user_id,
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "user_email": user["email"],
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "doctor_name": doctor_name,
            "reason_for_visit": full_reason,
            "status": "Pending",
        }

        inserted = supabase.table("appointment").insert(appointment_data).execute()
        new_appointment_id = inserted.data[0]["id"]

        messages.success(request, "Appointment booked successfully!")
        return redirect("appointment_history")

    return render(request, "book_appointment.html", context)


def user_cancel_appointment(request, appointment_id):
    # 1. Check if user is logged in
    if not request.session.get("user_id"):
        return redirect("login")

    if request.method == "POST":
        reason = request.POST.get("reason") # Get the reason from the dropdown
        
        try:
            # 2. Fetch the appointment
            response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
            if not response.data:
                messages.error(request, "Appointment not found.")
                return redirect("user_dashboard")
            
            appointment = response.data
            
            # 3. SECURITY: Verify the logged-in user owns this appointment
            # We compare the session email with the appointment email
            if appointment["user_email"] != request.session.get("user_email"):
                 messages.error(request, "Unauthorized action. You can only cancel your own appointments.")
                 return redirect("user_dashboard")

            # 4. Update the status and (optionally) the reason
            # Note: Make sure your Supabase 'appointment' table has a 'reason' or 'cancellation_reason' column if you want to save the text.
            # If you don't have that column yet, just removing 'reason' from this dictionary will fix potential errors.
            update_data = {
                "status": "Cancelled",
                "reason_for_visit": f"CANCELLED: {reason} | Original: {appointment.get('reason_for_visit', '')}" 
                # ^ Since we might not have a 'cancellation_reason' column, we can append it to the visit reason or notes
            }
            
            supabase.table("appointment").update(update_data).eq("id", appointment_id).execute()
            
            messages.success(request, "Appointment cancelled successfully.")
            
        except Exception as e:
            print(f"Error cancelling appointment: {e}")
            messages.error(request, "Failed to cancel appointment. Please try again.")
            
    return redirect("user_dashboard")



# --- APPOINTMENT REGISTRATION --- @admin_required
@admin_required
def register_appointment(request):
    # [NEW] Prevent doctors from booking appointments manually
    if request.session.get("role") == "doctor":
        messages.error(request, "Doctors are not authorized to book appointments manually.")
        return redirect("appointment_list")

    today = date.today().isoformat()

    # --- Fetch Doctors Logic ---
    try:
        doctors_response = supabase.table("users").select(
            "id, first_name, last_name, is_in, doctors(specialization)"
        ).eq("is_doctor", True).execute()

        all_doctors_data = []
        for d in doctors_response.data or []:
            specialization = None
            if d.get("doctors"):
                if isinstance(d["doctors"], list) and d["doctors"]:
                    specialization = d["doctors"][0].get("specialization")
                elif isinstance(d["doctors"], dict):
                    specialization = d["doctors"].get("specialization")

            if specialization:
                all_doctors_data.append({
                    "id": d["id"],
                    "first_name": d["first_name"],
                    "last_name": d["last_name"],
                    "is_in": d.get("is_in", True),
                    "specialization": specialization
                })

        specializations = sorted(list({d["specialization"] for d in all_doctors_data}))
        
    except Exception as e:
        print(f"Error fetching doctors: {e}")
        all_doctors_data = []
        specializations = []
        messages.error(request, "Could not load doctor list.")

    context = {
        "doctors": all_doctors_data,
        "specializations": ["All"] + specializations,
        "today": today
    }

    # --- Handle Form Submission ---
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        doctor_name = request.POST.get("doctor_name")
        user_email = request.POST.get("user_email")
        appointment_date = request.POST.get("appointment_date")
        appointment_time = request.POST.get("appointment_time")
        reason_for_visit = request.POST.get("reason_for_visit")

        if not all([first_name, last_name, doctor_name, user_email, appointment_date, appointment_time, reason_for_visit]):
            messages.error(request, "All fields are required.")
            return render(request, "appointment_form.html", context)

        # Check doctor availability
        active_doctors = {f"{d['first_name']} {d['last_name']}" for d in all_doctors_data if d["is_in"]}
        if doctor_name not in active_doctors:
            messages.error(request, f"{doctor_name} is not available for booking.")
            return render(request, "appointment_form.html", context)

        # Prevent past-date bookings
        try:
            selected_date = date.fromisoformat(appointment_date)
            if selected_date < date.today():
                messages.error(request, "You cannot book appointments on past dates.")
                return render(request, "appointment_form.html", context)
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, "appointment_form.html", context)

        # Find patient by email
        try:
            patient_lookup = supabase.table("users").select("id").eq("email", user_email).single().execute()
            if not patient_lookup.data:
                messages.error(request, "No user exists with that email.")
                return render(request, "appointment_form.html", context)
            patient_id = patient_lookup.data["id"]
        except Exception:
            messages.error(request, "Error finding user by email.")
            return render(request, "appointment_form.html", context)

        # Check for double booking
        try:
            existing = supabase.table("appointment").select("*") \
                .eq("doctor_name", doctor_name) \
                .eq("appointment_date", appointment_date) \
                .eq("appointment_time", appointment_time) \
                .execute()
            if existing.data:
                messages.error(request, f"{doctor_name} is already booked at {appointment_time} on {appointment_date}.")
                return render(request, "appointment_form.html", context)
        except Exception as e:
            print("Error checking existing appointments:", e)
            messages.error(request, "Could not check existing appointments.")
            return render(request, "appointment_form.html", context)

        # Insert appointment
        try:
            appointment_data = {
                "patient_id": patient_id,
                "first_name": first_name,
                "last_name": last_name,
                "user_email": user_email,
                "doctor_name": doctor_name,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "reason_for_visit": reason_for_visit,
                "status": "Pending"
            }
            insert_res = supabase.table("appointment").insert(appointment_data).execute()
            new_app_id = insert_res.data[0]["id"]

            # Create patient record
            supabase.table("patient_records").insert({
                "user_id": patient_id,
                "appointment_id": new_app_id,
                "record_date": appointment_date,
                "successful_appointment_visit": False,
                "doctor_notes": "Appointment scheduled."
            }).execute()
        except Exception as e:
            print("Error saving appointment:", e)
            messages.error(request, "Could not save appointment due to server error.")
            return render(request, "appointment_form.html", context)

        messages.success(request, f"Appointment for {first_name} {last_name} successfully registered! Awaiting approval.")
        return redirect("appointment_list")

    return render(request, "appointment_form.html", context)




# ============================================================
# APPOINTMENT LIST & ADMIN ACTIONS
# ============================================================
# --- APPOINTMENT LIST ---
@admin_required
def appointment_list_page(request):
    """Displays appointments. If user is a doctor, shows ONLY their appointments."""
    try:
        # 1. Start the base query
        query = supabase.table("appointment").select("*").order("appointment_date", desc=False)

        # 2. Check if the user is a doctor
        if request.session.get("is_doctor"):
            user_id = request.session.get("user_id")
            
            # Fetch the doctor's name from the users table to match the appointment record
            user_info = supabase.table("users").select("first_name, last_name").eq("id", user_id).single().execute()
            
            if user_info.data:
                # Construct the name exactly as it is stored in the appointment table
                # (Assuming you store it as "First Last" in book_appointment)
                full_doctor_name = f"{user_info.data['first_name']} {user_info.data['last_name']}"
                
                # 3. Apply the filter
                query = query.eq("doctor_name", full_doctor_name)

        # 4. Execute the query (filtered or unfiltered)
        response = query.execute()
        appointments = response.data or []
        
        context = {"appointments": appointments}
        return render(request, "appointments.html", context)

    except Exception as e:
        print(f"DEBUG: Error fetching appointments: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, "appointments.html", {"appointments": []})


@admin_required
def approve_appointment(request, appointment_id):
    response = supabase.table("appointment").select("*").eq("id", appointment_id).execute()
    
    if response.data:
        appointment = response.data[0]
        if appointment["status"] == "Pending":
            supabase.table("appointment").update({"status": "Approved"}).eq("id", appointment_id).execute()
            try:
                full_name = f"{appointment['first_name']} {appointment['last_name']}"
                send_appointment_confirmation_email(
                    user_name=full_name,
                    user_email=appointment["user_email"],
                    doctor_name=appointment["doctor_name"],
                    appointment_date=appointment["appointment_date"],
                    appointment_time=appointment["appointment_time"],
                    status="Approved"
                )
            except Exception as e:
                print(f"Email error: {e}")
            messages.success(request, f"Appointment #{appointment_id} approved successfully!")
        else:
            messages.warning(request, f"Appointment #{appointment_id} is already approved.")
    else:
        messages.error(request, f"Appointment #{appointment_id} not found.")
    
    return redirect('appointment_list')


@admin_required
def decline_appointment(request, appointment_id):
    try:
        response = supabase.table("appointment").select("*").eq("id", appointment_id).execute()
        if response.data:
            appointment = response.data[0]
            supabase.table("appointment").update({"status": "Declined"}).eq("id", appointment_id).execute()
            try:
                full_name = f"{appointment['first_name']} {appointment['last_name']}"
                send_appointment_confirmation_email(
                    user_name=full_name,
                    user_email=appointment["user_email"],
                    doctor_name=appointment["doctor_name"],
                    appointment_date=appointment["appointment_date"],
                    appointment_time=appointment["appointment_time"],
                    status="Declined"
                )
            except Exception as e:
                print(f"Decline email error: {e}")
            messages.success(request, f"Appointment #{appointment_id} declined.")
        else:
            messages.error(request, f"Appointment #{appointment_id} not found.")
    except Exception as e:
        print(f"Error declining appointment: {e}")
        messages.error(request, "Failed to decline the appointment.")
    
    return redirect("appointment_list")


@admin_required
def reinstate_appointment(request, appointment_id):
    if not request.session.get("role") in ["admin", "superadmin"]:
        messages.error(request, "Unauthorized action.")
        return redirect("appointment_list")

    try:
        response = supabase.table("appointment").select("*").eq("id", appointment_id).execute()
        if not response.data:
            messages.error(request, f"Appointment #{appointment_id} not found.")
            return redirect("appointment_list")

        appointment = response.data[0]
        supabase.table("appointment").update({"status": "Approved"}).eq("id", appointment_id).execute()
        messages.success(request, "Appointment has been reinstated successfully.")

        try:
            full_name = f"{appointment.get('first_name')} {appointment.get('last_name')}"
            send_appointment_confirmation_email(
                user_name=full_name,
                user_email=appointment.get("user_email"),
                doctor_name=appointment.get("doctor_name"),
                appointment_date=appointment.get("appointment_date"),
                appointment_time=appointment.get("appointment_time"),
                status="Reinstated"
            )
        except Exception as e:
            print(f"Email send failure: {e}")
            messages.warning(request, "Appointment reinstated, but email failed to send.")
    except Exception as e:
        print(f"Error reinstating appointment: {e}")
        messages.error(request, "Failed to reinstate the appointment. Please try again.")

    return redirect("appointment_list")


@admin_required
def cancel_appointment(request, appointment_id):
    if not request.session.get("role") in ["admin", "superadmin"]:
        messages.error(request, "Unauthorized action.")
        return redirect("appointment_list")

    try:
        response = supabase.table("appointment").select("*").eq("id", appointment_id).execute()
        if not response.data:
            messages.error(request, f"Appointment #{appointment_id} not found.")
            return redirect("appointment_list")

        appointment = response.data[0]
        supabase.table("appointment").update({"status": "Cancelled"}).eq("id", appointment_id).execute()
        messages.success(request, "Appointment has been cancelled successfully.")

        try:
            full_name = f"{appointment.get('first_name')} {appointment.get('last_name')}"
            send_appointment_confirmation_email(
                user_name=full_name,
                user_email=appointment.get("user_email"),
                doctor_name=appointment.get("doctor_name"),
                appointment_date=appointment.get("appointment_date"),
                appointment_time=appointment.get("appointment_time"),
                status="Cancelled"
            )
        except Exception as e:
            print(f"Email send failure: {e}")
            messages.warning(request, "Appointment cancelled, but email failed to send.")
    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        messages.error(request, "Failed to cancel the appointment. Please try again.")

    return redirect("appointment_list")

# --- MARK APPOINTMENT COMPLETE (New from your old version) ---
@admin_required
def complete_appointment(request, appointment_id):
    # [CHANGED] Allow admins, superadmins, AND doctors
    allowed_roles = ["admin", "superadmin", "doctor"]
    if request.session.get("role") not in allowed_roles:
        messages.error(request, "Unauthorized action.")
        return redirect("appointment_list")

    try:
        # 1. Update Appointment Status
        supabase.table("appointment").update({"status": "Completed"}).eq("id", appointment_id).execute()

        # 2. Update Patient Record
        response = supabase.table('patient_records').update({
            'successful_appointment_visit': True,
            'doctor_notes': 'Appointment completed and visit logged.'
        }).eq('appointment_id', appointment_id).execute()
        
        messages.success(request, f"Appointment #{appointment_id} marked as Complete!")
            
    except Exception as e:
        print(f"DEBUG: Error completing appointment {appointment_id}: {str(e)}")
        messages.error(request, f"Failed to complete appointment: {str(e)}")
            
    return redirect("appointment_list")


# --- EDIT APPOINTMENT ---
@admin_required
def edit_appointment(request, appointment_id):
    try:
        # Fetch the appointment
        response = supabase.table("appointment").select("*").eq("id", appointment_id).single().execute()
        appointment = response.data

        if not appointment:
            messages.error(request, "Appointment not found.")
            return redirect("appointment_list")

        # Convert appointment_date to Python date object
        appt_date_str = appointment.get("appointment_date")
        if appt_date_str:
            appointment["appointment_date"] = datetime.strptime(appt_date_str[:10], "%Y-%m-%d").date()

        # Normalize appointment_time to 12-hour format with AM/PM
        appt_time_str = appointment.get("appointment_time")
        if appt_time_str:
            try:
                appt_time_obj = datetime.strptime(appt_time_str.strip(), "%I:%M %p")
            except:
                try:
                    appt_time_obj = datetime.strptime(appt_time_str.strip(), "%H:%M")
                except:
                    appt_time_obj = None
            if appt_time_obj:
                appointment["appointment_time"] = appt_time_obj.strftime("%I:%M %p")
            else:
                appointment["appointment_time"] = ""

        today = date.today()

        times = [
            "08:00 AM","08:30 AM","09:00 AM","09:30 AM","10:00 AM","10:30 AM",
            "11:00 AM","11:30 AM","12:00 PM","12:30 PM","01:00 PM","01:30 PM",
            "02:00 PM","02:30 PM","03:00 PM","03:30 PM","04:00 PM","04:30 PM",
            "05:00 PM"
        ]

        # Get booked times for selected date (excluding current appointment)
        booked_resp = supabase.table("appointment").select("appointment_time")\
            .neq("id", appointment_id).execute()
        booked_times = []
        for b in booked_resp.data:
            btime = b.get("appointment_time")
            if btime:
                try:
                    b_obj = datetime.strptime(btime.strip(), "%I:%M %p")
                except:
                    try:
                        b_obj = datetime.strptime(btime.strip(), "%H:%M")
                    except:
                        b_obj = None
                if b_obj:
                    booked_times.append(b_obj.strftime("%I:%M %p"))

        if request.method == "POST":
            new_date_str = request.POST.get("appointment_date")
            new_time_str = request.POST.get("appointment_time")

            if not new_date_str or not new_time_str:
                messages.error(request, "Please select both date and time.")
                return render(request, "edit_appointment.html", {
                    "appointment": appointment, "today": today, "times": times, "booked_times": booked_times
                })

            # Check if selected date & time is already booked
            conflict_resp = supabase.table("appointment").select("*")\
                .eq("appointment_date", new_date_str)\
                .eq("appointment_time", new_time_str)\
                .neq("id", appointment_id).execute()

            if conflict_resp.data:
                return render(request, "edit_appointment.html", {
                    "appointment": appointment, "today": today, "times": times,
                    "booked_times": booked_times,
                    "error_popup": f"Time {new_time_str} on {new_date_str} is already taken!"
                })

            # Update appointment
            supabase.table("appointment").update({
                "appointment_date": new_date_str,
                "appointment_time": new_time_str
            }).eq("id", appointment_id).execute()

            # --- Send reschedule email ---
            user_name = appointment.get("user_name")  # adjust to your DB column
            user_email = appointment.get("user_email")  # adjust to your DB column
            doctor_name = appointment.get("doctor_name")
            send_appointment_confirmation_email(
                user_name=user_name,
                user_email=user_email,
                doctor_name=doctor_name,
                appointment_date=new_date_str,
                appointment_time=new_time_str,
                status="Rescheduled"
            )

            messages.success(request, f"Appointment #{appointment_id} rescheduled to {new_date_str} at {new_time_str}.")
            return redirect("appointment_list")

        return render(request, "edit_appointment.html", {
            "appointment": appointment,
            "today": today,
            "times": times,
            "booked_times": booked_times
        })

    except Exception as e:
        print(f"Error editing appointment {appointment_id}: {e}")
        messages.error(request, "An unexpected error occurred.")
        return redirect("appointment_list")



# --- DELETE APPOINTMENT (Includes Foreign Key fix) ---
@admin_required
def delete_appointment(request, appointment_id):
    try:
        # [CHANGED] 1. Check status before deleting
        check_response = supabase.table("appointment").select("status").eq("id", appointment_id).single().execute()
        if check_response.data:
            status = check_response.data.get("status")
            if status != "Cancelled":
                messages.error(request, "Appointment must be Cancelled before it can be deleted.")
                return redirect("appointment_list")
        else:
            messages.error(request, "Appointment not found.")
            return redirect("appointment_list")

        # 2. Update patient records referencing this appointment_id to NULL
        supabase.table('patient_records').update({'appointment_id': None}).eq('appointment_id', appointment_id).execute()
        
        # 3. Safely delete the appointment.
        response = supabase.table("appointment").delete().eq("id", appointment_id).execute()
        
        if response.data:
            messages.success(request, f"Appointment #{appointment_id} deleted successfully.")
        else:
            messages.error(request, f"Could not delete appointment #{appointment_id}.")

    except Exception as e:
        print(f"DEBUG: Error deleting appointment {appointment_id}: {e}")
        messages.error(request, "Failed to delete appointment.")
    
    return redirect("appointment_list")


# ============================================================
# USER MANAGEMENT (ADMIN)
# ============================================================
@admin_required
def user_management_page(request):
    """Fetches all users, separates them into Doctors and Patients, excluding admins."""
    try:
        response = supabase.table("users").select("*").order("last_name", desc=False).execute()
        all_users = response.data or []

        # Doctors: only users where is_doctor=True (admins are excluded)
        doctors = [u for u in all_users if u.get('is_doctor') == True and not u.get('is_admin')]

        # Patients: users who are not doctors AND not admins
        patients = [u for u in all_users if not u.get('is_doctor') and not u.get('is_admin')]

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
# main/views.py

@admin_required
def admin_dashboard(request):
    try:
        user_id = request.session.get("user_id")
        is_doctor = request.session.get("is_doctor", False)

        # 1. Base counts (same as before)
        patient_res = supabase.table("users").select("id", count='exact').eq("is_doctor", False).eq("is_admin", False).execute()
        total_patients = patient_res.count or 0
        
        doc_res = supabase.table("users").select("id", count='exact').eq("is_doctor", True).execute()
        total_doctors = doc_res.count or 0

        active_doc_res = supabase.table("users").select("id", count='exact').eq("is_doctor", True).eq("is_in", True).execute()
        active_doctors = active_doc_res.count or 0
        
        appt_res = supabase.table("appointment").select("id", count='exact').execute()
        total_appointments = appt_res.count or 0

        # --- [NEW] DOCTOR FILTERING LOGIC ---
        pending_query = supabase.table("appointment").select("id", count='exact').eq("status", "Pending")
        recent_appt_query = supabase.table("appointment").select("*").order("appointment_date", desc=True).limit(5)

        if is_doctor:
            # Fetch doctor's full name to match the 'doctor_name' column in appointments
            # (Ideally, we would match by ID, but your system currently uses names)
            user_info = supabase.table("users").select("first_name, last_name").eq("id", user_id).single().execute()
            if user_info.data:
                full_doctor_name = f"{user_info.data['first_name']} {user_info.data['last_name']}"
                
                # Filter Pending Count
                pending_query = pending_query.eq("doctor_name", full_doctor_name)
                
                # Filter Recent List
                recent_appt_query = recent_appt_query.eq("doctor_name", full_doctor_name)

        # Execute the (potentially filtered) queries
        pending_res = pending_query.execute()
        pending_appointments = pending_res.count or 0

        appointments_res = recent_appt_query.execute()
        appointments = appointments_res.data or []
        # ------------------------------------

        recent_users_res = supabase.table("users").select("*").eq("is_admin", False).order("id", desc=True).limit(5).execute()
        recent_activity = recent_users_res.data or []

        context = {
            "total_patients": total_patients,
            "total_doctors": total_doctors,
            "active_doctors": active_doctors,
            "total_appointments": total_appointments,
            "pending_appointments": pending_appointments,
            "recent_activity": recent_activity, 
            "appointments": appointments, 
            "is_doctor": is_doctor, # Pass this so template can hide "Total Doctors" etc. if you want
        }
        return render(request, "admin_dashboard.html", context)

    except Exception as e:
        print(f"CRITICAL ERROR IN ADMIN DASHBOARD: {e}")
        messages.error(request, f"Could not load dashboard data: {e}")
        return render(request, "admin_dashboard.html", {
            "total_patients": 0, "total_doctors": 0, "active_doctors": 0,
            "total_appointments": 0, "pending_appointments": 0, 
            "recent_activity": [], "appointments": []
        })
    

# ... existing imports ...

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
        status_notifications = []

        # Counters
        total_count = 0
        pending_count = 0
        completed_count = 0

        for appt in all_appointments:
            try:
                appt_date = datetime.strptime(appt['appointment_date'], '%Y-%m-%d').date()
                
                # --- UPDATED DASHBOARD LOGIC ---
                # Show Future or Today, BUT EXCLUDE Completed AND Cancelled
                if appt_date >= today and appt.get('status') not in ['Completed', 'Cancelled']:
                    upcoming_appointments.append(appt)
                    
                    # Create Reminder if Approved AND within 3 days
                    if appt_date <= reminder_threshold and appt.get('status') == 'Approved':
                        reminders.append(appt)

                # Collect notifications for status changes
                if appt.get('status') in ['Pending', 'Approved', 'Declined', 'Cancelled', 'Reinstated']:
                    status_notifications.append(appt)

                # Increment counters
                total_count += 1
                if appt.get('status') == 'Pending':
                    pending_count += 1
                elif appt.get('status') == 'Completed':
                    completed_count += 1

            except ValueError:
                continue

        # Sort notifications by most recent date
        status_notifications = sorted(
            status_notifications, 
            key=lambda x: x.get('updated_at', x['appointment_date']), 
            reverse=True
        )[:5]

        context = {
            "user_email": user_email,
            "first_name": first_name,
            "appointments": upcoming_appointments,
            "reminders": reminders, 
            "status_notifications": status_notifications,
            "total_count": total_count,
            "pending_count": pending_count,
            "completed_count": completed_count,
        }
        return render(request, "user-dashboard.html", context)

    except Exception as e:
        print(f"Error: {e}")
        return render(request, "user-dashboard.html", {"appointments": [], "total_count": 0})


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
                
                # --- UPDATED LOGIC HERE ---
                # Show in history if:
                # 1. Date is in the past
                # 2. Status is 'Completed'
                # 3. Status is 'Cancelled' (This was missing!)
                if appt_date < today or appt.get('status') in ['Completed', 'Cancelled']:
                    past_appointments.append(appt)
            except ValueError:
                continue

        return render(request, "appointment_history.html", {"history": past_appointments})

    except Exception as e:
        print(f"Error: {e}")
        return redirect("user_dashboard")

    
def home(request):
    return render(request, "home.html")

def about(request):
    return render(request, "about.html")

def all_doctors(request):
    specialty = request.GET.get("specialty")

    try:
        # Fetch from doctors table AND join user info including is_in
        query = (
            supabase.table("doctors")
            .select("doctor_id, specialization, users!inner(first_name, last_name, email, is_in)")
        )

        if specialty and specialty.lower() != "all":
            query = query.eq("specialization", specialty)

        response = query.execute()
        doctors = response.data

        # Format output for template
        formatted_doctors = []
        for d in doctors:
            user = d.get("users", {})
            formatted_doctors.append({
                "doctor_id": d.get("doctor_id"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "email": user.get("email"),
                "specialization": d.get("specialization"),
                "is_in": user.get("is_in", False),  # status from users table
            })

    except Exception as e:
        print("Error fetching doctors:", e)
        formatted_doctors = []

    paginator = Paginator(formatted_doctors, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "all_doctors.html", {
        "doctors": page_obj,
        "selected_specialty": specialty,
    })

def privacy_page(request):
    return render(request, "privacy.html")

def delete_user(request, user_id):
    if request.method == "POST":
        if request.session.get("role") != "superadmin":
            messages.error(request, "You do not have permission to delete this user.")
            return redirect("user_management")

        try:
            # Delete user from the users table
            supabase.table("users").delete().eq("id", user_id).execute()
            messages.success(request, "User deleted successfully.")
        except Exception as e:
            print(f"Error deleting user: {e}")
            messages.error(request, "Failed to delete the user.")

    return redirect("user_management")

@admin_required
def get_booked_times(request):
    date_str = request.GET.get("date")
    appointment_id = request.GET.get("appointment_id")
    doctor_name = request.GET.get("doctor_name")  # new

    booked_times = []

    if date_str and doctor_name:
        query = supabase.table("appointment").select("appointment_time")\
            .eq("appointment_date", date_str)\
            .eq("doctor_name", doctor_name)
        if appointment_id:
            query = query.neq("id", appointment_id)
        resp = query.execute()

        for b in resp.data:
            btime = b.get("appointment_time")
            if btime:
                try:
                    b_obj = datetime.strptime(btime.strip(), "%I:%M %p")
                except:
                    try:
                        b_obj = datetime.strptime(btime.strip(), "%H:%M")
                    except:
                        b_obj = None
                if b_obj:
                    booked_times.append(b_obj.strftime("%I:%M %p"))

    return JsonResponse({"booked_times": booked_times})
