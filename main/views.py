
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .supabase_client import supabase
from django.contrib.auth.hashers import check_password
from supabase import create_client, Client
from django.urls import reverse, NoReverseMatch

def hello_page(request):
    return HttpResponse("Hello, Django Page!")

def register_admin_page(request):
    # Security check: Only existing admins should be able to create new admins
    if not request.session.get("is_admin"):
        messages.error(request, "Access denied. Only existing administrators can add new staff.")
        return redirect("login")
    
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
            # 1. Check if email already exists
            response = supabase.table(table_name).select("email").eq("email", email).execute()
            if response.get('data') and len(response['data']) > 0:
                messages.error(request, "Email already registered!")
                return render(request, "register-admin.html")

            # 2. Hash Password
            hashed_password = make_password(password)

            # 3. Insert new staff member (CRITICAL: is_admin is True)
            response = supabase.table(table_name).insert({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_admin": True  # <--- THIS IS THE KEY DIFFERENCE
            }).execute()

            # 4. Check for Supabase Error (using the robust check from before)
            if isinstance(response, dict) and 'error' in response:
                error_message = f"Supabase Error: {response['error'].get('message', 'Unknown error')}"
                print(f"DEBUG: Staff insertion failed - {error_message}")
                messages.error(request, error_message)
                return render(request, "register-admin.html")

            messages.success(request, f"New staff member {first_name} added successfully! They can now log in.")
            return redirect("admin_dashboard") # Redirect back to the dashboard

        except Exception as e:
            messages.error(request, "Unexpected error: " + str(e))
            return render(request, "register-admin.html")

    return render(request, "register-admin.html")

def register_appointment(request):
    # Security check: only allow admins to book appointments from this page
    if not request.session.get("is_admin"):
        messages.error(request, "Access denied. Please log in as an administrator.")
        return redirect("login") 

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        appointment_date = request.POST.get("appointment_date")

        # Basic server-side validation
        if not all([first_name, last_name, appointment_date]):
            messages.error(request, "All fields are required!")
            return render(request, "appointment_form.html")

        # Supabase Data Structure (assuming your 'appointment' table has these columns)
        appointment_data = {
            "first_name": first_name,
            "last_name": last_name,
            "appointment_date": appointment_date, # This will be inserted as a date/timestamp type
            # You might add an admin_id or created_by field here using request.session.get("user_id")
        }

        try:
            # Insert the new appointment record into the 'appointment' table
            response = (
                supabase.table("appointment")
                .insert(appointment_data)
                .execute()
            )
            
            if isinstance(response, dict) and 'error' in response:
                error_message = f"Supabase Error: {response['error'].get('message', 'Unknown error')}"
                print(f"DEBUG: Supabase Insertion Failed - {error_message}")
                messages.error(request, error_message)
                return render(request, "appointment_form.html")

            messages.success(request, f"Appointment for {first_name} {last_name} on {appointment_date} successfully registered!")
            return redirect("admin_dashboard")

        except Exception as e:
            # This handles generic network or client-side errors
            print(f"DEBUG: Critical error during appointment registration: {str(e)}")
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return render(request, "appointment_form.html")

    # Handle GET request (initial page load)
    return render(request, "appointment_form.html")

def login_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        print("DEBUG: Received POST request")
        print(f"DEBUG: email={email}, password={'*' * len(password) if password else None}")

        if not email or not password:
            print("DEBUG: Missing email or password")
            messages.error(request, "Please fill in all fields!")
            return render(request, "login-student.html")

        try:
            print(f"DEBUG: Querying Supabase for email '{email}'")
            response = supabase.table("users").select("*").eq("email", email).execute()
            print(f"DEBUG: Supabase response: {response.data}")

            if not response.data:
                print("DEBUG: No user found with this email")
                messages.error(request, "Email not found!")
                return render(request, "login-student.html")

            user = response.data[0]
            print(f"DEBUG: Found user: {user}")

            if not check_password(password, user["password"]):
                print("DEBUG: Password check failed")
                messages.error(request, "Incorrect password!")
                return render(request, "login-student.html")

            print("DEBUG: Password check passed, setting session")
            request.session["user_id"] = user["id"]
            request.session["user_email"] = user["email"]
            request.session["is_admin"] = user.get("is_admin", False)
            request.session["first_name"] = user.get("first_name", "User")

            if user.get("is_admin", False):
                print("DEBUG: User is admin, redirecting to admin_dashboard")
                return redirect("admin_dashboard")
            else:
                print("DEBUG: User is normal user, redirecting to user_dashboard")
                return redirect("user_dashboard")

        except Exception as e:
            print(f"DEBUG: Exception occurred: {str(e)}")
            messages.error(request, f"Unexpected error: {str(e)}")
            return render(request, "login-student.html")

    print("DEBUG: GET request received, rendering login page")
    return render(request, "login-student.html")


def admin_dashboard(request):
    if not request.session.get("is_admin"):
        return redirect("login")

    try:
        # The complex Supabase interaction happens here.
        response = supabase.table("users").select("*").eq("is_admin", False).execute()
        total_patients = len(response.data) if response.data else 0

        new_registrations = total_patients

        context = {
            "total_patients": total_patients,
            "total_appointments": 0,    # placeholder for now
            "recent_activity": [],      # placeholder
            "new_registrations": new_registrations,
        }
        return render(request, "admin_dashboard.html", context)

    except Exception as e:
        # CRITICAL DEBUGGING LINES ADDED HERE
        print(f"CRITICAL ERROR IN ADMIN DASHBOARD: {e}")
        return HttpResponse(f"Admin Dashboard Crash: {e}", status=500)

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

            if response.error:
                messages.error(request, "Error creating account: " + str(response.error))
                return render(request, "register-student.html")

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
        # Example context; customize as needed
        context = {
            "user_email": request.session.get("user_email"),
            "first_name": request.session.get("first_name", "User"),
        }
        return render(request, "user_dashboard.html", context)

    except Exception as e:
        # CRITICAL DEBUGGING LINES ADDED HERE
        print(f"CRITICAL ERROR IN USER DASHBOARD: {e}")
        return HttpResponse(f"User Dashboard Crash: {e}", status=500)
