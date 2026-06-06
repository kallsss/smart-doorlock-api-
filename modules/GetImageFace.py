from flask import Blueprint, send_from_directory
import os

getimage_bp = Blueprint("getimage_bp", __name__)

# Tambahkan route ini
@getimage_bp.route('/faces/<user_id>/<filename>')
def get_face_image(user_id, filename):
    # Sesuaikan path-nya dengan lokasi di komputer kamu
    faces_dir = os.path.join(r'C:\faces_db', user_id)
    return send_from_directory(faces_dir, filename)