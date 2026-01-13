from flask import Blueprint
bp = Blueprint('utilisateur', __name__)
from app.utilisateur import routes
