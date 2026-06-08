from flask import Blueprint, request, jsonify
from modules.faceRecognition import FaceAuthenticator
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

        if len(image_files) != 3:
            return jsonify({
                "status": "failed",
                "message": "Harus mengirim 3 foto wajah"
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

    if not user_id:
        return jsonify({
            "status": "failed",
            "message": "user_id wajib diisi"
        }), 400

    try:

        FaceAuthenticator.delete_faces_db(user_id)

        return jsonify({
            "status": "success",
            "message": f"Face user {user_id} berhasil dihapus"
        })

    except Exception as e:

        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500 
    