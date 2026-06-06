from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from config.db import get_db_connection
from datetime import datetime
from modules.faceRecognition import FaceAuthenticator
import bcrypt

android_bp = Blueprint("android_bp", __name__)

@android_bp.route('/GrantAccess', methods=['PUT'])
@jwt_required()
def grant_access():

    data = request.get_json()

    user_ids = data.get("user_ids")

    if not user_ids:

        return jsonify({
            "status": "failed",
            "message": "No user IDs provided"
        }), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        format_strings = ','.join(['%s'] * len(user_ids))

        # Update user_door
        cur.execute(
            f"""
            UPDATE user_door
            SET door_access = 1
            WHERE id IN ({format_strings})
            """,
            tuple(user_ids)
        )

        # Update fingerprint
        cur.execute(
            f"""
            UPDATE fingerprint
            SET door_access = 1
            WHERE user_id IN ({format_strings})
            """,
            tuple(user_ids)
        )

        # Ambil verdb terbaru
        cur.execute(
            """
            SELECT COALESCE(MAX(verdb), 0)
            FROM sync_changes
            """
        )

        latest_verdb = cur.fetchone()[0]

        # Catat perubahan sync
        for index, user_id in enumerate(user_ids, start=1):

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
                    latest_verdb + index
                )
            )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Akses berhasil diberikan"
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

@android_bp.route('/RevokeAccess', methods=['PUT'])
@jwt_required()
def revoke_access():

    data = request.get_json()

    user_ids = data.get("user_ids")

    if not user_ids:

        user_id = data.get("user_id")

    if user_id:
        user_ids = [int(user_id)]

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        format_strings = ','.join(['%s'] * len(user_ids))

        # Cabut akses user_door
        cur.execute(
            f"""
            UPDATE user_door
            SET door_access = NULL
            WHERE id IN ({format_strings})
            """,
            tuple(user_ids)
        )

        # Cabut akses fingerprint
        cur.execute(
            f"""
            UPDATE fingerprint
            SET door_access = NULL
            WHERE user_id IN ({format_strings})
            """,
            tuple(user_ids)
        )

        # Ambil verdb terbaru
        cur.execute(
            """
            SELECT COALESCE(MAX(verdb), 0)
            FROM sync_changes
            """
        )

        latest_verdb = cur.fetchone()[0]

        # Tambah sync_changes untuk setiap user
        for index, user_id in enumerate(user_ids, start=1):

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
                    latest_verdb + index
                )
            )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Akses berhasil dicabut"
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
