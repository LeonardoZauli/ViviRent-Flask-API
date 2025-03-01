from flask import Flask
from extensions import mail  # Importa l'estensione Mail
from config import Config
from models import db
from routes import api  # Importa il Blueprint definito
from flasgger import Swagger
from flask_cors import CORS
from flask_jwt_extended import JWTManager
