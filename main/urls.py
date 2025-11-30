# main/urls.py
from django.urls import path
from . import views

urlpatterns = [
     # Home + Landing Page
    path("", views.home, name="home"),
    path("hello/", views.hello_page, name="hello"),
    # Authentication
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
    path("forgot-password/", views.forgot_password_page, name="forgot_password"),
    path("logout/", views.logout_page, name="logout"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("all-doctors/", views.all_doctors, name="all_doctors"),
    path("about/", views.about, name="about"),
    # --- User Side ---
    path("user-dashboard/", views.user_dashboard, name="user_dashboard"),
    path("history/", views.appointment_history, name="appointment_history"), # <--- NEW
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('profile/', views.profile_page, name='user_profile'),
    path('profile/upload-image/', views.update_profile_picture, name='update_profile_picture'),
    path('profile/update-info/', views.update_personal_info, name='update_personal_info'),
    
    # --- Admin / Staff Side ---
    path('register-appointment/', views.register_appointment, name='register_appointment'),
    path('register-staff/', views.register_admin_page, name='register_admin'),
    path('appointments/', views.appointment_list_page, name='appointment_list'),
    path('appointments/edit/<int:appointment_id>/', views.edit_appointment, name='edit_appointment'),
    path('appointments/delete/<int:appointment_id>/', views.delete_appointment, name='delete_appointment'),
    path('patient-records/', views.patient_records_list_page, name='patient_records_list'),
    path('users/', views.user_management_page, name='user_management'),
    path('users/edit/<int:user_id>/', views.edit_user_page, name='edit_user'),
    path('appointments/complete/<int:appointment_id>/', views.complete_appointment, name='complete_appointment'),
    path('appointments/cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/approve/<int:appointment_id>/', views.approve_appointment, name='approve_appointment'),
    path('appointments/decline/<int:appointment_id>/', views.decline_appointment, name='decline_appointment'),
    path("appointments/reinstate/<int:appointment_id>/", views.reinstate_appointment, name="reinstate_appointment"),
    
    # --- Settings ---
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),
    path('toggle-is-in/<int:user_id>/', views.toggle_is_in, name='toggle_is_in'),
]