from flask import Blueprint
bp = Blueprint('directeur', __name__)
from app.directeur import routes
