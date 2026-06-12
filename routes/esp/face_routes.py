from flask import Blueprint, request, jsonify
from modules.faceRecognition import FaceAuthenticator
from config.db import get_db_connection
import os

facerecog_bp = Blueprint("facerecog_bp", __name__)

ENROLL_FACE = 32

@facerecog_bp.route('/users/<int:user_id>/face', methods=['POST'])
def register_face(user_id):

    try:
        mode = int(request.form.get("mode"))
       
        if mode != ENROLL_FACE:
            return jsonify({
                "status": "failed",
                "message": "Mode harus ENROLL_FACE (32)"
            }), 400

        image_files = request.files.getlist("image")

       # Diubah ke < 1 agar bisa menerima penambahan foto satuan (increment 1)
        if len(image_files) < 1:
            return jsonify({
            "status": "failed",
            "message": "Harus mengirim minimal 1 foto wajah"
        }), 400
            
        # Jika ingin membatasi maksimal juga (opsional tapi disarankan)
        if len(image_files) > 7:
            return jsonify({
                "status": "failed",
                "message": "Maksimal 7 foto wajah"
            }), 400
        
        success_count = 0

        for image_file in image_files:

            image_path = f"temp_{user_id}_{success_count}.jpg"

            image_file.save(image_path)

            session = FaceAuthenticator(
                image_path,
                "yunet",
                "Facenet512"
            )

            session.register_face_db(user_id)

            success_count += 1

            if os.path.exists(image_path):
                os.remove(image_path)

        return jsonify({
            "status": "success",
            "message": f"{success_count} wajah berhasil diregistrasi",
            "user_id": user_id
        }), 200

    except Exception as e:

        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500

#DELETE FACE
@facerecog_bp.route('/users/<int:user_id>/face', methods=['DELETE'])
def delete_face(user_id):
    try:
        # 1. Hapus file fisik (folder)
        FaceAuthenticator.delete_faces_db(user_id)

        # 2. Hapus data di database (WAJIB agar count jadi 0)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM embeddings WHERE user_id=%s", (user_id,))
        cur.execute("UPDATE user_door SET face_recog=false WHERE id=%s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status": "success", "message": "Folder dan Database wajah dibersihkan"})
    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)}), 500