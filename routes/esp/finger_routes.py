from flask import Blueprint, request, jsonify
from config.db import get_db_connection
from datetime import datetime
from modules.faceRecognition import FaceAuthenticator

finger_bp = Blueprint("finger_bp", __name__)

@finger_bp.route('/RegisterFingerprint', methods=['POST'])
def enroll_fingerprint():

    data = request.get_json()

    user_id = data.get("user_id")
    door_access = data.get("door_access")

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT id
            FROM user_door
            WHERE id=%s
            """,
            (user_id,)
        )

        user = cur.fetchone()

        if user is None:

            return jsonify({
                "status": "failed",
                "message": "User tidak ditemukan"
            }), 404

        cur.execute(
            "INSERT INTO fingerprint (user_id, finger_id, door_access) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (user_id, user_id, door_access)
        )
        

        # Ambil verdb terbaru
        cur.execute(
            """
            SELECT COALESCE(MAX(verdb), 0) FROM sync_changes
            """
        )

        latest_verdb = cur.fetchone()[0]
        new_verdb = latest_verdb + 1

        # Catat perubahan untuk sinkronisasi ESP
        cur.execute(
            """
            INSERT INTO sync_changes
            (user_id, action, verdb)
            VALUES (%s,%s,%s)
            """,
            (user_id, "update", new_verdb)
        )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Fingerprint berhasil didaftarkan",
            "finger_id": user_id
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

@finger_bp.route('/DeleteFingerprint', methods=['DELETE'])
def delete_fingerprint():

    data = request.get_json()

    user_id = data.get("user_id")

    conn = get_db_connection()
    cur = conn.cursor()

    print("user_id =", user_id)

    try:

        cur.execute(
            
            """
            SELECT id
            FROM user_door
            WHERE id=%s
            """,
            (user_id,)
        )

        user = cur.fetchone()

        if user is None:

            return jsonify({
                "status": "failed",
                "message": "User tidak ditemukan"
            }), 404

        cur.execute(
            """
            DELETE FROM fingerprint
            WHERE user_id=%s
            """,
            (user_id,)
        )

        # Ambil verdb terbaru
        cur.execute(
            """
            SELECT COALESCE(MAX(verdb), 0)
            FROM sync_changes
            """
        )

        latest_verdb = cur.fetchone()[0]
        new_verdb = latest_verdb + 1

        # Catat perubahan sinkronisasi
        cur.execute(
            """
            INSERT INTO sync_changes
            (
                user_id,
                action,
                verdb
            )
            VALUES (%s,%s,%s)
            """,
            (
                user_id,
                "update",
                new_verdb
            )
        )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Fingerprint berhasil dihapus",
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