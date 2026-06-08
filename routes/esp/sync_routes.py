from flask import Blueprint, request, jsonify
from config.db import get_db_connection

syncusers_bp = Blueprint("syncusers_bp", __name__)

@syncusers_bp.route('/sync/users', methods=['GET'])
def sync_users():

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        
        current_verdb = int(
            request.args.get("verdb", 0)
        )

        full_sync = (
            request.args.get("full", "false").lower()
            == "true"
        )

        updated_users = []
        deleted_ids = []

        # Ambil verdb terbaru
        cur.execute("""
            SELECT COALESCE(MAX(verdb), 0)
            FROM sync_changes
        """)

        latest_verdb = cur.fetchone()[0]

        # FULL SYNC
        if full_sync:

            cur.execute("""
                SELECT u.id, u.name, u.pin, u.uid_rfid, f.finger_id
                FROM user_door u LEFT JOIN fingerprint f
                ON u.id = f.user_id
            """)

            users = cur.fetchall()
            for user in users:

                updated_users.append({
                    "id": user[0],
                    "name": user[1],
                    "PIN": user[2],
                    "RFID": user[3],
                    "Fingerprint": user[4]

                })

            return jsonify({
                "mode": "full",
                "verdb": latest_verdb,
                "updated_users": updated_users,
                "deleted_ids": []

            })

        #Incremental sync
        cur.execute(
            """
            SELECT user_id, action, verdb
            FROM sync_changes
            WHERE verdb > %s
            ORDER BY verdb ASC
            """,
            (current_verdb,)
        )

        changes = cur.fetchall()
        processed_updates = set()

        for change in changes:
            user_id = change[0]
            action = change[1]

            if action == "delete":
                deleted_ids.append(user_id)
                continue

            if action in ["insert", "update"]:

                if user_id in processed_updates:
                    continue

                processed_updates.add(user_id)

                cur.execute(
                    """
                    SELECT u.id, u.name, u.pin, u.uid_rfid, f.finger_id
                    FROM user_door u
                    LEFT JOIN fingerprint f ON u.id = f.user_id
                    WHERE u.id = %s
                    """,
                    (user_id,)
                )

                user = cur.fetchone()
                if user:
                    updated_users.append({

                        "id": user[0],
                        "name": user[1],
                        "PIN": user[2],
                        "RFID": user[3],
                        "Fingerprint": user[4]

                    })

        return jsonify({

            "mode": "incremental",
            "verdb": latest_verdb,
            "updated_users": updated_users,
            "deleted_ids": deleted_ids

        })

    except Exception as e:

        return jsonify({

            "status": "failed",
            "message": str(e)

        }), 500

    finally:
        cur.close()
        conn.close()