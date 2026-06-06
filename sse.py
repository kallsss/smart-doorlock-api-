from flask import Response, Blueprint
from flask_jwt_extended import jwt_required
from config.db import get_db_connection
import json
import time

sse_bp = Blueprint("sse_bp", __name__)

@sse_bp.route('/stream', methods=['GET'])
def stream_logs():

    def event_stream():

        last_id = 0

        while True:

            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT
                    log_access.id,
                    user_door.name,
                    log_access.method,
                    log_access.created_at

                FROM log_access

                JOIN user_door
                ON log_access.user_id = user_door.id

                ORDER BY log_access.id DESC
                LIMIT 1
                """
            )

            row = cur.fetchone()
            if row:
                current_id = row[0]
                if current_id != last_id:

                    data = {
                        "id": row[0],
                        "name": row[1],
                        "method": row[2],
                        "created_at": str(row[3])
                    }

                    yield f"data: {json.dumps(data)}\n\n"

                    last_id = current_id

            cur.close()
            conn.close()

            time.sleep(2)

    return Response(
        event_stream(),
        mimetype="text/event-stream"
    )
# @door_bp.route('/stream')
# def stream():

#     def event_stream():

#         conn = get_db_connection()
#         cur = conn.cursor()

#         cur.execute("""
#             SELECT *
#             FROM log_access
#             ORDER BY id DESC
#             LIMIT 1
#         """)

#         row = cur.fetchone()

#         yield f"data: {row}\n\n"

#     return Response(
#         event_stream(),
#         mimetype="text/event-stream"
#     )
