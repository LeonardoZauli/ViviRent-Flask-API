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
db.init_app(app)

# 🔒 Lista dei token invalidati
jwt_blacklist = set()

# Abilita CORS per tutte le rotte
CORS(app)

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
    app.run(debug=True)
