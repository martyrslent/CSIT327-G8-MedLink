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
            # ... (Supabase query logic is fine here, it succeeded in previous logs)
            response = supabase.table("users").select("*").eq("email", email).execute()
            print(f"DEBUG: Supabase response: {response.data}")

            if not response.data:
                # ... (error handling)
                messages.error(request, "Email not found!")
                return render(request, "login-student.html")

            user = response.data[0]
            print(f"DEBUG: Found user: {user}")

            if not check_password(password, user["password"]):
                # ... (error handling)
                messages.error(request, "Incorrect password!")
                return render(request, "login-student.html")

            print("DEBUG: Password check passed, setting session")
            request.session["user_id"] = user["id"]
            request.session["user_email"] = user["email"]
            request.session["is_admin"] = user.get("is_admin", False)
            request.session["first_name"] = user.get("first_name", "User")

            # 🛑 DIAGNOSTIC CHANGE: Temporary redirect for all users 🛑
            print("DIAGNOSTIC: Forcing redirect to user_dashboard for testing.")
            return redirect("user_dashboard")
            
            # --- Original Redirection Logic (Commented out) ---
            # if user.get("is_admin", False):
            #     print("DEBUG: User is admin, redirecting to admin_dashboard")
            #     return redirect("admin_dashboard")
            # else:
            #     print("DEBUG: User is normal user, redirecting to user_dashboard")
            #     return redirect("user_dashboard")

        except Exception as e:
            # ... (exception handling)
            print(f"DEBUG: Exception occurred: {str(e)}")
            messages.error(request, f"Unexpected error: {str(e)}")
            return render(request, "login-student.html")

    print("DEBUG: GET request received, rendering login page")
    return render(request, "login-student.html")

# --- (Rest of views.py remains unchanged, including your safe admin_dashboard and user_dashboard) ---

def admin_dashboard(request):
    if not request.session.get("is_admin"):
        return redirect("login")
    
    # This check confirms the client loaded, which it did in the logs.
    if supabase is None:
        print("FATAL: Supabase client is None, cannot query database.")
        return HttpResponse("Database connection error. Check server logs.", status=500)

    try:
        # 🛑 TEMPORARY WORKAROUND 🛑
        # Bypassing the Supabase query to prevent the low network timeout crash (500 error).
        print("DEBUG: Bypassing Supabase query to test redirect stability.")
        
        # NOTE: Using placeholder data to ensure the dashboard loads.
        total_patients = 150 
        new_registrations = 8

        # --- (Original code commented out below) ---
        # print("DEBUG: Attempting Supabase query for patient count...")
        # response = supabase.table("users").select("*").eq("is_admin", False).execute()
        # print("DEBUG: Supabase query successful.")
        # total_patients = len(response.data) if response.data else 0
        # new_registrations = total_patients
        # -------------------------------------------

        context = {
            "total_patients": total_patients,
            "total_appointments": 0,      # placeholder for now
            "recent_activity": [],        # placeholder
            "new_registrations": new_registrations,
        }
        
        return render(request, "admin_dashboard.html", context)

    except Exception as e:
        # This logging will now only fire if a Python error (not a Gunicorn crash) occurs.
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