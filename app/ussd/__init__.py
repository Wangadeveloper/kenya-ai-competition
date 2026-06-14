from flask import Blueprint

ussd_bp = Blueprint('ussd', __name__)

from app.ussd import routes
