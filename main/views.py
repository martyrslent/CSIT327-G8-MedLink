from django.http import HttpResponse
from django.shortcuts import render

def hello_page(request):
    return HttpResponse("Hello, Django Page!")

def login_page(request):
    return render(request, "login-student.html")

def register_page(request):
    from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages

def register_page(request):
    #the database in this rn is just a placeholder, i don't know the database yet.
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, "register-student.html")

        # check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "register-student.html")

        # create the user (saved to DB)
        user = User.objects.create_user(username=username, password=password)
        user.save()

        messages.success(request, "Account created successfully! Please log in.")
        return redirect("login")  

    return render(request, "register-student.html")

def forgot_password_page(request):
    return render(request, "forgot-password.html")

def home_page(request):
    return render(request, "home.html")
