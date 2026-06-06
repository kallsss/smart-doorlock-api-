from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from datetime import timedelta
from config.db import get_db_connection
import bcrypt

token_bp = Blueprint("token_bp", __name__)

#TOKEN ANDROID
@token_bp.route('/login', methods=['POST'])
def login():

    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, password
        FROM user_android
        WHERE name=%s
        """,
        (username,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:

        user_id = user[0]
        hashed_password = user[1]

        if bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        ):

            token = create_access_token(
                identity=f"user_{user_id}",
                expires_delta=timedelta(days=30)
            )

            return jsonify({
                "status": "success",
                "type": "android",
                "access_token": token
            })

    return jsonify({
        "status": "failed",
        "message": "Username atau password salah"
    }), 401

#TOKEN ESP 32
@token_bp.route('/esp/login', methods=['POST'])
def esp_login():

    data = request.get_json()

    client_id = data.get("client_id")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, door_name FROM door WHERE client_id=%s",
        (client_id,)
    )

    door = cur.fetchone()

    cur.close()
    conn.close()

    if door:
        token = create_access_token(
            identity=f"esp_{client_id}",
            expires_delta=timedelta(days=365)
        )

        return jsonify({
            "status": "success",
            "type": "esp32",
            "door_name": door[1],
            "access_token": token
        })

    return jsonify({
        "status": "failed",
        "message": "ESP tidak terdaftar"
    }), 401