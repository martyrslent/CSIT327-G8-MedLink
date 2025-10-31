from django.urls import path
from . import views

urlpatterns = [
    path('hello/', views.hello_page, name='hello'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path('forgot-password/', views.forgot_password_page, name='forgot_password'),
    path('', views.register_page, name='register'),
    path("logout/", views.logout_page, name="logout"),
    path("user-dashboard/", views.user_dashboard, name="user_dashboard"),
    path('register-appointment/', views.register_appointment, name='register_appointment'),
]