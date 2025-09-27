from django.http import HttpResponse
from django.shortcuts import render

def hello_page(request):
    return HttpResponse("Hello, Django Page!")

def login_page(request):
    return render(request, "login-student.html")

def register_page(request):
    return render(request, "register-student.html")

def forgot_password_page(request):
    return render(request, "forgot-password.html")

def home_page(request):
    return render(request, "home.html")
