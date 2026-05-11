from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect


db = SQLAlchemy()
socketio = SocketIO(async_mode="threading", cors_allowed_origins=[])
csrf = CSRFProtect()
