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

        table_name = "users"

        try:
            print(f"DEBUG: Querying Supabase table '{table_name}' for email '{email}'")
            response = supabase.table(table_name).select("*").eq("email", email).execute()
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
            else:
                print("DEBUG: Password check passed")

            request.session["user_id"] = user["id"]
            request.session["user_email"] = user["email"]
            request.session["is_admin"] = user.get("is_admin", False)
            print("DEBUG: User session set successfully")

            try:
                if user.get("is_admin", False):
                    print("DEBUG: User is admin, redirecting")
                    return redirect("admin_dashboard")
                else:
                    print("DEBUG: User is normal user, redirecting")
                    # Replace "user_dashboard" with a valid URL name if it exists
                    return redirect("register")  # fallback to register page for now

            except NoReverseMatch as e:
                print(f"DEBUG: Redirect failed: {e}")
                messages.error(request, f"Redirect failed: {e}")
                return render(request, "login-student.html")

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
        response = supabase.table("users").select("*").eq("is_admin", False).execute()
        total_patients = len(response.data) if response.data else 0

        new_registrations = total_patients

        context = {
            "total_patients": total_patients,
            "total_appointments": 0,   # placeholder for now
            "recent_activity": [],     # placeholder
            "new_registrations": new_registrations,
        }

    except Exception as e:
        context = {
            "total_patients": "Error",
            "error_message": str(e),
        }

    return render(request, "admin_dashboard.html", context)

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
    
    # Example context; customize as needed
    context = {
        "user_email": request.session.get("user_email"),
        "first_name": request.session.get("first_name", "User"),
    }
    return render(request, "user_dashboard.html", context)