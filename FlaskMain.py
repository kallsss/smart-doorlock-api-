from flask import Flask
from flask_jwt_extended import JWTManager
from routes.token_routes import token_bp
from routes.Android.dashboard_routes import android_bp
from routes.esp.face_routes import facerecog_bp
from routes.esp.sync_routes import syncusers_bp
from routes.esp.finger_routes import finger_bp
from routes.esp.auth_routes import espauth_bp
from routes.esp.status_routes import doorstatus_bp
from modules.GetImageFace import getimage_bp
from modules.faceRecognition import load_models

# Konfigurasi Face Recognition
FACE_DETECTOR = "yunet"
FACE_RECOGNITION = "Facenet512"

from sse import sse_bp

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = "super_secret_key_123456789"

jwt = JWTManager(app)

app.register_blueprint(token_bp)
app.register_blueprint(android_bp)
app.register_blueprint(sse_bp)
app.register_blueprint(syncusers_bp)
app.register_blueprint(getimage_bp)
app.register_blueprint(espauth_bp)
app.register_blueprint(finger_bp)
app.register_blueprint(doorstatus_bp)
app.register_blueprint(facerecog_bp)


if __name__ == "__main__":

    print("Loading Face Recognition Models...")

    load_models(
        FACE_DETECTOR,
        FACE_RECOGNITION
    )

    print("Models Loaded!")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
    