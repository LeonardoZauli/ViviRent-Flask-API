from flask import Flask, send_from_directory
from config import Config
from models import db, TokenBlacklist
from routes import api
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from swagger_confing import init_swagger
import os

app = Flask(__name__)
app.config.from_object(Config)

# JWT configuration
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False


db.init_app(app)

jwt = JWTManager(app)

@jwt.token_in_blocklist_loader
def check_if_token_is_blacklisted(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return TokenBlacklist.is_token_blacklisted(jti)

# CORS configuration
CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5000", "https://localhost:5173", "https://127.0.0.1:5000"]}})

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
