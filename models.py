from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal
from sqlalchemy import and_, or_
from datetime import datetime
from datetime import timedelta
from sqlalchemy.exc import SQLAlchemyError
import json, hashlib
from werkzeug.security import generate_password_hash
from flask_mail import Message  # Importa Message per l'email
from extensions import mail  # Importa mail dall'estensione di Flask-Mail

# Usa l'istanza di db definita in app.py
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(512), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(50), default="user")
    bday = db.Column(db.Date, nullable=False)  # Nuovo campo: data di nascita
    place = db.Column(db.String(100), nullable=False)  # Nuovo campo: luogo di nascita
    register_ts = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp di registrazione

    def __init__(self, name, surname, password, email, bday, place, role="user"):
        self.name = name
        self.surname = surname
        self.password = password
        self.email = email
        self.bday = bday
        self.place = place
        self.role = role  # Ora usa il valore passato o "user" di default
        self.register_ts = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'surname': self.surname,
            'email': self.email,
            'bday': self.bday.strftime('%Y-%m-%d') if self.bday else None,  # Gestisce il caso None
            'place': self.place,
            'role': self.role,
            'register_ts': self.register_ts.strftime('%Y-%m-%d %H:%M:%S') if self.register_ts else None  # Gestisce il caso None
        }

    # Aggiungere un nuovo utente
    @staticmethod
    def add_user(name, surname, password, email, bday, place, role="user"):
        # 🔒 Genera l'hash una sola volta
        hashed_password = generate_password_hash(password)
        # print(Password Hash Generata:", hashed_password)

        new_user = User(
            name=name,
            surname=surname,
            password=hashed_password,  # Usa l'hash generato
            email=email,
            bday=bday,
            place=place,
            role=role
        )

        # 🔍 Verifica immediata prima di salvare
        # print(🔍 Hash prima di salvare:", new_user.password)

        db.session.add(new_user)
        db.session.commit()

        # 🔍 Controllo immediato dopo il commit
        saved_user = User.find_by_email(email)
        # print(🔍 Hash salvato nel DB:", saved_user.password)

        return new_user.to_dict()

    # Trovare un utente tramite email
    @staticmethod
    def find_by_email(email):
        return User.query.filter_by(email=email).first()

    # Trovare solo l'ID di un utente tramite email
    @staticmethod
    def find_user_id_by_email(email):
        user = User.query.filter_by(email=email).first()
        return user.id if user else None

    # Restituire tutti gli utenti
    @staticmethod
    def get_all_users():
        return [user.to_dict() for user in User.query.all()]

    # 🔄 Modificare i dettagli di un utente senza aggiornare la password e il ruolo
    @staticmethod
    def update_user(user_id, name=None, surname=None, email=None, bday=None, place=None):
        user = User.query.get(user_id)
        if user:
            if name:
                user.name = name
            if surname:
                user.surname = surname
            if email:
                user.email = email
            if bday:
                user.bday = bday
            if place:
                user.place = place

            # Commit solo se c'è stata una modifica
            db.session.commit()
            return user.to_dict()

        return None  # Se l'utente non esiste

    # Eliminare un utente
    @staticmethod
    def delete_user(user_id):
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return {"message": "User deleted successfully"}
        return {"error": "User not found"}

    @staticmethod
    def is_email_registered(email):
        return User.query.filter_by(email=email).first() is not None

    @staticmethod
    def change_role(user_id, new_role):
        user = User.query.get(user_id)
        if user:
            user.role = new_role
            db.session.commit()
            return True
        return False

    def is_admin(self):
        return self.role == "admin"

    @staticmethod
    def send_welcome_email(user):
        msg = Message("Benvenuto nel sito!", recipients=[user.email])
        msg.body = f"Ciao {user.name}, grazie per esserti registrato!"
        mail.send(msg)

    @staticmethod
    def count_users():
        return User.query.count()

    @staticmethod
    def search_users(keyword):
        return [user.to_dict() for user in User.query.filter(
            or_(
                User.name.ilike(f"%{keyword}%"),
                User.surname.ilike(f"%{keyword}%")
            )
        ).all()]

    @staticmethod
    def find_by_name_and_surname(name, surname):

        return [user.to_dict() for user in User.query.filter(
            and_(
                User.name.ilike(f"%{name}%"),
                User.surname.ilike(f"%{surname}%")
            )
        ).all()]

    def send_email(self, subject, body):
        try:
            msg = Message(
                subject=subject,
                recipients=[self.email],  # 📧 Email dell'utente
                body=body
            )
            mail.send(msg)
            return {"message": "Email inviata con successo."}
        except SQLAlchemyError as e:
            return {"error": f"Errore durante l'invio dell'email: {str(e)}"}
        except Exception as e:
            return {"error": f"Errore generale: {str(e)}"}
    
class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vehicle_type = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price_per_hour = db.Column(db.Numeric(10, 2), nullable=False)
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    driving_license = db.Column(db.String(10), nullable=False)
    power = db.Column(db.String(50), nullable=True)
    engine_size = db.Column(db.Numeric(5, 1), nullable=True)
    fuel_type = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    deposit = db.Column(db.Numeric(10, 2), nullable=False)

    def __init__(self, vehicle_type, brand, model, year, price_per_hour, license_plate, driving_license,
                 power=None, engine_size=None, fuel_type=None, is_active=True, description=None, image_url=None, deposit=0.0):
        self.vehicle_type = vehicle_type
        self.brand = brand
        self.model = model
        self.year = year
        self.price_per_hour = price_per_hour
        self.license_plate = license_plate
        self.driving_license = driving_license
        self.power = power
        self.engine_size = engine_size
        self.fuel_type = fuel_type
        self.is_active = is_active
        self.description = description
        self.image_url = image_url
        self.deposit = deposit

    def to_dict(self):
        return {
            'id': self.id,
            'vehicle_type': self.vehicle_type,
            'brand': self.brand,
            'model': self.model,
            'year': self.year,
            'price_per_hour': float(self.price_per_hour),
            'license_plate': self.license_plate,
            'driving_license': self.driving_license,
            'power': self.power,
            'engine_size': float(self.engine_size) if self.engine_size else None,
            'fuel_type': self.fuel_type,
            'is_active': self.is_active,
            'description': self.description,
            'image_url': self.image_url,
            'deposit': float(self.deposit)
        }

    # ➕ Aggiungere un nuovo veicolo
    @staticmethod
    def add_vehicle(vehicle_type, brand, model, year, price_per_hour, license_plate, driving_license,
                    power=None, engine_size=None, fuel_type=None, description=None, image_url=None, deposit=0.0):
        new_vehicle = Vehicle(
            vehicle_type=vehicle_type,
            brand=brand,
            model=model,
            year=year,
            price_per_hour=price_per_hour,
            license_plate=license_plate,
            driving_license=driving_license,
            power=power,
            engine_size=engine_size,
            fuel_type=fuel_type,
            description=description,
            image_url=image_url,
            deposit=deposit
        )
        db.session.add(new_vehicle)
        db.session.commit()
        return new_vehicle.to_dict()

    # 🔍 Trovare un veicolo tramite targa
    @staticmethod
    def find_by_license_plate(license_plate):
        return Vehicle.query.filter_by(license_plate=license_plate).first()

    # 🔍 Trovare un veicolo tramite ID
    @staticmethod
    def find_by_id(vehicle_id):
        return Vehicle.query.get(vehicle_id)

    # 📋 Restituire tutti i veicoli attivi
    @staticmethod
    def get_all_active_vehicles():
        return [vehicle.to_dict() for vehicle in Vehicle.query.filter_by(is_active=True).all()]

    # 🔄 Aggiornare i dettagli di un veicolo
    @staticmethod
    def update_vehicle(vehicle_id, **kwargs):
        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle:
            for key, value in kwargs.items():
                if hasattr(vehicle, key):
                    setattr(vehicle, key, value)
            db.session.commit()
            return vehicle.to_dict()
        return None

    # Eliminare un veicolo
    @staticmethod
    def delete_vehicle(vehicle_id):
        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle:
            db.session.delete(vehicle)
            db.session.commit()
            return {"message": "Veicolo eliminato con successo"}
        return {"error": "Veicolo non trovato"}

    # 🔍 Ricerca avanzata per filtro
    @staticmethod
    def search_vehicles(keyword):
        return [vehicle.to_dict() for vehicle in Vehicle.query.filter(
            or_(
                Vehicle.brand.ilike(f"%{keyword}%"),
                Vehicle.model.ilike(f"%{keyword}%"),
                Vehicle.vehicle_type.ilike(f"%{keyword}%"),
                Vehicle.fuel_type.ilike(f"%{keyword}%")
            )
        ).all()]

    # 🔧 Attivare o disattivare un veicolo
    @staticmethod
    def toggle_active_status(vehicle_id):
        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle:
            vehicle.is_active = not vehicle.is_active
            db.session.commit()
            return vehicle.to_dict()
        return None

    # 💰 Calcolare il costo totale del noleggio
    @staticmethod
    def calculate_rental_cost(vehicle_id, hours):
        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle:
            return round(vehicle.price_per_hour * hours + vehicle.deposit, 2)
        return None

    # 🔍 Filtrare i veicoli disponibili per tipo
    @staticmethod
    def filter_by_type(vehicle_type):
        return [vehicle.to_dict() for vehicle in Vehicle.query.filter_by(vehicle_type=vehicle_type, is_active=True).all()]

    # 🔍 Filtrare veicoli per tipo di patente
    @staticmethod
    def filter_by_driving_license(license_type):
        """
        Restituisce tutti i veicoli attivi che richiedono un tipo specifico di patente.

        Args:
            license_type (str): Il tipo di patente richiesto (es. 'A', 'B', 'C').

        Returns:
            list: Un elenco di veicoli sotto forma di dizionari.
        """
        vehicles = Vehicle.query.filter_by(driving_license=license_type, is_active=True).all()
        return [vehicle.to_dict() for vehicle in vehicles]
    
    @staticmethod
    def get_available_vehicles_in_range(start_date, end_date):
        """
        Restituisce tutti i veicoli che NON sono prenotati in un determinato intervallo di date.
        """
        conflicting_vehicles = db.session.query(Booking.bike_id).filter(
            Booking.status == True,  # Solo prenotazioni attive
            or_(
                (Booking.start_date <= start_date) & (Booking.end_date >= start_date),
                (Booking.start_date <= end_date) & (Booking.end_date >= end_date),
                (Booking.start_date >= start_date) & (Booking.end_date <= end_date)
            )
        ).subquery()  # Subquery per ottenere gli ID delle moto prenotate

        # Recupera i veicoli che NON sono nella lista delle prenotazioni in conflitto
        available_vehicles = Vehicle.query.filter(
            Vehicle.id.notin_(conflicting_vehicles),
            Vehicle.is_active == True
        ).all()

        return [vehicle.to_dict() for vehicle in available_vehicles]

    # 🔍 Filtrare per fascia di prezzo
    @staticmethod
    def filter_by_price_range(min_price, max_price):
        return [vehicle.to_dict() for vehicle in Vehicle.query.filter(
            Vehicle.price_per_hour.between(min_price, max_price), Vehicle.is_active == True
        ).all()]
 
class Cart(db.Model):
    __tablename__ = 'carts'

    cart_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    items_id_list = db.Column(db.Text, default=json.dumps([]))
    final_price = db.Column(db.Numeric(10, 2), default=0.0)
    status = db.Column(db.Enum('active', 'completed', 'cancelled'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ➕ Crea un nuovo carrello
    @staticmethod
    def create_cart(user_id):
        new_cart = Cart(
            user_id=user_id,
            items_id_list=json.dumps([]),
            final_price=0.0,
            status='active'
        )
        db.session.add(new_cart)
        db.session.commit()
        return new_cart.to_dict()

    # 🔍 Controllo conflitti di date senza restituire il prodotto
    def check_date_conflict(self, start_date, end_date):
        # Verifica sovrapposizioni di date
        conflicting_items = CartItem.query.filter(
            CartItem.cart_id == self.cart_id,
            or_(
                # Il nuovo intervallo si sovrappone parzialmente o totalmente
                (CartItem.start_date <= start_date) & (CartItem.end_date >= start_date),
                (CartItem.start_date <= end_date) & (CartItem.end_date >= end_date),
                (CartItem.start_date >= start_date) & (CartItem.end_date <= end_date)
            )
        ).all()

        # Restituisci solo un messaggio di errore in caso di conflitto
        if conflicting_items:
            return {
                "error": "Il prodotto non può essere aggiunto: le date selezionate si sovrappongono a un altro prodotto nel carrello."
            }

        return None
    
    @staticmethod
    def is_bike_booked(moto_id, start_date, end_date):
        """
        Controlla se una moto è già prenotata in un intervallo di date.
        
        Args:
            moto_id (int): ID della moto da controllare.
            start_date (datetime): Data di inizio della prenotazione richiesta.
            end_date (datetime): Data di fine della prenotazione richiesta.
        
        Returns:
            bool: True se la moto è già prenotata, False altrimenti.
        """
        conflicting_bookings = Booking.query.filter(
            Booking.bike_id == moto_id,
            Booking.status == True,  # Solo prenotazioni attive
            or_(
                # La nuova prenotazione si sovrappone con una esistente
                (Booking.start_date <= start_date) & (Booking.end_date >= start_date),
                (Booking.start_date <= end_date) & (Booking.end_date >= end_date),
                (Booking.start_date >= start_date) & (Booking.end_date <= end_date)
            )
        ).all()

        return len(conflicting_bookings) > 0

    # 🔍 Recupera un carrello tramite ID
    @staticmethod
    def get_cart_by_id(cart_id):
        cart = Cart.query.get(cart_id)
        return cart.to_dict() if cart else None

    # 🔍 Recupera tutti i carrelli di un utente
    @staticmethod
    def get_carts_by_user(user_id):
        carts = Cart.query.filter_by(user_id=user_id).all()
        return [cart.to_dict() for cart in carts]

    def add_item(self, moto_id, start_date, end_date, price, accessories=None):
        if self.status != 'active':
            return {"error": "Non è possibile aggiungere oggetti a un carrello non attivo."}

        # Log di debug
        print("Aggiunta al carrello: ", {
            "moto_id": moto_id,
            "start_date": start_date,
            "end_date": end_date,
            "price": price,
            "accessories": accessories
        })

        # 🔍 Controlla conflitti di date
        conflict = self.check_date_conflict(start_date, end_date)
        if conflict:
            return conflict

        # Serializza gli accessori come JSON
        try:
            serialized_accessories = json.dumps(accessories if accessories else [])
        except Exception as e:
            return {"error": f"Accessori non validi: {str(e)}"}

        # ➕ Aggiungi il nuovo prodotto se non ci sono conflitti
        new_item = CartItem(
            cart_id=self.cart_id,
            moto_id=moto_id,
            start_date=start_date,
            end_date=end_date,
            price=Decimal(str(price)),
            accessories=serialized_accessories
        )

        db.session.add(new_item)
        db.session.commit()

        # 🔥 Aggiorna il prezzo totale
        self.final_price += Decimal(str(price))
        db.session.commit()

        return new_item.to_dict()

    def get_detailed_user_cart(self):
        return {
            "cart_id": self.cart_id,
            "user_id": self.user_id,
            "items": [
                {
                    "item_id": item.item_id,
                    "moto_id": item.moto_id,
                    "start_date": item.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "end_date": item.end_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "price": float(item.price),
                    "accessories": item.accessories,
                    "moto_details": self.get_moto_details(item.moto_id)
                }
                for item in CartItem.query.filter_by(cart_id=self.cart_id).all()
            ],
            "final_price": float(self.final_price),
            "status": self.status,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_moto_details(self, moto_id):
    # 🔍 Recupera i dettagli della moto usando il metodo della classe Vehicle
        moto = Vehicle.find_by_id(moto_id)
        if moto:
            return moto.to_dict()
        return None

    def get_user_cart(self):
        return {
            "cart_id": self.cart_id,
            "user_id": self.user_id,
            "items": [
                {
                    "item_id": item.item_id,
                    "moto_id": item.moto_id,
                    "start_date": item.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "end_date": item.end_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "price": float(item.price),
                    "accessories": item.accessories
                }
                for item in CartItem.query.filter_by(cart_id=self.cart_id).all()
            ],
            "final_price": float(self.final_price),
            "status": self.status,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # Cancella un prodotto dal carrello
    def remove_item(self, item_id):
        if self.status != 'active':
            return {"error": "Non è possibile rimuovere oggetti da un carrello non attivo."}

        # 🔍 Verifica se l'oggetto esiste nel carrello
        item = CartItem.query.filter_by(cart_id=self.cart_id, item_id=item_id).first()
        if not item:
            return {"error": "Oggetto non trovato nel carrello."}

        # 🗑️ Rimuovi l'oggetto dal carrello
        db.session.delete(item)
        db.session.commit()

        return {"message": "Oggetto rimosso con successo dal carrello."}
    
    # 🔄 Completa il carrello
    def complete_cart(self):
        if self.status != 'active':
            return {"error": "Il carrello non è attivo."}

        self.status = 'completed'
        db.session.commit()
        return self.to_dict()

    # Annulla il carrello
    def cancel_cart(self):
        if self.status != 'active':
            return {"error": "Il carrello non è attivo."}

        self.status = 'cancelled'
        db.session.commit()
        return self.to_dict()

    # 🗑️ Elimina tutti i prodotti dal carrello
    def clear_cart(self):
        if self.status != 'active':
            return {"error": "Il carrello non è attivo."}

        try:
            # 🔍 Recupera tutti gli oggetti del carrello
            cart_items = CartItem.query.filter_by(cart_id=self.cart_id).all()

            if not cart_items:
                return {"error": "Il carrello è già vuoto."}

            # 🗑️ Rimuove tutti gli oggetti del carrello
            for item in cart_items:
                db.session.delete(item)

            # 🔄 Resetta il prezzo finale e aggiorna il carrello
            self.final_price = 0.0
            self.items_id_list = "[]"
            db.session.commit()

            return {
                "message": "Tutti i prodotti sono stati rimossi dal carrello.",
                "cart_id": self.cart_id
            }

        except SQLAlchemyError as e:
            db.session.rollback()  # Rollback in caso di errore
            return {"error": f"Errore durante la cancellazione degli oggetti dal carrello: {str(e)}"}

    # 🔍 Ottieni gli oggetti del carrello
    def get_cart_items(self):
        items = CartItem.query.filter_by(cart_id=self.cart_id).all()
        return [item.to_dict() for item in items]

    # 🔄 Sottometti il carrello come ordine e genera automaticamente un codice
    def submit_cart_as_order(self, extra_data):
        if self.status != 'active':
            return {"error": "Il carrello non è attivo."}

        cart_items = self.get_cart_items()

        if not cart_items:
            return {"error": "Il carrello è vuoto."}

        try:
            booking_codes = []  # Lista per tenere traccia dei codici generati

            for item_data in cart_items:
                # 🛒 Crea una prenotazione
                new_booking = Booking(
                    bike_id=item_data["moto_id"],
                    customer_id=self.user_id,
                    start_date=datetime.strptime(item_data["start_date"], "%Y-%m-%d %H:%M:%S"),
                    end_date=datetime.strptime(item_data["end_date"], "%Y-%m-%d %H:%M:%S"),
                    total_price=item_data["price"],
                    accessories=item_data.get("accessories", "[]"),
                    dl_type=extra_data.get("dl_type", "A"),
                    dl_expiration=datetime.strptime(extra_data.get("dl_expiration", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d"),
                    dl_number=extra_data.get("dl_number", "DL000000"),
                    helmet_size=extra_data.get("helmet_size", "M"),
                    gloves_size=extra_data.get("gloves_size", "M"),
                    pickup=item_data.get("pickup", False),
                    return_=item_data.get("return_", False),
                    status=True,
                    payment_status=False
                )
                db.session.add(new_booking)
                db.session.flush()  # 🔍 Ottieni l'ID della prenotazione

            # 🔄 Completa l'ordine
            db.session.commit()

            return {
                "message": "Ordine effettuato con successo.",
                "cart_id": self.cart_id,
                "generated_codes": booking_codes
            }

        except (SQLAlchemyError, ValueError) as e:
            db.session.rollback()
            return {"error": f"Errore durante l'elaborazione dell'ordine: {str(e)}"}

    # 🔍 Ottieni lo stato del carrello
    def get_status(self):
        return self.status

    # 🔍 Conta il numero di oggetti nel carrello
    def count_items(self):
        return len(json.loads(self.items_id_list))

    def to_dict(self):
        return {
            "cart_id": self.cart_id,
            "user_id": self.user_id,
            "items_id_list": json.loads(self.items_id_list or "[]"),
            "final_price": float(self.final_price),
            "status": self.status,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

class CartItem(db.Model):
    __tablename__ = 'cart_items'

    item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.cart_id'), nullable=False)
    moto_id = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    accessories = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔍 Ottieni un oggetto tramite ID
    @staticmethod
    def get_item_by_id(item_id):
        item = CartItem.query.get(item_id)
        return item.to_dict() if item else None

    # ➡️ Converte un oggetto in un dizionario
    def to_dict(self):
        return {
            "item_id": self.item_id,
            "cart_id": self.cart_id,
            "moto_id": self.moto_id,
            "start_date": self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            "end_date": self.end_date.strftime('%Y-%m-%d %H:%M:%S'),
            "price": float(self.price),
            "accessories": self.accessories,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bike_id = db.Column(db.Integer, nullable=False)
    customer_id = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Boolean, default=True)  # True = attivo, False = cancellato
    payment_status = db.Column(db.Boolean, default=False)  # True = pagato, False = non pagato
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    accessories = db.Column(db.Text)
    dl_type = db.Column(db.String(10))
    dl_expiration = db.Column(db.Date)
    dl_number = db.Column(db.String(50))
    helmet_size = db.Column(db.String(10))
    gloves_size = db.Column(db.String(10))
    pickup = db.Column(db.Boolean, default=False)
    return_ = db.Column(db.Boolean, default=False)
    booking_code = db.Column(
    db.String(8),
    unique=True,
    nullable=False,
    default=lambda: Booking.generate_unique_booking_code()
)

    # ➕ Crea una nuova prenotazione
    @staticmethod
    def create_booking(data):
        new_booking = Booking(
            bike_id=data['bike_id'],
            customer_id=data['customer_id'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            total_price=data['total_price'],
            accessories=json.dumps(data.get('accessories', [])),
            dl_type=data.get('dl_type'),
            dl_expiration=data.get('dl_expiration'),
            dl_number=data.get('dl_number'),
            helmet_size=data.get('helmet_size'),
            gloves_size=data.get('gloves_size'),
            pickup=data.get('pickup', False),
            return_=data.get('return_', False)
        )
        db.session.add(new_booking)
        db.session.commit()

        return new_booking.to_dict()

    @staticmethod
    def generate_unique_booking_code(max_attempts=1000):
        """
        Genera un booking_code a 8 cifre univoco, assicurandosi che non esista già nel database.
        :param max_attempts: Numero massimo di tentativi.
        :return: Un booking_code a 8 cifre.
        :raises Exception: Se non viene trovato un codice univoco dopo max_attempts tentativi.
        """
        import random
        attempts = 0
        while attempts < max_attempts:
            code = ''.join(random.choices('0123456789', k=8))
            # Verifica se esiste già una prenotazione con questo booking_code
            existing = Booking.query.filter_by(booking_code=code).first()
            if not existing:
                return code
            attempts += 1
        raise Exception("Non è stato possibile generare un booking_code univoco dopo molti tentativi.")
    
    # 🔍 Recupera una prenotazione tramite ID
    @staticmethod
    def get_booking_by_id(booking_id):
        booking = Booking.query.get(booking_id)
        return booking.to_dict() if booking else None

    # 🔍 Recupera tutte le prenotazioni di un utente
    @staticmethod
    def get_bookings_by_customer(customer_id):
        bookings = Booking.query.filter_by(customer_id=customer_id).all()
        return [booking.to_dict() for booking in bookings]

    # 🔍 Recupera tutte le prenotazioni (solo per admin)
    @staticmethod
    def get_all_bookings():
        bookings = Booking.query.all()
        return [booking.to_dict() for booking in bookings]

    # 🔍 Recupera i dettagli di una prenotazione usando il codice generato
    @staticmethod
    def get_booking_by_code(generated_code):
        # 🔍 Recupera il booking_id dalla tabella booking_codes
        booking_code = BookingCode.query.filter_by(generated_code=generated_code).first()

        if not booking_code:
            return {"error": "Nessuna prenotazione trovata per il codice fornito."}

        # 🔍 Recupera la prenotazione dalla tabella bookings
        booking = Booking.query.get(booking_code.booking_id)

        if not booking:
            return {"error": "Prenotazione non trovata."}

        return booking.to_dict()

    # 🔄 Aggiorna lo stato della prenotazione
    def update_status(self, new_status):
        self.status = new_status
        db.session.commit()
        return self.to_dict()

    # 💳 Aggiorna lo stato di pagamento della prenotazione
    @staticmethod
    def update_payment_status(booking_id, customer_id):
        booking = Booking.query.filter_by(id=booking_id, customer_id=customer_id).first()

        if not booking:
            return {"error": "Prenotazione non trovata o non appartiene all'utente."}

        if booking.payment_status:
            return {"error": "La prenotazione è già stata pagata."}

        # 💳 Aggiorna il campo di pagamento
        booking.payment_status = True
        db.session.commit()

        return {
            "message": "Pagamento registrato con successo.",
            "booking": booking.to_dict()
        }

    # 🗑️ Elimina una prenotazione solo se appartiene all'utente
    @staticmethod
    def delete_booking(booking_id, user_id):
        user = User.query.get(user_id)

        if user and user.role == "admin":
            # 🔥 L'admin può cancellare qualsiasi prenotazione
            booking = Booking.query.get(booking_id)
        else:
            # 🔒 L'utente normale può cancellare solo le proprie prenotazioni
            booking = Booking.query.filter_by(id=booking_id, customer_id=user_id).first()

        if not booking:
            return {"error": "Prenotazione non trovata o non appartiene all'utente."}

        # 🗑️ Elimina la prenotazione
        db.session.delete(booking)
        db.session.commit()
        return {
            "message": "Prenotazione eliminata con successo.",
            "booking": booking.to_dict()
        }

    # 🔍 Controlla se le date sono disponibili per una nuova prenotazione
    @staticmethod
    def check_availability(bike_id, start_date, end_date):
        conflicting_bookings = Booking.query.filter(
            Booking.bike_id == bike_id,
            Booking.status == True,
            or_(
                (Booking.start_date <= start_date) & (Booking.end_date >= start_date),
                (Booking.start_date <= end_date) & (Booking.end_date >= end_date),
                (Booking.start_date >= start_date) & (Booking.end_date <= end_date)
            )
        ).all()
        return len(conflicting_bookings) == 0

    # 🔄 Aggiorna una prenotazione
    @staticmethod
    def update_booking(booking_id, customer_id, update_data):
        booking = Booking.query.filter_by(id=booking_id, customer_id=customer_id).first()

        if not booking:
            return {"error": "Prenotazione non trovata o non appartiene all'utente."}

        if not booking.status:
            return {"error": "Non è possibile aggiornare una prenotazione già cancellata o completata."}

        # 🔄 Aggiorna i campi della prenotazione
        for key, value in update_data.items():
            if hasattr(booking, key):
                setattr(booking, key, value)

        # 🔄 Aggiorna la data di modifica
        booking.last_update = datetime.utcnow()

        db.session.commit()

        return {
            "message": "Prenotazione aggiornata con successo.",
            "booking": booking.to_dict()
        }

    # 🔍 Recupera tutte le prenotazioni di un utente
    @staticmethod
    def get_user_bookings(customer_id):
        bookings = Booking.query.filter_by(customer_id=customer_id).all()

        if not bookings:
            return {"error": "Nessuna prenotazione trovata per questo utente."}

        return [booking.to_dict() for booking in bookings]
    
    # 🔍 Controllo conflitto di date nelle prenotazioni attive
    @staticmethod
    def check_date_conflict_in_cart(customer_id, start_date, end_date):
        # 🔍 Recupera tutte le prenotazioni attive per l'utente
        conflicting_bookings = Booking.query.filter(
            Booking.customer_id == customer_id,
            Booking.status == True,  # Solo prenotazioni attive
            or_(
                (Booking.start_date <= start_date) & (Booking.end_date >= start_date),
                (Booking.start_date <= end_date) & (Booking.end_date >= end_date),
                (Booking.start_date >= start_date) & (Booking.end_date <= end_date)
            )
        ).all()

        # 🚫 Se ci sono prenotazioni con date sovrapposte
        if conflicting_bookings:
            return {
                "error": "Hai già una prenotazione attiva con date che si sovrappongono a quelle selezionate."
            }

        # Nessun conflitto
        return None

    # 🔍 Recupera tutte le prenotazioni relative a un veicolo specifico
    @staticmethod
    def get_bookings_by_vehicle(bike_id):
        bookings = Booking.query.filter_by(bike_id=bike_id).all()

        if not bookings:
            return {"error": "Nessuna prenotazione trovata per questo veicolo."}

        return [booking.to_dict() for booking in bookings]

    @staticmethod
    def toggle_pickup(booking_id, user_id):
        booking = Booking.query.filter_by(id=booking_id).first()

        if not booking:
            return {"error": "Prenotazione non trovata o non appartiene all'utente."}

        # Verifica i permessi
        user = User.query.get(user_id)
        if not user or (booking.customer_id != user_id and user.role != "admin"):
            return {"error": "Accesso negato. Non hai i permessi per modificare questa prenotazione."}

        # 🔄 Inverti il valore di pickup
        booking.pickup = not booking.pickup
        db.session.commit()

        return {
            "message": "Campo 'pickup' aggiornato con successo.",
            "new_value": booking.pickup
        }

    @staticmethod
    def toggle_return(booking_id, user_id):
        booking = Booking.query.filter_by(id=booking_id).first()

        if not booking:
            return {"error": "Prenotazione non trovata o non appartiene all'utente."}

        user = User.query.get(user_id)
        if not user or (booking.customer_id != user_id and user.role != "admin"):
            return {"error": "Accesso negato. Non hai i permessi per modificare questa prenotazione."}

        # 🔄 Inverti il valore di return_
        booking.return_ = not booking.return_
        db.session.commit()

        return {
            "message": "Campo 'return' aggiornato con successo.",
            "new_value": booking.return_
        }

    @staticmethod
    def toggle_payment_status(booking_id, user_id):
        booking = Booking.query.filter_by(id=booking_id).first()

        if not booking:
            return {"error": "Prenotazione non trovata o non appartiene all'utente."}

        user = User.query.get(user_id)
        if not user or (booking.customer_id != user_id and user.role != "admin"):
            return {"error": "Accesso negato. Non hai i permessi per modificare questa prenotazione."}

        # 🔄 Inverti il valore di payment_status
        booking.payment_status = not booking.payment_status
        db.session.commit()

        return {
            "message": "Campo 'payment_status' aggiornato con successo.",
            "new_value": booking.payment_status
        }   
    
    # 🔍 Recupera il codice di prenotazione tramite ID della prenotazione
    @staticmethod
    def get_booking_code_by_booking_id(booking_id):
        try:
            # 🔍 Verifica se esiste una prenotazione con l'ID fornito
            booking = Booking.query.get(booking_id)

            if not booking:
                return {"error": "❌ Prenotazione non trovata."}

            # 🔍 Cerca il codice di prenotazione nella tabella BookingCode
            booking_code = BookingCode.query.filter_by(booking_id=booking_id).first()

            if not booking_code:
                return {"error": "❌ Nessun codice di prenotazione trovato per questa prenotazione."}

            # ✅ Restituisce il codice di prenotazione
            return {
                "message": "✅ Codice di prenotazione recuperato con successo.",
                "booking_id": booking_id,
                "booking_code": booking_code.generated_code
            }

        except SQLAlchemyError as e:
            return {"error": f"❌ Errore durante il recupero del codice di prenotazione: {str(e)}"}
    
    # 🔍 Metodo per ottenere le prenotazioni in base a nome e cognome
    @staticmethod
    def get_detailed_bookings_by_name(first_name, last_name):
        bookings = Booking.query.join(User, Booking.customer_id == User.id).join(Vehicle, Booking.bike_id == Vehicle.id).filter(
            User.name.ilike(f"%{first_name}%"),
            User.surname.ilike(f"%{last_name}%")
        ).all()

        detailed_bookings = []
        for booking in bookings:
            booking_data = booking.to_dict()

            # Aggiungi i dettagli dell'utente
            user = User.query.get(booking.customer_id)
            booking_data["user"] = user.to_dict() if user else {}

            # Aggiungi i dettagli del veicolo
            vehicle = Vehicle.query.get(booking.bike_id)
            booking_data["vehicle"] = vehicle.to_dict() if vehicle else {}

            # Aggiungi il codice della prenotazione
            booking_code_entry = BookingCode.query.filter_by(booking_id=booking.id).first()
            booking_data["booking_code"] = booking_code_entry.generated_code if booking_code_entry else None

            detailed_bookings.append(booking_data)

        return detailed_bookings

    # Metodo per controllare conflitti di prenotazioni per lo stesso utente
    @staticmethod
    def has_conflicting_booking(user_id, start_date, end_date):
        """
        Controlla se l'utente ha già una prenotazione che si sovrappone con le date fornite.
        
        Args:
            user_id (int): ID dell'utente.
            start_date (datetime): Data di inizio.
            end_date (datetime): Data di fine.
        
        Returns:
            bool: True se c'è una sovrapposizione, False altrimenti.
        """
        conflicting_bookings = Booking.query.filter(
            Booking.customer_id == user_id,
            Booking.status == True,  # Solo prenotazioni attive
            or_(
                # L'intervallo fornito si sovrappone a un'altra prenotazione
                (Booking.start_date <= start_date) & (Booking.end_date >= start_date),
                (Booking.start_date <= end_date) & (Booking.end_date >= end_date),
                (Booking.start_date >= start_date) & (Booking.end_date <= end_date)
            )
        ).all()

        return len(conflicting_bookings) > 0
    
    @staticmethod
    def submit_cart_as_booking(cart):
        try:
            cart_details = cart.get_detailed_user_cart()

            if not cart_details or cart_details['status'] != 'active':
                return {"error": "Il carrello non è attivo o non esiste."}

            booking_codes = []

            for item in cart_details["items"]:
                # 🛒 Crea una nuova prenotazione
                new_booking = Booking(
                    customer_id=cart_details["user_id"],
                    bike_id=item["moto_id"],
                    start_date=datetime.strptime(item["start_date"], '%Y-%m-%d %H:%M:%S'),
                    end_date=datetime.strptime(item["end_date"], '%Y-%m-%d %H:%M:%S'),
                    total_price=item["price"],
                    accessories=item.get("accessories", "[]"),
                    dl_type="A",
                    dl_expiration=datetime.now().date(),
                    dl_number="DL000000",
                    helmet_size="M",
                    gloves_size="M",
                    pickup=False,
                    return_=False,
                    status=True,
                    payment_status=False
                )

                db.session.add(new_booking)
                db.session.flush()  # 🔍 Ottieni l'ID della prenotazione

                # 🔢 Genera automaticamente il codice di prenotazione
                generated_code_result = BookingCode.generate_code_only(
                    user_id=cart_details["user_id"],
                    bike_id=item["moto_id"],
                    booking_id=new_booking.id,
                    start_date=item["start_date"],
                    end_date=item["end_date"]
                )

                if "error" in generated_code_result:
                    raise ValueError(f"Errore nella generazione del codice: {generated_code_result['error']}")

                generated_code = generated_code_result["generated_code"]

                # ➕ Aggiungi il codice al database
                add_code_result = BookingCode.add_booking_code(new_booking.id, generated_code)

                if "error" in add_code_result:
                    raise ValueError(f"Errore durante il salvataggio del codice: {add_code_result['error']}")

                booking_codes.append({
                    "booking_id": new_booking.id,
                    "generated_code": generated_code
                })

                # ❌ Elimina l'item sottomesso dal carrello
                CartItem.query.filter_by(item_id=item["item_id"]).delete()

            # 💾 Commetti le modifiche
            db.session.commit()

            return {
                "message": "Prenotazioni completate con successo.",
                "bookings": booking_codes
            }

        except (SQLAlchemyError, ValueError) as e:
            db.session.rollback()
            return {"error": f"Errore durante la sottomissione delle prenotazioni: {str(e)}"}

    # 🔄 Converte la prenotazione in dizionario
    def to_dict(self):
        return {
            "id": self.id,
            "bike_id": self.bike_id,
            "customer_id": self.customer_id,
            "start_date": self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            "end_date": self.end_date.strftime('%Y-%m-%d %H:%M:%S'),
            "total_price": float(self.total_price),
            "status": self.status,
            "payment_status": self.payment_status,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "last_update": self.last_update.strftime('%Y-%m-%d %H:%M:%S'),
            "accessories": json.loads(self.accessories) if self.accessories else [],
            "dl_type": self.dl_type,
            "dl_expiration": self.dl_expiration.strftime('%Y-%m-%d') if self.dl_expiration else None,
            "dl_number": self.dl_number,
            "helmet_size": self.helmet_size,
            "gloves_size": self.gloves_size,
            "pickup": self.pickup,
            "return_": self.return_,
            "booking_code": self.booking_code
        }
    
class BookingCode(db.Model):
    __tablename__ = 'booking_codes'

    key_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(db.Integer, nullable=False)
    generated_code = db.Column(db.Integer, unique=True, nullable=False)

    @staticmethod
    def generate_code_only(user_id, bike_id, booking_id, start_date, end_date):
        # 🔍 Verifica se la prenotazione esiste e appartiene alla moto
        booking = Booking.query.filter_by(id=booking_id, bike_id=bike_id).first()

        if not booking:
            return {"error": "Prenotazione non trovata o non associata alla moto specificata."}

        # 🔗 Crea una stringa univoca con i parametri forniti
        unique_string = f"{user_id}{bike_id}{booking_id}{start_date}{end_date}"

        # 🔢 Genera un hash SHA-256 e convertilo in un numero
        hash_object = hashlib.sha256(unique_string.encode())
        hash_digest = hash_object.hexdigest()

        # 🔢 Prendi i primi 8 caratteri numerici dell'hash per ottenere un numero a 8 cifre
        numeric_part = int(hash_digest, 16) % 10**8

        return {
            "message": "Codice generato con successo.",
            "generated_code": numeric_part
        }

    @staticmethod
    def get_code_by_booking_id(booking_id):
        code = BookingCode.query.filter_by(booking_id=booking_id).first()
        if code:
            return code.generated_code
        return None

    @staticmethod
    def add_booking_code(booking_id, generated_code):
        # 🔍 Controlla se la prenotazione esiste
        booking = Booking.query.get(booking_id)
        if not booking:
            return {"error": "Prenotazione non trovata."}

        # 🔍 Verifica se esiste già un codice per questa prenotazione
        existing_code = BookingCode.query.filter_by(booking_id=booking_id).first()
        if existing_code:
            return {"error": "Codice già esistente per questa prenotazione."}

        # 🔍 Verifica se il codice è già utilizzato in un'altra prenotazione
        duplicate_code = BookingCode.query.filter_by(generated_code=generated_code).first()
        if duplicate_code:
            return {"error": "Questo codice è già associato a un'altra prenotazione."}

        try:
            # ➕ Aggiunge il codice alla tabella
            new_code = BookingCode(
                booking_id=booking_id,
                generated_code=generated_code
            )
            db.session.add(new_code)
            db.session.commit()

            return {
                "message": "Codice di prenotazione aggiunto con successo.",
                "generated_code": generated_code
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            return {"error": f"Errore durante l'aggiunta del codice: {str(e)}"}
        
class TokenBlacklist(db.Model):
    __tablename__ = 'revoked_tokens'  # Tabella aggiornata

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def add_token(jti):
        """Aggiunge un token alla blacklist"""
        if not TokenBlacklist.is_token_blacklisted(jti):
            db.session.add(TokenBlacklist(jti=jti))
            db.session.commit()

    @staticmethod
    def is_token_blacklisted(jti):
        """Controlla se il token è nella blacklist"""
        return TokenBlacklist.query.filter_by(jti=jti).first() is not None

    @staticmethod
    def clean_old_tokens():
        """Rimuove i token revocati più vecchi di 30 giorni"""
        threshold = datetime.utcnow() - timedelta(days=30)
        db.session.query(TokenBlacklist).filter(TokenBlacklist.created_at < threshold).delete()
        db.session.commit()
