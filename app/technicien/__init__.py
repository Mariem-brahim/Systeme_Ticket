from flask import Blueprint
bp = Blueprint('technicien', __name__)
from app.technicien import routes
