import smtplib
import ssl
import os
from email.message import EmailMessage

def send_appointment_confirmation_email(user_name, user_email, doctor_name, appointment_date, appointment_time):
    """
    Sends an appointment confirmation email to the user using smtplib.
    """
    
    # Get email credentials from environment variables
    email_sender = os.environ.get('YOUR_EMAIL_USER')
    email_password = os.environ.get('YOUR_EMAIL_PASS')

    # Failsafe if credentials are not set
    if not email_sender or not email_password:
        print("❌ ERROR: Email credentials (YOUR_EMAIL_USER, YOUR_EMAIL_PASS) are not set in your environment variables.")
        return

    # Set the recipient
    email_receiver = user_email

    # Create the email content
    subject = 'Your MedLink Appointment Confirmation'
    body = f"""
Hi {user_name},

Your appointment has been successfully booked!

📅 Date: {appointment_date}
⏰ Time: {appointment_time}
👨‍⚕️ Doctor: {doctor_name}

Thank you for choosing MedLink!
"""

    # Create the EmailMessage object
    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = email_receiver
    em['Subject'] = subject
    em.set_content(body)

    # Add SSL context for a secure connection
    context = ssl.create_default_context()

    try:
        # We use SMTP_SSL for port 465
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo() 
            smtp.starttls(context=context) # Encrypts the connection after the initial handshake
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, email_receiver, em.as_string())
        print(f"✅ Successfully sent appointment confirmation to {user_email}")

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
