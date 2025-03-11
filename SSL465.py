import smtplib

EMAIL_HOST = "alabama.o2switch.net"
EMAIL_PORT = 587
EMAIL_HOST_USER = "cyberh@dlxi7823.odns.fr"
EMAIL_HOST_PASSWORD = "Ld(hfnbK5cvO"

try:
    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    message = "Subject: Test Email\n\nHello, this is a test email!"
    server.sendmail(EMAIL_HOST_USER, "norman.marie-marthe@cyberun.info", message)
    server.quit()
    print("✅ Email envoyé avec succès")
except Exception as e:
    print(f"❌ Erreur: {e}")

# Ce fichier peut être supprimé car il est vide et inutile
