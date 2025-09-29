from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .supabase_client import supabase  
def hello_page(request):
    return HttpResponse("Hello, Django Page!")

def login_page(request):
    return render(request, "login-student.html")

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
                "password": hashed_password
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