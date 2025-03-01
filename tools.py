import random
from flask_mail import Message
from extensions import mail  # Importa mail da extensions.py

def generate_code():
    """Genera un codice a 8 cifre."""
    return ''.join(random.choices('0123456789', k=8))

def send_confirmation_code(email):
    """
    Funzione che genera un codice di conferma e lo invia via email.
    :param email: Email del destinatario.
    :return: Il codice generato.
    """
    confirmation_code = generate_code()

    msg = Message(
        subject="Conferma Ordine",
        recipients=[email],
        body=f"Il tuo codice di conferma è: {confirmation_code}"
    )
    mail.send(msg)

    return confirmation_code
