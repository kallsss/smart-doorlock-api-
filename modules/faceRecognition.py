import sys
import os
import shutil
from pathlib import Path
import config.creds as creds
import cv2
import modules.postgres as postgres

lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib'))

# Memasukkan folder 'lib' ke dalam sistem pencarian modul Python
sys.path.append(lib_path)

# Sekarang kamu bisa mengimpornya dengan normal tanpa titik-titik (..)
from deepface import DeepFace

models = [
    "VGG-Face", "Facenet", "Facenet512", "OpenFace", "DeepFace",
    "DeepID", "ArcFace", "Dlib", "SFace", "GhostFaceNet",
    "Buffalo_L",
]

backends = [
    'opencv', 'ssd', 'dlib', 'mtcnn', 'fastmtcnn',
    'retinaface', 'mediapipe', 'yolov8n', 'yolov8m', 
    'yolov8l', 'yolov11n', 'yolov11s', 'yolov11m',
    'yolov11l', 'yolov12n', 'yolov12s', 'yolov12m',
    'yolov12l', 'yunet', 'centerface',
]

class FaceAuthenticator:
    def __init__(self, target_img:str, detector_model:str, recognition_model:str):
        self.target_img = target_img
        self.detector_model = detector_model
        self.recognition_model = recognition_model
        self.load_img = cv2.imread(target_img)

    def extract_face_region(self, face_list: list, chosen_face: int):
        img = cv2.imread(self.target_img)
        target_crop = face_list[chosen_face]
        h, w = img.shape[:2]

        # Ekstraksi koordinat bounding box dari deteksi YuNet
        x1, y1 = target_crop["x"], target_crop["y"]
        x2, y2 = target_crop["x2"], target_crop["y2"]
        face_w = x2 - x1
        face_h = y2 - y1

        # Mencari titik tengah (center) dari wajah
        center_x = x1 + face_w // 2
        center_y = y1 + face_h // 2

        # Mencari sisi paling panjang untuk memastikan crop berbentuk persegi
        max_side = max(face_w, face_h)
        
        # Menambahkan padding dinamis (misal 5% dari ukuran sisi terpanjang)
        padding = int(max_side * 0.05)
        crop_size = max_side + (padding * 2)

        # Menghitung koordinat baru untuk pemotongan (memastikan bentuknya persegi)
        half_size = crop_size // 2
        new_x1 = max(0, center_x - half_size)
        new_y1 = max(0, center_y - half_size)
        new_x2 = min(w, center_x + half_size)
        new_y2 = min(h, center_y + half_size)

        # Memotong gambar
        crop_img = img[new_y1:new_y2, new_x1:new_x2]

        # Mengubah resolusi gambar yang sudah di crop
        target_size = (160, 160)
        resize_image = cv2.resize(crop_img, target_size, interpolation=cv2.INTER_AREA)
        
        return resize_image

    def store_face_record(self, img, username):
        dirFace = f"{creds.DF_DBDir}/{username}"
        if not os.path.exists(dirFace):
                os.makedirs(dirFace)
        
        # Mulai pencarian urutan file yang kosong
        i = 0
        while True:
            i += 1
            file_name = f"{username}_Crop_{i}.jpeg"
            path_save = os.path.join(dirFace, file_name)
            
            if not os.path.exists(path_save):
                break

        cv2.imwrite(path_save, img)
        print("Saved at: ", path_save)
        return path_save

    def detect_faces(self):
        try:
            find_faces = DeepFace.extract_faces(img_path=self.target_img, detector_backend=self.detector_model, anti_spoofing=True)
        except Exception as err:
            print(err)
            return []
        
        face_detected = []
        print(find_faces)
        i = 0
        for face_now in find_faces:
            spoof = face_now['is_real']
            x = face_now['facial_area']['x']
            y = face_now['facial_area']['y']
            w = face_now['facial_area']['w']
            h = face_now['facial_area']['h']
            facial_area = {"x" : x, "y" : y, "x2" : x + w, "y2" : y + h, "spoof": spoof}
            face_detected.append(facial_area)

            color = (0,0,0)
            if spoof:
                color = (0,255,0)
            else:
                color = (0,0,255)
            cv2.putText(self.load_img, str(i), (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.rectangle(self.load_img, (x, y), (x + w, y + h), color, 2)

        # Kalau yang terdeteksi mukanya lebih dari satu buat window preview untuk milih
        if len(face_detected) > 1:
            cv2.namedWindow("Image Preview", cv2.WINDOW_KEEPRATIO)
            cv2.imshow("Image Preview", self.load_img)
            cv2.waitKey(0)

        return face_detected
    
    def enroll_face2dir(self, user_id : int = 0): # Function yang berfungsi untuk menaruh gambar di directory folder secara terstruktut
        # Mengecek apakah wajah terdeteksi lebih dari satu
        face_detector = self.detect_faces()
        if not face_detector:
            print("Error: Tidak ada wajah terdeteksi!")
            return None
        elif len(face_detector) > 1:
            selected_face = int(input(f"Terdeteksi {len(face_detector)} wajah. Pilih index yang mau di-crop ({len(face_detector)-1}): "))
        else:
            selected_face = 0
            
        crop_img = self.extract_face_region(face_detector, selected_face)

        # Mengecek apakah wajah sudah terdaftar
        ver_dfs = []
        try:
            ver_dfs = DeepFace.search(img=crop_img, detector_backend=self.detector_model, model_name=self.recognition_model, connection=postgres.conn)
            print(ver_dfs)
        except:
            print("database still empty")
            
        # Cek apakah wajah yang terdeteksi punya user lain atau tidak
        owner_face = None
        if len(ver_dfs) > 0 and not ver_dfs[0].empty:
            result_face = ver_dfs[0].iloc[0]
            if result_face['distance'] < 0.4:
                owner_face = result_face['user_id']
            
            if user_id != owner_face:
                print(f"Error: Nama muka tidak cocok! (Target: {user_id}, Terdeteksi: {owner_face})")
                return None

        put_path = self.store_face_record(crop_img, user_id)
        return put_path

    def face_verify(self):
        # Mencari gambar yang paling mirip/terdekat
        dfs = DeepFace.find(img_path=self.target_img, db_path=creds.DF_DBDir, detector_backend=self.detector_model, 
                            model_name=self.recognition_model)
        print(dfs)
        results = []

        for df in dfs:
            if df.empty:
                continue
            
            best_match = df.iloc[0]
            x = int(best_match['source_x'])
            y = int(best_match['source_y'])
            w = int(best_match['source_w'])
            h = int(best_match['source_h'])
            
            path_identity = best_match['identity']
            parent_folder = os.path.basename(os.path.dirname(path_identity))

            # Check apakah threshold wajah sudah memenuhi syarat
            if best_match['distance'] > 0.4:
                cv2.rectangle(self.load_img, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cv2.putText(self.load_img, f"{best_match['distance']}", (x, y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(self.load_img, f"{parent_folder}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                continue

            # Gambar kotak (frame) hijau untuk wajah yang dikenali
            cv2.rectangle(self.load_img, (x, y), (x + w, y + h), (0, 255, 0), 3)
            # Tulis nama orang di atas kotak
            cv2.putText(self.load_img, parent_folder, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            results.append({"name": parent_folder, "distance": best_match['distance']})

        cv2.namedWindow("Result Veritification", cv2.WINDOW_KEEPRATIO)
        cv2.imshow("Result Veritification", self.load_img)
        cv2.waitKey(0)
        return results
    
    def register_face_db(self, user_id : int):
        # Mengecek apakah id terdaftar dalam DB
        if not postgres.check_user_id(user_id):
            print("User id tidak ditemukan")
            return None
    
        preped_img_path = self.enroll_face2dir(user_id)
        if not preped_img_path:
            print("regist failed")
            return None

        DeepFace.register(img=preped_img_path, user_id=user_id, model_name=self.recognition_model,
                        detector_backend=self.detector_model, connection=postgres.conn)
        postgres.update_faceAuth_status(user_id, True)
        print("Successfully registered!")
    
    def delete_faces_db(user_id : int):
        # Mengecek apakah id terdaftar dalam DB
        if not postgres.check_user_id(user_id):
            print("User id tidak ditemukan")
            return None
        
        query = postgres.delete_fromEmbeddings(user_id)
        if not query:
            print("Error")
            return None
        
        postgres.update_faceAuth_status(user_id, False)
        try:
            # Cek apakah foldernya benar-benar ada sebelum dihapus
            dir_path = Path(f"{creds.DF_DBDir}/{user_id}")
            if dir_path.exists and dir_path.is_dir():
                shutil.rmtree(dir_path)
                print(f"Folder foto untuk user {user_id} berhasil dihapus beserta isinya!")
            else:
                print(f"Folder foto untuk user {user_id} tidak ditemukan secara fisik, dilewati.")
            return
        except Exception as e:
            print(f"Gagal menghapus folder foto: {e}")
            
        print("Berhasil dihapus!")
        return True
        
    def search_face_db(self):
        try:
            query = DeepFace.search(img=self.target_img , model_name=self.recognition_model, 
                                    detector_backend=self.detector_model, connection=postgres.conn)
            df_result = query[0]
            if df_result.empty:
                print("Wajah tidak dikenali!")
                return {"user_id": None}
            
            highest_score = df_result.iloc[0]
            name = postgres.get_name(highest_score["user_id"])
            result = {"user_id": str(highest_score["user_id"]), "name": name, "distance": highest_score["distance"]}
            return result
        except Exception as e: 
            print("Error:", e)
            return {"user_id": None}

def load_models(face_detector:str, face_recognition:str):
    DeepFace.build_model(face_detector, "face_detector")
    DeepFace.build_model(face_recognition, "facial_recognition")
        
    print("Models load successfully!")