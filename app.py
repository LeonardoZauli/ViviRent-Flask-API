from flask import Flask
from extensions import mail  # Importa l'estensione Mail
from config import Config
from models import db, TokenBlacklist
from routes import api  # Importa il Blueprint definito
from flasgger import Swagger
from flask_cors import CORS
from flask_jwt_extended import JWTManager



# Configurazione dell'app Flask
app = Flask(__name__)
app.config.from_object(Config)
app.config['JWT_TOKEN_LOCATION'] = ['cookies']  # 🔥 Assicura che Flask legga i JWT solo dai cookie
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'  # Nome del cookie JWT
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # 🔥 Disabilita la protezione CSRF per il test (puoi abilitarla più tardi)

db.init_app(app)

# 🔒 Lista dei token invalidati
jwt_blacklist = set()

# Abilita CORS per tutte le rotte
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "https://localhost:5173"}})

# ✅ Configurazione JWT
jwt = JWTManager(app)

@jwt.token_in_blocklist_loader
def check_if_token_is_blacklisted(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return TokenBlacklist.is_token_blacklisted(jti)

# ✅ Configurazione Swagger
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "ViviRent API",
        "description": "Questa API consente di gestire utenti e operazioni relative.",
        "version": "1.0.0"
    },
    "basePath": "/api"  # Prefisso delle rotte
})

# ✅ Registra il Blueprint
app.register_blueprint(api, url_prefix='/api')

# Esegui l'app Flask
if __name__ == '__main__':
    app.run(ssl_context=('cert.pem', 'key.pem'), debug=True)

