import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_reset_email(to_email: str, pin: str):
    """
    Envía un correo con el PIN de 6 dígitos para recuperación de contraseña.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"ATENCIÓN: Credenciales SMTP no configuradas. El PIN para {to_email} es {pin}")
        return False
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Recuperación de Contraseña - Acompañar"
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = to_email

        html_content = f"""
        <html>
          <body>
            <h2>Recuperación de Contraseña</h2>
            <p>Hemos recibido una solicitud para restablecer tu contraseña.</p>
            <p>Tu código de seguridad de 6 dígitos es:</p>
            <h1 style="color: #4F46E5; letter-spacing: 5px;">{pin}</h1>
            <p>Este código expira en 15 minutos.</p>
            <p>Si no solicitaste este cambio, ignora este correo.</p>
            <br/>
            <p>El equipo de Acompañar.</p>
          </body>
        </html>
        """
        part = MIMEText(html_content, "html")
        msg.attach(part)

        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        if settings.SMTP_TLS:
            server.starttls()
            
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error al enviar correo a {to_email}: {e}")
        return False
