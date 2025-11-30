from django.core.mail import send_mail

def send_appointment_confirmation_email(user_name, user_email, doctor_name, appointment_date, appointment_time, status="Booked"):
    subject = f"Your MedLink Appointment {status}"

    if status == "Booked":
        action = "successfully booked"
    elif status == "Cancelled":
        action = "has been cancelled"
    elif status == "Reinstated":
        action = "has been reinstated"
    elif status == "Approved":
        action = "has been approved"
    else:
        action = "updated"

    message = f"""
Hi {user_name},

Your appointment {action}!

📅 Date: {appointment_date}
⏰ Time: {appointment_time}
👨‍⚕️ Doctor: {doctor_name}

Thank you for choosing MedLink!
"""

    try:
        send_mail(
            subject,
            message,
            None,  # uses DEFAULT_FROM_EMAIL automatically
            [user_email],
            fail_silently=False
        )
        return True
    except Exception as e:
        print("Email failed:", e)
        return False