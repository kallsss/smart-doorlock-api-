import psycopg
from pathlib import Path
import config.creds as creds

QUERY_USERID = "SELECT id FROM user_door WHERE id = %s"
QUERY_USERNAME = "SELECT name FROM user_door WHERE id = %s"
QUERY_UPDATE_FACEAUTH_STATUS = "UPDATE user_door SET face_recog = %s WHERE id = %s;"
QUERY_FACEAUTH_STATUS = "SELECT face_recog FROM user_door WHERE id = %s"
QUERY_DELETE_FACES = "DELETE from embeddings WHERE user_id = %s"

conn = psycopg.connect(
    host = creds.db_host,
    port = creds.db_port,
    dbname = creds.db_name,
    user = creds.db_username,
    password = creds.db_password
)

cur = conn.cursor()

def check_user_id(user_id : int):
    try:
        cur.execute(QUERY_USERID,(user_id,))
        result = cur.fetchone()

        if result:
            return True

        return False

    except Exception as e:
        print("Error:", e)
        return False

def update_faceAuth_status(user_id : int, status : bool):
    try:
        cur.execute(QUERY_FACEAUTH_STATUS, (user_id,))
        result = cur.fetchone()
        print(result)

        if result is not None and result[0] == status:
            print("Status Sudah Sama, tidak perlu update.")
            return True
        
        cur.execute(QUERY_UPDATE_FACEAUTH_STATUS, (status, user_id))
        conn.commit()
        print("Status berhasil diupdate!")
        return True
    except Exception as e:
        print("Error:", e)
        conn.rollback()
        return False

def delete_fromEmbeddings(user_id : int):
    try:
        cur.execute(QUERY_DELETE_FACES, (user_id,))
        conn.commit()
        return True
        
    except Exception as e:
        print("Error:", e)
        conn.rollback()
        return False

def get_name(user_id : int):
    try:
        cur.execute(QUERY_USERNAME, (user_id,))
        result = cur.fetchone()

        if result:
            return result[0]

        return None

    except Exception as e:
        print("Error:", e)
        return None


if __name__ == "__main__":
    userid = int(input("id: "))
    print(update_faceAuth_status(userid, False))
    