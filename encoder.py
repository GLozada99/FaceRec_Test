import face_recognition
import sys, numpy, os
import database as db


'''
Encode means taking a numpy array and turning it into bytes so that it can be stored on and retrieved from a database
'''

DIR = './KnownIMGs'

def byte_encode(path: str, large: bool=False) -> tuple[str, bytes, bytes]:
    '''
    Given path of image, takes the face, and encodes it into bytes. Returns name of image, raw picture in bytes, face enconding of numpy array in bytes
    '''
    mod = 'large' if large else 'small'
    name = path.split('/')[-1]
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

def save_encoding(path: str, mode: bool=False):
    '''
    Encodes face o picture and inserts it into db, given its path
    '''
    conn = db.connect()
    data = byte_encode(path, mode)
    db.insert_code(conn, *data)
    conn.close()

