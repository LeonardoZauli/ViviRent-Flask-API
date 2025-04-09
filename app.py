from flask import Flask, send_from_directory,jsonify
from config import Config
from models import db, TokenBlacklist
from routes import api, refresh_access_token
from flask import request
from flask_jwt_extended import create_access_token, get_jwt_identity
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from swagger_confing import init_swagger
import os

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

jwt = JWTManager(app)

@jwt.token_in_blocklist_loader
def check_if_token_is_blacklisted(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return TokenBlacklist.is_token_blacklisted(jti)

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):

    # ✅ Ottieni il refresh token dai cookie
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        print("❌ Nessun refresh token trovato nei cookie!")
        return jsonify({"error": "no_refresh_token", "message": "Nessun refresh token presente, fai il login"}), 401

    try:
        # ✅ Chiama direttamente refresh_access_token() e passa il token
        with app.test_request_context('/api/refresh', method="POST", headers={"Cookie": f"refresh_token={refresh_token}"}):
            response = refresh_access_token()

        print("✅ Access token rinnovato con successo!")
        return response

    except Exception as e:
        print("❌ Errore nel refresh token:", str(e))
        return jsonify({"error": "invalid_refresh_token", "message": "Refresh token non valido o scaduto"}), 401

# CORS configuration
CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["https://localhost:5173", "http://127.0.0.1:5000", "https://localhost:5176", "https://127.0.0.1:5000", "https://vivirent-react-web-production.up.railway.app"]}})

# Inizializzazione Swagger
init_swagger(app)

# Servire il file swagger.yaml
@app.route("/swagger.yaml")
def serve_swagger():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "swagger.yaml")

# Registrazione Blueprint
app.register_blueprint(api, url_prefix='/api')

if __name__ == '__main__':
    app.run(ssl_context=('cert.pem', 'key.pem'), debug=True)
