from flask import Blueprint, request, jsonify
from config.db import get_db_connection
from datetime import datetime
from modules.faceRecognition import FaceAuthenticator

espauth_bp = Blueprint("espauth_bp", __name__)

#Autentikasi User
def check_auth(cur, auth_type, auth_data, door_access, image_file=None):

    if auth_type == 11:

        cur.execute(
            "SELECT id, name FROM user_door WHERE pin=%s AND door_access=%s ",
            (auth_data, door_access)
        )

        return cur.fetchone()

    elif auth_type == 12:

        cur.execute(
            "SELECT id, name FROM user_door WHERE uid_rfid=%s AND door_access=%s",
            (auth_data, door_access)
        )

        return cur.fetchone()

    elif auth_type == 13:

        cur.execute(
            """
            SELECT user_door.id, user_door.name
            FROM fingerprint
            JOIN user_door
            ON fingerprint.user_id = user_door.id
            WHERE fingerprint.finger_id=%s
            AND fingerprint.door_access=%s
            """,
            (auth_data, door_access)
        )

        return cur.fetchone()

    elif auth_type == 14:

        print("=== FACE AUTH START ===")

        image_file = request.files.get("image")

        if image_file is None:
            print("File image tidak ada")
            return None

        image_path = "image_upload.jpg"
        image_file.save(image_path)

        session = FaceAuthenticator(
            image_path,
            "yunet",
            "Facenet512"
        )

        face_result = session.search_face_db()

        print("Face Result =", face_result)

        if face_result["user_id"] is None:
            print("User tidak dikenali")
            return None

        user_id = face_result["user_id"]

        cur.execute(
            """
            SELECT id, name
            FROM user_door
            WHERE id=%s
            AND door_access=%s
            """,
            (user_id, door_access)
        )

        return cur.fetchone()

@espauth_bp.route('/auth', methods=['POST'])
def auth_door():

    client_id = request.form.get("client_id")

    auth1_type = int(request.form.get("auth1_type"))
    auth1_data = request.form.get("auth1_data")

    auth2_type = int(request.form.get("auth2_type"))
    auth2_data = request.form.get("auth2_data")

    auth_type_name = {
        11: "pin",
        12: "rfid",
        13: "finger",
        14: "face"
    }

    conn = get_db_connection()
    cur = conn.cursor()

    # Cari door
    cur.execute(
        "SELECT id FROM door WHERE client_id=%s",
        (client_id,)
    )

    door = cur.fetchone()

    if door is None:

        cur.close()
        conn.close()

        return jsonify({
            "status": "failed",
            "message": "Door tidak ditemukan"
        }), 404

    door_access = door[0]

    # Autentikasi pertama
    result1 = check_auth(
        cur,
        auth1_type,
        auth1_data,
        door_access
    )

    if result1 is None:

        cur.close()
        conn.close()

        return jsonify({
            "status": "failed",
            "message": "Autentikasi pertama gagal"
        }), 401

    # Autentikasi kedua
    result2 = check_auth(
        cur,
        auth2_type,
        auth2_data,
        door_access
    )

    if result2 is None:

        cur.close()
        conn.close()

        return jsonify({
            "status": "failed",
            "message": "Autentikasi kedua gagal"
        }), 401

    # Pastikan user yang sama
    if result1[0] != result2[0]:

        cur.close()
        conn.close()

        return jsonify({
            "status": "failed",
            "message": "Metode autentikasi milik user berbeda"
        }), 401

    user_id = result1[0]
    user_name = result1[1]

    method_used = (
        auth_type_name[auth1_type]
        + ","
        + auth_type_name[auth2_type]
    )

    # Simpan log akses
    cur.execute(
        "INSERT INTO log_access (user_id,door_access,method,created_at) VALUES (%s, %s, %s, NOW())",
        (user_id,door_access,method_used)
    )

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Akses diterima",
        "user_id": user_id,
        "name": user_name,
        "door_access": door_access,
        "method": method_used
    })