from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from config.db import get_db_connection
from datetime import datetime
from modules.faceRecognition import FaceAuthenticator
import bcrypt

android_bp = Blueprint("android_bp", __name__)

#REGISTRASI USER
@android_bp.route('/users', methods=['POST'])
def register_user():

    data = request.get_json()

    name = data.get("name")
    pin = data.get("pin")
    uid_rfid = data.get("uid_rfid")
    door_access = data.get("door_access")

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            INSERT INTO user_door
            (name, pin, uid_rfid, door_access, created_at )
            VALUES (%s,%s,%s,%s,NOW())
            RETURNING id
            """,
            (name, pin, uid_rfid, door_access )
        )

        user_id = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COALESCE(MAX(verdb),0)
            FROM sync_changes
            """
        )

        new_verdb = cur.fetchone()[0] + 1

        cur.execute(
            """
            INSERT INTO sync_changes
            (user_id, action, verdb) VALUES (%s,%s,%s)
            """,
            (user_id, "insert", new_verdb)
        )


        conn.commit()

        return jsonify({
            "status": "success",
            "message": "User berhasil dibuat",
            "user_id": user_id
        })

    except Exception as e:

        conn.rollback()

        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500

    finally:

        cur.close()
        conn.close()

@android_bp.route('/admins', methods=['POST'])
def register_admin():

    data = request.get_json()

    name = data.get("name")
    password = data.get("password")

    # HASH PASSWORD
    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO user_android
        (name, password, created_at)
        VALUES (%s, %s, NOW())
        """,
        (name, hashed_password)
    )

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Admin berhasil dibuat"
    })

@android_bp.route('/logs', methods=['GET'])
@jwt_required()
def get_logs():

    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(
        """
        SELECT log_access.id, user_door.name, log_access.method, log_access.created_at
        FROM log_access
        JOIN user_door ON log_access.user_id = user_door.id
        ORDER BY log_access.created_at DESC -- Urutkan dari yang terbaru
        """
    )
    rows = cur.fetchall()
    data = [{"id": r[0], "name": r[1], "method": r[2], "created_at": str(r[3])} for r in rows]
    cur.close()
    conn.close()
    return jsonify(data)


@android_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            u.id,           -- index 0
            u.name,         -- index 1
            u.created_at,   -- index 2
            u.uid_rfid,     -- index 3
            u.pin,          -- index 4
            u.door_access,  -- index 5
            EXISTS(SELECT 1 FROM fingerprint f WHERE f.user_id = u.id) as has_finger, -- index 6
            EXISTS(SELECT 1 FROM embeddings e WHERE e.user_id = u.id) as has_face     -- index 7
        FROM user_door u
        ORDER BY u.created_at ASC
        """
    )

    rows = cur.fetchall()
    data = []

    for row in rows:
        methods = []
        if row[3]: methods.append("rfid")  
        if row[4]: methods.append("pin")   
        if row[6]: methods.append("finger") 
        if row[7]: methods.append("face")   

        data.append({
            "id": str(row[0]),       
            "name": row[1],
            "methods": methods,
            "created_at": str(row[2]),
            "door_access": int(row[5]) if row[5] is not None else 0, 
            "uid_rfid": row[3], 
            "pin": row[4]
        })

    cur.close()
    conn.close()

    return jsonify(data)


@android_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):

    name = request.form.get("name")
    pin = request.form.get("pin")
    uid_rfid = request.form.get("uid_rfid")

    methods = request.form.getlist("methods")

    image_files = request.files.getlist("image")

    has_face = "face" in methods

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # cek status lama
        cur.execute(
            """
            SELECT face_recog
            FROM user_door
            WHERE id=%s
            """,
            (user_id,)
        )

        result = cur.fetchone()
        old_face = result[0] if result else False

        # face dicabut
        if old_face and not has_face:

            FaceAuthenticator.delete_faces_db(
                user_id
            )

        # face masih ada dan upload foto baru
        elif has_face and len(image_files) > 0:
            FaceAuthenticator.delete_faces_db(
                user_id
        )

            for image_file in image_files:
                image_path = f"temp_{image_file.filename}"
                image_file.save(image_path)
                session = FaceAuthenticator(
                    image_path,
                    "yunet",
                    "Facenet512"
                )

                session.register_face_db(
                    user_id
                )

        cur.execute(
            """
            UPDATE user_door
            SET
                name=%s,
                pin=%s,
                uid_rfid=%s,
                face_recog=%s
            WHERE id=%s
            """,
            (
                name,
                pin,
                uid_rfid,
                has_face,
                user_id
            )
        )

        cur.execute(
            """
            SELECT COALESCE(MAX(verdb),0)
            FROM sync_changes
            """
        )

        new_verdb = cur.fetchone()[0] + 1

        cur.execute(
            """
            INSERT INTO sync_changes
            (user_id, action, verdb) VALUES (%s, %s, %s )
            """,
            (user_id, "update", new_verdb)
        )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "User berhasil diupdate"
        })

    except Exception as e:

        conn.rollback()

        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500

    finally:

        cur.close()
        conn.close()

@android_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        cur.execute(
        """
        SELECT COALESCE(MAX(verdb),0)
        FROM sync_changes
        """
        )

        new_verdb = cur.fetchone()[0] + 1

        cur.execute(
            """
            INSERT INTO sync_changes
            (user_id, action, verdb)
            VALUES
            (%s, %s, %s)
            """,
            (user_id, "delete", new_verdb)
        )
        
        try:
            FaceAuthenticator.delete_faces_db(user_id)
        except Exception as e:
            print("Delete face error:", e)
        
        cur.execute(
            "DELETE FROM fingerprint WHERE user_id=%s",
            (user_id,)
        )

        cur.execute(
            "DELETE FROM embeddings WHERE user_id=%s",
            (user_id,)
        )

        cur.execute(
            "DELETE FROM user_door WHERE id=%s",
            (user_id,)
        )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "User berhasil dihapus"
        })

    except Exception as e:

        conn.rollback()
        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()

