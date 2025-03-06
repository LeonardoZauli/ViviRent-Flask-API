from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity, create_refresh_token
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Vehicle, Cart, Booking, BookingCode, TokenBlacklist
import datetime as dt  # Rinominato per evitare conflitti
from datetime import datetime  # Classe datetime senza conflitti
from datetime import timedelta  # ✅ Import corretto
import re
from dateutil import parser  # Aggiungi questa importazione in cima al file
from functools import wraps

# Define the jwt_blacklist set to store blacklisted JWTs
jwt_blacklist = set()

# ✅ Creazione del Blueprint
api = Blueprint('api', __name__)

# 🔒 Controllo ruolo admin
def admin_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != "admin":
            return jsonify({"error": "Accesso negato. Solo gli amministratori possono accedere a questa risorsa."}), 403
        return fn(*args, **kwargs)

    return wrapper
  
########################## USERS ##########################

# Endpoint per la registrazione di un nuovo utente
@api.route('/register', methods=['POST'])
def register_user():
    """
    Registra un nuovo utente e imposta JWT nei cookie httpOnly
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Richiesta non valida. Il payload JSON è richiesto."}), 400

    required_fields = ['name', 'surname', 'password', 'email', 'bday', 'place']
    for field in required_fields:
        if field not in data or not data[field].strip():
            return jsonify({"error": f"Il campo '{field}' è obbligatorio."}), 400

    # ✅ Pulizia e validazione
    name = data['name'].strip()
    surname = data['surname'].strip()
    password = data['password'].strip()
    email = data['email'].strip()
    bday_str = data['bday'].strip()
    place = data['place'].strip()

    # ✅ Validazione email
    if not is_valid_email(email):
        return jsonify({"error": "Formato email non valido."}), 400

    # 🔍 Controllo email già registrata
    if User.is_email_registered(email):
        return jsonify({"error": "Questa email è già registrata."}), 400

    # ✅ Validazione della data di nascita
    try:
        bday = datetime.strptime(bday_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "La data di nascita deve essere nel formato YYYY-MM-DD."}), 400

    # ➕ Creazione dell'utente
    try:
        new_user = User.add_user(
            name=name,
            surname=surname,
            password=password,
            email=email,
            bday=bday,
            place=place
        )

        # 🔍 Recupera l'ID dal database dopo il commit
        user_instance = User.find_by_email(email)
        if not user_instance:
            return jsonify({"error": "Errore durante la registrazione: Utente non trovato dopo il commit."}), 500

        # ➕ Crea un nuovo carrello per l'utente
        cart = Cart.create_cart(user_instance.id)

        # ✅ Generazione dei token JWT con ruolo incluso
        access_token = create_access_token(
            identity=str(user_instance.id),
            additional_claims={"role": user_instance.role},
            expires_delta=timedelta(hours=1)
        )
        refresh_token = create_refresh_token(
            identity=str(user_instance.id),
            additional_claims={"role": user_instance.role},
            expires_delta=timedelta(days=7)
        )

        # ✅ Creazione della risposta con i cookie
        response = make_response(jsonify({"message": "Registrazione avvenuta con successo!"}))

        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            secure=True,  # 🔥 Imposta a False per test in locale senza HTTPS
            samesite="None",
            path="/"
        )
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            secure=True,  # 🔥 Imposta a False per test in locale senza HTTPS
            samesite="None",
            path="/"
        )

        return response, 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la registrazione: {str(e)}"}), 500

# Login user restituendo un cookie contenente l'accessToken JWT
@api.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    # 🔍 Recupera l'utente dal DB tramite email
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # 👀 Verifica la password
    if not check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    #print(user)
    # ✅ Usa l'ID dell'utente come identity
    access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role}, expires_delta=dt.timedelta(hours=1))
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims={"role": user.role}, expires_delta=dt.timedelta(days=7))

    response = make_response(jsonify({'message': 'Login successful'}))
    response.set_cookie(
        'access_token',
        access_token,
        httponly=True,
        secure=True,  # Necessario su HTTPS
        samesite="None"
    )
    response.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=True,
        samesite="None"
    )
    return response

# Endpoint per l'update del profilo utente
@api.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_user():
    # #print(✅ La richiesta è stata ricevuta.")
    
    try:
        data = request.get_json()
        # #print(📥 Dati ricevuti:", data)

        if not data:
            return jsonify({"error": "Nessun dato ricevuto per l'aggiornamento."}), 400

        # 🔐 Ottieni l'ID dell'utente dal token JWT
        user_id = get_jwt_identity()
        # #print(🔑 ID Utente dal JWT:", user_id)

        updated_user = User.update_user(
            user_id=user_id,
            name=data.get('name'),
            surname=data.get('surname'),
            email=data.get('email'),
            bday=data.get('bday'),
            place=data.get('place')
        )

        if updated_user:
            return jsonify({
                "message": "Dati aggiornati con successo!",
                "user": updated_user
            }), 200
        else:
            return jsonify({"error": "Utente non trovato."}), 404
    except Exception as e:
        # #print(Errore:", str(e))
        return jsonify({"error": "Errore imprevisto."}), 500

@api.route('/delete-profile', methods=['DELETE'])
@jwt_required()
def delete_account():
    """
    🗑️ Cancella l'account dell'utente autenticato e revoca il token attivo
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Account cancellato e token revocato con successo
      404:
        description: Utente non trovato
    """
    try:
        # 🔐 Ottieni l'ID utente dal token JWT
        user_id = get_jwt_identity()
        #print(user_id)

        # 🔄 Elimina l'utente
        result = User.delete_user(user_id)

        if result:
            # 🔒 Revoca il token attuale (aggiungendolo alla blacklist)
            jti = get_jwt()["jti"]  # 🔍 Ottieni il JWT Token ID
            jwt_blacklist.add(jti)

            return jsonify({
                "message": "Account eliminato con successo. Il token è stato revocato."
            }), 200
        else:
            return jsonify({"error": "Utente non trovato."}), 404

    except Exception as e:
        return jsonify({"error": f"Errore durante l'eliminazione dell'account: {str(e)}"}), 500

@api.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({"message": "Logged out successfully"}))
    response.set_cookie(
        "access_token",
        value="",
        expires=0,
        secure=True,
        httponly=True,
        samesite="None",
        path="/"
    )
    response.set_cookie(
        "refresh_token",
        value="",
        expires=0,
        secure=True,
        httponly=True,
        samesite="None",
        path="/"
    )
    return response, 200
    
@api.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({"message": f"Hello {current_user}, you are authenticated!"})

@api.route("/check-auth", methods=["GET"])
@jwt_required()  # legge il cookie access_token
def check_auth():
    current_user = get_jwt_identity()
    return jsonify({"message": f"User {current_user} is authenticated"}), 200

@api.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)  # Richiede un refresh token valido
def refresh_token():
    """
    Genera un nuovo access token
    """
    try:
        user_id = get_jwt_identity()  # Ottiene l'utente attuale
        new_access_token = create_access_token(identity=user_id)  # Crea un nuovo token accesso
        return jsonify({"access_token": new_access_token}), 200
    except Exception as e:
        return jsonify({"error": f"Errore durante il refresh token: {str(e)}"}), 500
  
@api.route('/get-role', methods=['GET'])
@jwt_required()  # ✅ Verifica il token JWT nel cookie httpOnly
def get_role():
    try:
        claims = get_jwt()  # 🔥 Ottiene i dati dal JWT
        user_role = claims.get("role", None)  # Recupera il ruolo aggiunto nel token

        if not user_role:
            return jsonify({"error": "Ruolo non trovato nel token"}), 400

        return jsonify({"role": user_role}), 200

    except Exception as e:
        return jsonify({"error": f"Errore nel recupero del ruolo: {str(e)}"}), 500
    
@api.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def get_all_users():
    """
    👥 Recupera tutti gli utenti (solo per amministratori)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Lista di tutti gli utenti
      403:
        description: Accesso negato, permessi insufficienti
    """
    try:

        # ✅ Recupera tutti gli utenti dal database
        all_users = User.get_all_users()

        return jsonify({
            "message": "Utenti recuperati con successo.",
            "users": all_users
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero degli utenti: {str(e)}"}), 500

@api.route('/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    try:
        # 🔐 user_id ora è un intero (es: 1)
        user_id = get_jwt_identity()
        ##print(user_id)
        
        # 🔍 Recupera l'utente dal DB usando la PK
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Utente non trovato."}), 404

        return jsonify({
            "message": "Profilo utente recuperato con successo.",
            "user": user.to_dict()  # E.g. { "id": 1, "email": "a@gmail" }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero del profilo: {str(e)}"}), 500

@api.route('/change-password', methods=['POST'])
@jwt_required()  # 🔒 Richiede autenticazione tramite JWT
def change_password():
    """
    Permette a un utente autenticato di cambiare la password
    """
    try:
        # ✅ Ottiene l'utente attuale dal token JWT
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "Utente non trovato"}), 404

        # ✅ Riceve i dati JSON
        data = request.get_json()

        if not data or "current_password" not in data or "new_password" not in data:
            return jsonify({"error": "Dati mancanti"}), 400

        # ✅ Aggiorna la password usando il metodo `update_password`
        user.update_password(data["current_password"].strip(), data["new_password"].strip())

        return jsonify({"message": "Password aggiornata con successo!"}), 200

    except ValueError as e:  # 🔍 Cattura errori specifici di validazione
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Errore durante la modifica della password: {str(e)}"}), 500

@api.route('/password-reset/request', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email richiesta"}), 400

    user = User.find_by_email(email=email)

    if not user:
        return jsonify({"error": "Nessun utente trovato con questa email"}), 400

    # ✅ Crea un token di reset con scadenza di 30 minuti
    reset_token = create_access_token(identity=user.id, expires_delta=timedelta(minutes=30))

    return jsonify({"reset_token": reset_token}), 200

@api.route('/password-reset/<string:token>', methods=['POST'])
@jwt_required()
def reset_password(token):
    """
    ✅ Endpoint per aggiornare la password dopo il reset
    """
    try:
        # ✅ Ottiene l'ID utente dal token JWT
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "Utente non trovato"}), 404

        # ✅ Riceve la nuova password dal payload JSON
        data = request.get_json()
        new_password = data.get("new_password")

        if not new_password:
            return jsonify({"error": "La nuova password è obbligatoria."}), 400

        # ✅ Aggiorna la password tramite il metodo della classe `User`
        user.update_password(new_password)

        return jsonify({"message": "Password aggiornata con successo!"}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Errore durante il reset della password: {str(e)}"}), 500

######################### VEHICLES #########################

@api.route('/vehicles', methods=['GET'])
def get_all_vehicles():
    """
    🚗 Restituisce tutti i veicoli attivi disponibili
    ---
    tags:
      - Vehicles
    security:
      - Bearer: []
    responses:
      200:
        description: Lista di tutti i veicoli attivi
      500:
        description: Errore durante il recupero dei veicoli
    """
    try:
        # ✅ Recupera tutti i veicoli attivi
        all_vehicles = Vehicle.get_all_active_vehicles()

        return jsonify({
            "message": "Veicoli recuperati con successo.",
            "vehicles": all_vehicles
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero dei veicoli: {str(e)}"}), 500

@api.route('/vehicles/<int:vehicle_id>', methods=['GET'])
def get_vehicle_by_id(vehicle_id):
    """
    🚗 Recupera i dettagli di un veicolo specifico tramite ID
    ---
    tags:
      - Vehicles
    security:
      - Bearer: []
    parameters:
      - name: vehicle_id
        in: path
        required: true
        type: integer
        description: L'ID del veicolo da recuperare
    responses:
      200:
        description: Dati del veicolo trovati con successo
      404:
        description: Veicolo non trovato
    """
    try:
        # 🔍 Cerca il veicolo tramite ID
        vehicle = Vehicle.find_by_id(vehicle_id)

        if vehicle:
            return jsonify({
                "message": "Veicolo trovato con successo.",
                "vehicle": vehicle.to_dict()
            }), 200
        else:
            return jsonify({"error": "Veicolo non trovato."}), 404

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero del veicolo: {str(e)}"}), 500

@api.route('/vehicles/license/<string:license_type>', methods=['GET'])
def get_vehicles_by_license(license_type):
    """
    🚗 Recupera i veicoli disponibili per una determinata patente
    ---
    tags:
      - Vehicles
    security:
      - Bearer: []
    parameters:
      - name: license_type
        in: path
        required: true
        type: string
        description: Tipo di patente richiesta (es. A, A1, B)
    responses:
      200:
        description: Lista dei veicoli per il tipo di patente richiesto
      404:
        description: Nessun veicolo trovato per il tipo di patente
    """
    try:
        # 🔍 Recupera i veicoli che richiedono la patente specificata
        vehicles = Vehicle.filter_by_driving_license(license_type)

        if vehicles:
            return jsonify({
                "message": f"✅ Veicoli trovati per la patente {license_type}.",
                "vehicles": vehicles  # Rimuovi il ciclo con to_dict()
            }), 200
        else:
            return jsonify({"error": f"Nessun veicolo trovato per la patente {license_type}."}), 404

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero dei veicoli: {str(e)}"}), 500

@api.route('/vehicles/available', methods=['GET'])
def get_available_vehicles():
    """
    🚗 Recupera solo i veicoli attualmente disponibili
    ---
    tags:
      - Vehicles
    security:
      - Bearer: []
    responses:
      200:
        description: Lista di tutti i veicoli disponibili
      404:
        description: Nessun veicolo disponibile trovato
    """
    try:
        # 🔍 Recupera solo i veicoli attivi
        available_vehicles = Vehicle.get_all_active_vehicles()

        if available_vehicles:
            return jsonify({
                "message": "Veicoli disponibili recuperati con successo.",
                "vehicles": available_vehicles
            }), 200
        else:
            return jsonify({"error": "Nessun veicolo disponibile trovato."}), 404

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero dei veicoli disponibili: {str(e)}"}), 500

@api.route('/vehicles', methods=['POST'])
@jwt_required()  # 🔐 Richiede autenticazione JWT
@admin_required
def add_vehicle():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dati mancanti o non validi."}), 400

        # Rimuovi 'is_active' dalla lista dei campi obbligatori
        required_fields = [
            'vehicle_type', 'brand', 'model', 'year', 'price_per_hour',
            'license_plate', 'driving_license', 'power', 'engine_size',
            'fuel_type', 'description', 'image_url', 'deposit'
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Il campo '{field}' è obbligatorio."}), 400

        new_vehicle = Vehicle(
            vehicle_type=data['vehicle_type'],
            brand=data['brand'],
            model=data['model'],
            year=data['year'],
            price_per_hour=data['price_per_hour'],
            license_plate=data['license_plate'],
            driving_license=data['driving_license'],
            power=data['power'],
            engine_size=data['engine_size'],
            fuel_type=data['fuel_type'],
            # Usa il default True se non viene inviato
            is_active=data.get('is_active', True),
            description=data['description'],
            image_url=data['image_url'],
            deposit=data['deposit']
        )

        db.session.add(new_vehicle)
        db.session.commit()

        return jsonify({
            "message": "Veicolo aggiunto con successo.",
            "vehicle": new_vehicle.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante l'aggiunta del veicolo: {str(e)}"}), 500

@api.route('/vehicles/update/<int:vehicle_id>', methods=['PUT'])
@jwt_required()  # 🔐 Richiede autenticazione JWT
@admin_required
def update_vehicle(vehicle_id):
    """
    🔄 Modifica i dettagli di un veicolo specifico (solo per amministratori)
    ---
    tags:
      - Vehicles
    security:
      - Bearer: []
    parameters:
      - name: vehicle_id
        in: path
        required: true
        type: integer
        description: ID del veicolo da aggiornare
    responses:
      200:
        description: Veicolo aggiornato con successo
      404:
        description: Veicolo non trovato
      403:
        description: Accesso negato, permessi insufficienti
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Dati mancanti o non validi."}), 400

        # 🔄 Usa il metodo della classe per aggiornare il veicolo
        updated_vehicle = Vehicle.update_vehicle(vehicle_id, **data)

        if updated_vehicle:
            return jsonify({
                "message": "Veicolo aggiornato con successo.",
                "vehicle": updated_vehicle
            }), 200
        else:
            return jsonify({"error": "Veicolo non trovato."}), 404

    except Exception as e:
        return jsonify({"error": f"Errore durante l'aggiornamento del veicolo: {str(e)}"}), 500

@api.route('/vehicles/available-range', methods=['GET'])
def get_available_vehicles_range():
    """
    📅 Recupera i veicoli disponibili in un intervallo di date.
    ---
    tags:
      - Vehicles
    parameters:
      - name: start_date
        in: query
        required: true
        type: string
        description: Data di inizio nel formato ISO (es. 2025-02-27T09:00:00)
      - name: end_date
        in: query
        required: true
        type: string
        description: Data di fine nel formato ISO (es. 2025-02-28T17:00:00)
    responses:
      200:
        description: Lista di veicoli disponibili
      400:
        description: Errore nei parametri forniti
    """
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({"error": "Le date 'start_date' e 'end_date' sono obbligatorie."}), 400

        # Converti le stringhe in oggetti datetime
        start_date = parser.parse(start_date_str)
        end_date = parser.parse(end_date_str)   

        # Controlla che le date siano valide
        if start_date >= end_date:
            return jsonify({"error": "La data di inizio deve essere antecedente alla data di fine."}), 400

        # Recupera i veicoli disponibili
        available_vehicles = Vehicle.get_available_vehicles_in_range(start_date, end_date)

        return jsonify({
            "message": "Veicoli disponibili recuperati con successo.",
            "vehicles": available_vehicles
        }), 200

    except ValueError:
        return jsonify({"error": "Formato delle date non valido. Usa il formato ISO (YYYY-MM-DDTHH:MM:SS)."}), 400
    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero dei veicoli disponibili: {str(e)}"}), 500

@api.route('/vehicles/<int:vehicle_id>', methods=['DELETE'])
@jwt_required()  # 🔐 Richiede autenticazione JWT
@admin_required
def delete_vehicle(vehicle_id):
    """
    🗑️ Elimina un veicolo specifico tramite ID (solo per amministratori)
    ---
    tags:
      - Vehicles
    security:
      - Bearer: []
    parameters:
      - name: vehicle_id
        in: path
        required: true
        type: integer
        description: ID del veicolo da eliminare
    responses:
      200:
        description: Veicolo eliminato con successo
      404:
        description: Veicolo non trovato
      403:
        description: Accesso negato, permessi insufficienti
    """
    try:
        # 🔄 Usa il metodo della classe per eliminare il veicolo
        deleted = Vehicle.delete_vehicle(vehicle_id)

        if deleted:
            return jsonify({"message": "Veicolo eliminato con successo."}), 200
        else:
            return jsonify({"error": "Veicolo non trovato."}), 404

    except Exception as e:
        return jsonify({"error": f"Errore durante l'eliminazione del veicolo: {str(e)}"}), 500

@api.route('/check-moto-availability', methods=['POST'])
def check_moto_availability():
    """
    🔍 Controlla se una moto è già prenotata in un intervallo di date.
    ---  
    tags:
      - Bookings
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            moto_id:
              type: integer
              description: ID della moto
            start_date:
              type: string
              description: Data di inizio (formato: YYYY-MM-DD HH:MM:SS)
            end_date:
              type: string
              description: Data di fine (formato: YYYY-MM-DD HH:MM:SS)
    responses:
      200:
        description: Risposta con la disponibilità della moto
      400:
        description: Errore nei dati inviati
    """
    try:
        data = request.get_json()

        # Controllo parametri richiesti
        if not data or "moto_id" not in data or "start_date" not in data or "end_date" not in data:
            return jsonify({"error": "Dati mancanti o non validi."}), 400

        moto_id = data["moto_id"]
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d %H:%M:%S")

        # Controllo se la data di inizio è inferiore alle 24 ore dal momento attuale
        now = datetime.now()
        if start_date <= now + timedelta(hours=12):
            return jsonify({
                "moto_id": moto_id,
                "is_booked": True,
                "message": "La moto è bloccata poiché la data di inizio è inferiore alle 24 ore."
            }), 200

        # Verifica la disponibilità tramite la classe Cart
        is_booked = Cart.is_bike_booked(moto_id, start_date, end_date)

        return jsonify({
            "moto_id": moto_id,
            "is_booked": is_booked
        }), 200

    except ValueError:
        return jsonify({"error": "Formato data non valido. Usa il formato YYYY-MM-DD HH:MM:SS."}), 400
    except Exception as e:
        return jsonify({"error": f"Errore durante il controllo della disponibilità: {str(e)}"}), 500
    
######################## CARTS #########################

@api.route('/cart/create', methods=['POST'])
@jwt_required()  # 🔐 Richiede autenticazione JWT
def create_cart():
    """
    ➕ Crea un nuovo carrello per l'utente autenticato
    ---
    tags:
      - Cart
    security:
      - Bearer: []
    responses:
      200:
        description: Carrello creato con successo
    """
    try:
        user_id = get_jwt_identity()  # 🔐 Ottiene l'ID dell'utente dal JWT

        # ➕ Crea un nuovo carrello
        cart = Cart.create_cart(user_id)

        return jsonify({
            "message": "Carrello creato con successo.",
            "cart": cart
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la creazione del carrello: {str(e)}"}), 500

@api.route('/cart', methods=['POST'])
@jwt_required()
def add_item_to_user_cart():
    try:
        user_id = get_jwt_identity()
        ##print(user_id)

        # 🔍 Recupera il carrello attivo per l'utente
        carts = Cart.get_carts_by_user(user_id)
        #print(carts)
        active_cart = next((cart for cart in carts if cart['status'] == 'active'), None)

        if not active_cart:
            return jsonify({"error": "Nessun carrello attivo trovato per l'utente."}), 404

        cart = Cart.query.get(active_cart['cart_id'])

        # ✅ Ricezione dati dal body della richiesta
        if not request.is_json:
            return jsonify({"error": "Il corpo della richiesta deve essere in formato JSON."}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "Nessun dato fornito per aggiungere il prodotto."}), 400

        # ➕ Aggiungi il prodotto al carrello
        item = cart.add_item(
        moto_id=data['moto_id'],
        start_date=parser.isoparse(data['start_date']) + timedelta(hours=1),
        end_date=parser.isoparse(data['end_date']) + timedelta(hours=1),
        price=data['price'],
        accessories=data.get('accessories', [])
    )

        # 🔍 Se viene restituito un errore dal metodo add_item
        if isinstance(item, dict) and "error" in item:
            return jsonify({"error": item["error"]}), 400  # Restituisce solo l'errore

        return jsonify({
            "message": "Prodotto aggiunto con successo al carrello.",
            "item": item
        }), 200

    except Exception as e:
        # #print(f"Errore completo: {str(e)}")
        return jsonify({"error": f"Errore durante l'aggiunta del prodotto: {str(e)}"}), 500

@api.route('/cart/remove/<int:item_id>', methods=['DELETE'])
@jwt_required()
def remove_item_from_cart(item_id):
    try:
        user_id = get_jwt_identity()

        # 🔍 Recupera il carrello attivo per l'utente
        carts = Cart.get_carts_by_user(user_id)
        active_cart = next((cart for cart in carts if cart['status'] == 'active'), None)

        if not active_cart:
            return jsonify({"error": "Nessun carrello attivo trovato per l'utente."}), 404

        cart = Cart.query.get(active_cart['cart_id'])

        # 🗑️ Rimuovi l'elemento dal carrello
        result = cart.remove_item(item_id)

        # 🔍 Gestione di eventuali errori
        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        # #print(f"Errore completo: {str(e)}")
        return jsonify({"error": f"Errore durante la rimozione del prodotto: {str(e)}"}), 500

@api.route('/cart', methods=['GET'])
@jwt_required()
def get_user_cart_basic():
    try:
        user_id = get_jwt_identity()

        # 🔍 Recupera il carrello attivo per l'utente
        carts = Cart.get_carts_by_user(user_id)
        active_cart = next((cart for cart in carts if cart['status'] == 'active'), None)

        if not active_cart:
            return jsonify({"error": "Nessun carrello attivo trovato per l'utente."}), 404

        cart = Cart.query.get(active_cart['cart_id'])
        cart_data = cart.get_user_cart()

        return jsonify(cart_data), 200

    except Exception as e:
        # #print(f"Errore completo: {str(e)}")
        return jsonify({"error": f"Errore durante il recupero del carrello: {str(e)}"}), 500

@api.route('/cart/detailed', methods=['GET'])
@jwt_required()
def get_user_cart_detailed():
    try:
        user_id = get_jwt_identity()

        # 🔍 Recupera il carrello attivo per l'utente
        carts = Cart.get_carts_by_user(user_id)
        active_cart = next((cart for cart in carts if cart['status'] == 'active'), None)

        if not active_cart:
            return jsonify({"error": "Nessun carrello attivo trovato per l'utente."}), 404

        cart = Cart.query.get(active_cart['cart_id'])
        detailed_cart_data = cart.get_detailed_user_cart()

        return jsonify(detailed_cart_data), 200

    except Exception as e:
        # #print(f"Errore completo: {str(e)}")
        return jsonify({"error": f"Errore durante il recupero dettagliato del carrello: {str(e)}"}), 500

######################## BOOKINGS #########################

@api.route('/booking', methods=['POST'])
@jwt_required()
def create_booking():
    try:
        user_id = get_jwt_identity()

        # ✅ Controlla se il corpo della richiesta è in formato JSON
        if not request.is_json:
            return jsonify({"error": "Il corpo della richiesta deve essere in formato JSON."}), 400

        data = request.get_json()

        # 🔍 Verifica dei dati obbligatori
        required_fields = [
            "bike_id", "start_date", "end_date", "total_price",
            "dl_type", "dl_expiration", "dl_number"
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Campi obbligatori mancanti: {', '.join(missing_fields)}"}), 400

        # 🕒 Converti le date in formato datetime
        try:
            start_date = datetime.strptime(data['start_date'], "%Y-%m-%d %H:%M:%S")
            end_date = datetime.strptime(data['end_date'], "%Y-%m-%d %H:%M:%S")
            dl_expiration = datetime.strptime(data['dl_expiration'], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Formato data non valido. Usa 'YYYY-MM-DD HH:MM:SS'."}), 400

        # 🔍 Verifica disponibilità della moto
        if not Booking.check_availability(data['bike_id'], start_date, end_date):
            return jsonify({"error": "La moto non è disponibile per le date selezionate."}), 400

        # 🔍 Controlla conflitti con altre prenotazioni
        date_conflict = Booking.check_date_conflict_in_cart(user_id, start_date, end_date)
        if date_conflict:
            return jsonify(date_conflict), 400

        # ➕ Crea la prenotazione
        booking_data = {
            "bike_id": data['bike_id'],
            "customer_id": user_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_price": data['total_price'],
            "accessories": data.get('accessories', []),
            "dl_type": data['dl_type'],
            "dl_expiration": dl_expiration,
            "dl_number": data['dl_number'],
            "helmet_size": data.get('helmet_size'),
            "gloves_size": data.get('gloves_size'),
            "pickup": data.get('pickup', False),
            "return_": data.get('return_', False)
        }

        new_booking = Booking.create_booking(booking_data)

        return jsonify({
            "message": "Prenotazione creata con successo.",
            "booking": new_booking
        }), 201

    except Exception as e:
        return jsonify({"error": f"Errore durante la creazione della prenotazione: {str(e)}"}), 500

@api.route('/booking/<int:booking_id>', methods=['DELETE'])
@jwt_required()
def delete_booking(booking_id):
    try:
        user_id = get_jwt_identity()

        # 🔍 Utilizza il metodo della classe per eliminare la prenotazione
        result = Booking.delete_booking(booking_id, user_id)

        # Controlla se la prenotazione è stata trovata o è già cancellata
        if "error" in result:
            return jsonify({"error": result["error"]}), 404

        return jsonify({
            "message": "Prenotazione cancellata con successo.",
            "booking": result
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la cancellazione della prenotazione: {str(e)}"}), 500

@api.route('/all-bookings', methods=['GET'])
@jwt_required()
@admin_required
def get_all_bookings():
    try:
        # 🔍 Recupera tutte le prenotazioni utilizzando il metodo della classe
        all_bookings = Booking.get_all_bookings()

        # 🔄 Aggiunge il codice di prenotazione, nome utente e modello veicolo a ciascun booking
        detailed_bookings = []
        for booking in all_bookings:
            # 🔢 Recupera il codice di prenotazione
            booking_code_data = Booking.get_booking_code_by_booking_id(booking['id'])
            booking_code = (
                booking_code_data.get('booking_code')
                if 'booking_code' in booking_code_data
                else None
            )

            # 🔍 Recupera le informazioni del cliente
            customer = User.query.get(booking['customer_id'])
            customer_name = f"{customer.name} {customer.surname}" if customer else "Non trovato"

            # 🔍 Recupera le informazioni del veicolo
            vehicle = Vehicle.query.get(booking['bike_id'])
            vehicle_info = f"{vehicle.brand} {vehicle.model}" if vehicle else "Non trovato"

            # ➕ Aggiunge i dettagli al booking
            booking['booking_code'] = booking_code
            booking['customer_name'] = customer_name
            booking['vehicle_info'] = vehicle_info
            detailed_bookings.append(booking)

        # ✅ Restituisce tutte le prenotazioni con i dettagli aggiuntivi
        return jsonify({
            "message": "Elenco di tutte le prenotazioni recuperato con successo.",
            "bookings": detailed_bookings
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero delle prenotazioni: {str(e)}"}), 500

@api.route('/booking/<int:booking_id>', methods=['PUT'])
@jwt_required()
def update_booking(booking_id):
    try:
        user_id = get_jwt_identity()

        # ✅ Controlla se il corpo della richiesta è in formato JSON
        if not request.is_json:
            return jsonify({"error": "Il corpo della richiesta deve essere in formato JSON."}), 400

        data = request.get_json()

        # 🔍 Controlla che siano stati inviati dati da aggiornare
        if not data:
            return jsonify({"error": "Nessun dato fornito per l'aggiornamento."}), 400

        # 🔍 Utilizza il metodo della classe per aggiornare la prenotazione
        result = Booking.update_booking(booking_id, user_id, data)

        # Controlla se si è verificato un errore
        if "error" in result:
            return jsonify({"error": result["error"]}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante l'aggiornamento della prenotazione: {str(e)}"}), 500

@api.route('/booking/user', methods=['GET'])
@jwt_required()
def get_user_bookings():
    try:
        user_id = get_jwt_identity()

        # 🔍 Recupera tutte le prenotazioni dell'utente usando il metodo della classe
        bookings = Booking.get_bookings_by_customer(user_id)

        # 🔄 Aggiungi i dettagli del veicolo e il codice di prenotazione
        detailed_bookings = []
        for booking in bookings:
            # 🔍 Aggiungi i dettagli del veicolo
            vehicle = Vehicle.find_by_id(booking['bike_id'])
            if vehicle:
                booking['vehicle'] = vehicle.to_dict()

            detailed_bookings.append(booking)

        return jsonify({
            "message": "Elenco delle prenotazioni recuperato con successo.",
            "bookings": detailed_bookings
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero delle prenotazioni: {str(e)}"}), 500

@api.route('/bookings/vehicle/<int:bike_id>', methods=['GET'])
def get_bookings_by_vehicle(bike_id):
    try:
        # 🔍 Recupera tutte le prenotazioni per il veicolo usando il metodo della classe
        bookings = Booking.get_bookings_by_vehicle(bike_id)

        # Controlla se ci sono prenotazioni
        if isinstance(bookings, dict) and "error" in bookings:
            return jsonify({"error": bookings["error"]}), 404

        return jsonify({
            "message": "Elenco delle prenotazioni recuperato con successo.",
            "bookings": bookings
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero delle prenotazioni: {str(e)}"}), 500

@api.route('/booking/<int:booking_id>/payment', methods=['PATCH'])
@jwt_required()
def update_payment_status(booking_id):
    try:
        user_id = get_jwt_identity()

        # 🔍 Usa il metodo della classe per aggiornare il pagamento
        result = Booking.update_payment_status(booking_id, user_id)

        # Controlla se ci sono errori
        if "error" in result:
            return jsonify({"error": result["error"]}), 404 if "non trovata" in result["error"] else 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante l'aggiornamento dello stato di pagamento: {str(e)}"}), 500

@api.route('/cart/submit', methods=['POST'])
@jwt_required()
def submit_cart():
    try:
        user_id = get_jwt_identity()

        # ✅ Controlla se il corpo della richiesta è in formato JSON
        if not request.is_json:
            return jsonify({"error": "Il corpo della richiesta deve essere in formato JSON."}), 400

        extra_data = request.get_json()

        # 🔍 Recupera il carrello attivo
        carts = Cart.get_carts_by_user(user_id)
        active_cart = next((cart for cart in carts if cart['status'] == 'active'), None)

        if not active_cart:
            return jsonify({"error": "Nessun carrello attivo trovato per l'utente."}), 404

        cart = Cart.query.get(active_cart['cart_id'])

        # 🔄 Usa il metodo della classe per sottomettere il carrello con i dati extra
        result = cart.submit_cart_as_order(extra_data)

        # Controlla se si è verificato un errore
        if "error" in result:
            return jsonify({"error": result["error"]}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la sottomissione del carrello: {str(e)}"}), 500

@api.route('/cart/clear', methods=['DELETE'])
@jwt_required()
def clear_cart():
    try:
        user_id = get_jwt_identity()

        # 🔍 Recupera il carrello attivo
        carts = Cart.get_carts_by_user(user_id)
        active_cart = next((cart for cart in carts if cart['status'] == 'active'), None)

        if not active_cart:
            return jsonify({"error": "Nessun carrello attivo trovato per l'utente."}), 404

        cart = Cart.query.get(active_cart['cart_id'])

        # 🔄 Usa il metodo della classe per eliminare tutti i prodotti
        result = cart.clear_cart()

        # Controlla se si è verificato un errore
        if "error" in result:
            return jsonify({"error": result["error"]}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la cancellazione del carrello: {str(e)}"}), 500

@api.route('/booking/code/<int:generated_code>', methods=['GET'])
@jwt_required()
def get_booking_by_code(generated_code):
    try:
        user_id = get_jwt_identity()

        # 🔍 Recupera l'utente autenticato
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Utente non trovato."}), 404

        # 🔍 Usa il metodo della classe per recuperare la prenotazione
        booking = Booking.get_booking_by_code(generated_code)

        # Controlla se la prenotazione è stata trovata
        if booking is None:
            return jsonify({"error": "Prenotazione non trovata."}), 404

        # 🔒 Controllo dei permessi di accesso:
        if booking["customer_id"] != user_id and user.role != "admin":
            return jsonify({"error": "Accesso negato. La prenotazione non appartiene all'utente o non sei un admin."}), 403

        # 🔍 Recupera i dati completi del cliente
        customer = User.query.get(booking["customer_id"])
        if not customer:
            return jsonify({"error": "Utente associato alla prenotazione non trovato."}), 404

        # 🏍️ Recupera i dettagli del veicolo associato
        vehicle = Vehicle.query.get(booking["bike_id"])
        if not vehicle:
            return jsonify({"error": "Veicolo associato alla prenotazione non trovato."}), 404

        # 📄 Costruisce la risposta dettagliata
        detailed_booking = {
            "id": booking["id"],
            "booking_code": generated_code,
            "start_date": booking["start_date"],
            "end_date": booking["end_date"],
            "total_price": booking["total_price"],
            "payment_status": booking["payment_status"],
            "pickup": booking["pickup"],
            "return_": booking["return_"],
            "status": booking["status"],
            "user": {
                "id": customer.id,
                "name": customer.name,
                "surname": customer.surname,
                "email": customer.email,
                "bday": customer.bday.strftime("%Y-%m-%d") if customer.bday else None,
                "place": customer.place,
                "role": customer.role
            },
            "vehicle": {
                "id": vehicle.id,
                "brand": vehicle.brand,
                "model": vehicle.model,
                "year": vehicle.year,
                "license_plate": vehicle.license_plate,
                "fuel_type": vehicle.fuel_type,
                "deposit": vehicle.deposit,
                "power": vehicle.power,
                "image_url": vehicle.image_url,
                "description": vehicle.description
            }
        }

        return jsonify({
            "message": "Prenotazione trovata con successo.",
            "booking": detailed_booking
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero della prenotazione: {str(e)}"}), 500

@api.route('/check-user-booking-conflict', methods=['POST'])
@jwt_required()
def check_user_booking_conflict():
    """
    🔍 Controlla se l'utente ha altre prenotazioni nello stesso intervallo di date.
    ---
    tags:
      - Bookings
    consumes:
      - application/json
    responses:
      200:
        description: Restituisce se c'è un conflitto o meno
      400:
        description: Dati non validi
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Controlla la presenza dei dati richiesti
        if not data or "start_date" not in data or "end_date" not in data:
            return jsonify({"error": "Dati mancanti o non validi."}), 400

        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d %H:%M:%S")

        # Verifica se ci sono prenotazioni in conflitto
        has_conflict = Booking.has_conflicting_booking(user_id, start_date, end_date)

        return jsonify({
            "user_id": user_id,
            "has_conflict": has_conflict
        }), 200

    except ValueError:
        return jsonify({"error": "Formato data non valido. Usa il formato YYYY-MM-DD HH:MM:SS."}), 400
    except Exception as e:
        return jsonify({"error": f"Errore durante il controllo del conflitto: {str(e)}"}), 500

@api.route('/bookings_by_name', methods=['GET'])
@jwt_required()
def get_bookings_by_name():
    try:
        first_name = request.args.get('first_name', '').strip()
        last_name = request.args.get('last_name', '').strip()

        if not first_name or not last_name:
            return jsonify({"error": "I parametri 'first_name' e 'last_name' sono obbligatori."}), 400

        # Recupera le prenotazioni dettagliate
        bookings = Booking.get_detailed_bookings_by_name(first_name, last_name)

        if not bookings:
            return jsonify({"message": "Nessuna prenotazione trovata per questo utente."}), 200

        return jsonify({"bookings": bookings}), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la ricerca delle prenotazioni: {str(e)}"}), 500

@api.route('/booking/generate-code', methods=['POST'])
@jwt_required()
def generate_booking_code_without_saving():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # 🔍 Controllo dei dati richiesti
        required_fields = ["bike_id", "booking_id", "start_date", "end_date"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Dati richiesti mancanti."}), 400

        bike_id = data["bike_id"]
        booking_id = data["booking_id"]
        start_date = data["start_date"]
        end_date = data["end_date"]

        # 🔢 Genera solo il codice senza salvarlo nel database
        result = BookingCode.generate_code_only(user_id, bike_id, booking_id, start_date, end_date)

        if "error" in result:
            return jsonify({"error": result["error"]}), 404

        return jsonify({
            "message": "Codice generato con successo.",
            "generated_code": result["generated_code"]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la generazione del codice: {str(e)}"}), 500

########################## UTILS ##########################

@api.route('/booking/<int:booking_id>/toggle-pickup', methods=['PATCH'])
@jwt_required()
def toggle_pickup(booking_id):
    try:
        user_id = get_jwt_identity()
        result = Booking.toggle_pickup(booking_id, user_id)

        if "error" in result:
            return jsonify({"error": result["error"]}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il toggle del campo pickup: {str(e)}"}), 500

@api.route('/booking/<int:booking_id>/toggle-return', methods=['PATCH'])
@jwt_required()
def toggle_return(booking_id):
    try:
        user_id = get_jwt_identity()
        result = Booking.toggle_return(booking_id, user_id)

        if "error" in result:
            return jsonify({"error": result["error"]}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il toggle del campo return: {str(e)}"}), 500

@api.route('/booking/<int:booking_id>/toggle-payment', methods=['PATCH'])
@jwt_required()
def toggle_payment_status(booking_id):
    try:
        user_id = get_jwt_identity()
        result = Booking.toggle_payment_status(booking_id, user_id)

        if "error" in result:
            return jsonify({"error": result["error"]}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il toggle del campo payment_status: {str(e)}"}), 500

@api.route('/protected', methods=['GET'])
@jwt_required()
def protected_route():
    """
    Rotta protetta accessibile solo con un token JWT valido
    """
    user_id = get_jwt_identity()
    return jsonify({"message": f"Accesso consentito. ID utente: {user_id}"}), 200

@api.route('/booking/add-code', methods=['POST'])
@jwt_required()
def api_add_booking_code():
    try:
        user_id = get_jwt_identity()  # Recupera l'utente autenticato
        data = request.get_json()

        # 🔍 Controllo dei dati richiesti
        required_fields = ["booking_id", "generated_code"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Dati richiesti mancanti."}), 400

        booking_id = data["booking_id"]
        generated_code = data["generated_code"]

        # ➕ Usa il metodo della classe per aggiungere il codice
        result = BookingCode.add_booking_code(booking_id, generated_code)

        # 🚫 Restituisci un errore se qualcosa è andato storto
        if "error" in result:
            return jsonify({"error": result["error"]}), 400

        # ✅ Codice aggiunto con successo
        return jsonify({
            "message": "Codice di prenotazione aggiunto con successo.",
            "generated_code": result["generated_code"]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante l'aggiunta del codice: {str(e)}"}), 500

@api.route('/user/<int:user_id>/send-email', methods=['POST'])
@jwt_required()
def send_email_to_user(user_id):
    try:
        # 🔍 Recupera l'utente
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Utente non trovato."}), 404

        # 📥 Ricevi i dati della mail dal JSON
        if not request.is_json:
            return jsonify({"error": "Il corpo della richiesta deve essere in formato JSON."}), 400

        data = request.get_json()
        subject = data.get("subject")
        body = data.get("body")

        # 🔍 Controlla se i dati sono validi
        if not subject or not body:
            return jsonify({"error": "Subject e body sono obbligatori."}), 400

        # 📧 Invia l'email usando il metodo della classe User
        result = user.send_email(subject, body)

        # Gestione degli errori
        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante l'invio dell'email: {str(e)}"}), 500
