from flask import Blueprint, request, jsonify
from modules.faceRecognition import FaceAuthenticator

facerecog_bp = Blueprint("facerecog_bp", __name__)

@facerecog_bp.route('/RegisterFace', methods=['POST'])
def register_face():

    user_id = int(request.form.get("user_id"))

    image_files = request.files.getlist("image")

    if len(image_files) == 0:

        return jsonify({
            "status": "failed",
            "message": "Tidak ada file wajah"
        }), 400

    success_count = 0

    try:

        for image_file in image_files:

            image_path = f"temp_{image_file.filename}"

            image_file.save(image_path)

            session = FaceAuthenticator(
                image_path,
                "yunet",
                "Facenet512"
            )

            session.register_face_db(user_id)

            success_count += 1

        return jsonify({
            "status": "success",
            "message": f"{success_count} wajah berhasil diregistrasi",
            "user_id": user_id
        })

    except Exception as e:

        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500

#DELETE FACE
@facerecog_bp.route('/DeleteFace', methods=['DELETE'])
def delete_face():

    user_id = request.json.get("user_id")

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
    