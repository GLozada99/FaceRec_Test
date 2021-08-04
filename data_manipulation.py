import io,os,sys
from icecream import ic
import numpy as np
import face_recognition as fr
import crud
from PIL import Image
from numpy_serializer import to_bytes, from_bytes
from cv2 import cv2
import base64
import classes  


def process_picture_path(path: str, large: bool=False) -> tuple[str, bytes, bytes]:
    '''
    Given path of image, takes the face, and encodes it into bytes for storing. Returns raw picture in bytes, face enconding of numpy array in bytes
    '''
    data = None
    mod = 'large' if large else 'small'
    try:
        person_id = int(path.split('/')[-1].split('.')[0].split('_')[0])
    except:
        return None
    pic = fr.load_image_file(path)
    face_encodings = fr.face_encodings(pic,model=mod)
    if face_encodings:
        face_encoding = to_bytes(face_encodings[0])
        raw_bin_pic = to_bytes(pic) 
        data = (person_id, raw_bin_pic, face_encoding)
    return data

def process_picture_file(img_data, large: bool=False):
    '''
    Given image, takes the face, and encodes it into bytes for storing. Returns raw picture in bytes, face enconding of numpy array in bytes
    '''
    data = None
    mod = 'large' if large else 'small'
    image = Image.open(img_data)
    pic = np.array(image)
    face_encodings = fr.face_encodings(pic,model=mod)
    if face_encodings:
        face_encoding = to_bytes(face_encodings[0])
        raw_bin_pic = to_bytes(pic) 
        data = (raw_bin_pic, face_encoding)
    return data

def _byte_decode(face_bytes: bytes) -> np.ndarray:
    '''
    Decodes bytes into numpy array that represents a face. Returns decoded numpy array
    '''
    face_encoding = from_bytes(face_bytes)
    return face_encoding

def _unprocess_picture(coded_data):
    '''
    Decodes data, works for pictures and face encodings
    '''
    decoded_data = _byte_decode(coded_data)
    return decoded_data

def insert_picture_directory(path: str):
    '''
    Loops through directory of pictures and inserts them into the database
    '''
    for root,_,files in os.walk(path,topdown=True):
        for name in files:
            pic_address = os.path.join(root, name)
            data = process_picture_path(pic_address,True)
            if data:
                person_id, picture_bytes, face_bytes  = data
            else:
                continue
            newPicture = classes.Picture(person_id=person_id,picture_bytes=picture_bytes,face_bytes=face_bytes)
            if crud.get_entry(classes.Person, person_id):
                crud.add_entry(newPicture)
            else:
                print(f'No hay una persona registrada con el id {person_id}')
    
def insert_picture_file(path: str):
    '''
    Inserts single picture into database, given it's path
    '''
    pic_address = path
    person_id, picture_bytes, face_bytes = process_picture_path(pic_address,True)
    newPicture = classes.Picture(person_id=person_id,picture_bytes=picture_bytes,face_bytes=face_bytes)
    if crud.get_entry(classes.Person, person_id):
        crud.add_entry(newPicture)
    else:
        print(f'No hay una persona registrada con el id {person_id}')
        sys.exit(1)

def insert_picture_discovered(person_id, picture_frame, face_encoding):
    '''
    Inserts single picture into database. Used for frames taken live.
    Both the the picture_frame and the face_encoding must be arrays
    '''
    picture_bytes = to_bytes(picture_frame)
    face_bytes = to_bytes(face_encoding)
    newPicture = classes.Picture(person_id=person_id,picture_bytes=picture_bytes,face_bytes=face_bytes)
    crud.add_entry(newPicture)

def get_pictures_encodings():
    '''
    Returns list of tuples in the format (person_id, face_encoding)
    '''
    pic_list = []
    for pic in crud.get_entries(classes.Picture):
        person_id = pic.person_id
        face_encodings = _unprocess_picture(pic.face_bytes)
        pic_list.append((person_id,face_encodings))
    return pic_list

def get_pictures():
    '''
    Returns list of tuples in the format (person_id, picture_array)
    '''
    pic_list = []
    for pic in crud.get_entries(classes.Picture):
        person_id = pic.person_id
        picture = _unprocess_picture(pic.picture_bytes)
        pic_list.append((person_id,picture))
    return pic_list


