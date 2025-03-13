from app import app, db  # Assicurati di importare app dal tuo progetto
from models import Cart, Booking

# 🔍 Recupera il carrello attivo per un utente specifico
def test_submit_cart_as_booking(user_id):
    with app.app_context():  # ✅ Imposta il contesto dell'applicazione
        try:
            # 🔄 Recupera il carrello attivo
            cart = Cart.query.filter_by(user_id=user_id, status='active').first()

            if not cart:
                print("❌ Nessun carrello attivo trovato per questo utente.")
                return

            # 🛒 Sottometti il carrello come prenotazione
            result = Booking.submit_cart_as_booking(cart)

            if "error" in result:
                print(f"❌ Errore durante la sottomissione: {result['error']}")
            else:
                print("✅ Prenotazione completata con successo.")
                print("📄 Dettagli della prenotazione:")
                for booking in result["bookings"]:
                    print(f" - Booking ID: {booking['booking_id']}, Codice: {booking['generated_code']}")

        except Exception as e:
            print(f"❌ Errore generale: {str(e)}")

# 🔥 Test del metodo con un utente specifico (cambia l'ID con uno valido)
test_submit_cart_as_booking(user_id=39)
