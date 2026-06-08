from flask import Blueprint, request, jsonify
from config.db import get_db_connection

doorstatus_bp = Blueprint("status_bp", __name__)

@doorstatus_bp.route('/doors/<int:door_id>/status', methods=['POST'])
def update_door_status():

    data = request.get_json()

    door_id = request.view_args["door_id"]
    
    ssid_wifi = data.get("ssid_wifi")
    battery = data.get("battery")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE door
        SET ssid_wifi=%s, battery=%s
        WHERE id=%s
        """,
        (
            ssid_wifi,
            battery,
            door_id
        )
    )

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success"
    })