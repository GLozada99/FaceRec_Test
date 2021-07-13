import database as db
import numpy, os, io
import face_recognition
from PIL import Image

'''
Encode means taking a numpy array and turning it into bytes so that it can be stored on and retrieved from a database
'''

DIR = './KnownIMGs'

def byte_encode(path: str, large: bool=False) -> tuple[str, bytes, bytes]:
    '''
    Given path of image, takes the face, and encodes it into bytes. Returns name of image, raw picture in bytes, face enconding of numpy array in bytes
    '''
    mod = 'large' if large else 'small'
    name = path.split('/')[-1].split('_')[0]
    pic = face_recognition.load_image_file(path)
    face_encoding = face_recognition.face_encodings(pic,model=mod)[0].tobytes()
    with open(path, 'rb') as fil:
        raw_bin_pic = fil.read()
    return name, raw_bin_pic, face_encoding

def byte_decode(face_bytes: bytes) -> numpy.ndarray:
    '''
    Decodes bytes into numpy array that represents a face. Returns decoded numpy array
    '''
    face_encoding = numpy.frombuffer(face_bytes)

    return face_encoding

def populate_table_with_directory(DIR: str):
    '''
    Loops through entire directory of pictures, encondes and inserts them into table in database
    '''
    conn = db.connect()
    for root,_,files in os.walk(DIR,topdown=True):
        for name in files:
            pic_address = os.path.join(root, name)
            data = byte_encode(pic_address,True)
            db.insert_code(conn, *data)
    conn.close()

def populate_table_with_picture(pic_address: str=None, picture_data=None):
    '''
    Encodes and inserts one picture, encondes and inserts them into table in database
    '''
    conn = db.connect()
    if pic_address:
        data = byte_encode(pic_address,True)
    elif picture_data:
        data = picture_data
    try:
        db.insert_code(conn, *data)
    except Exception as e:
        print(e)
    conn.close()

def save_encoding(path: str, mode: bool=False):
    '''
    Encodes face o picture and inserts it into db, given its path
    '''
    conn = db.connect()
    data = byte_encode(path, mode)
    db.insert_code(conn, *data)
    conn.close()

def get_data():
    '''
    Gets data from db, turns picture and face data (in bytes) into the usable data objects
    '''
    data = []
    conn = db.connect()
    encoded_data = db.get_encondings(conn)
    for name, num, picture, enc_dat, in encoded_data:
        image = Image.open(io.BytesIO(picture))
        decoded_face = byte_decode(enc_dat)
        data.append((name, num, image, decoded_face))
    conn.close()
    return data

