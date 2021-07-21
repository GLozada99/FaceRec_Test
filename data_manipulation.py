import io,os,sys
from icecream import ic
import numpy as np
import face_recognition as fr
import crud
from PIL import Image
from numpy_serializer import to_bytes, from_bytes
import classes  


def process_picture(path: str, large: bool=False) -> tuple[str, bytes, bytes]:
    '''
    Given path of image, takes the face, and encodes it into bytes for storing. Returns name of image, raw picture in bytes, face enconding of numpy array in bytes
    '''
    data = None
    mod = 'large' if large else 'small'
    person_id = path.split('/')[-1].split('.')[0].split('_')[0]
    pic = fr.load_image_file(path)
    face_encodings = fr.face_encodings(pic,model=mod)
    if face_encodings:
        face_encoding = to_bytes(face_encodings[0])
        raw_bin_pic = to_bytes(np.asarray(pic)) 
        data = (person_id, raw_bin_pic, face_encoding)
    
    return data  

def _byte_decode(face_bytes: bytes) -> np.ndarray:
    '''
    Decodes bytes into numpy array that represents a face. Returns decoded numpy array
    '''
    face_encoding = from_bytes(face_bytes)
    return face_encoding

def _unprocess_picture(person_id, raw_bin_pic, face_encoding):
    '''
    Takes processed picture data and returns name, picture in bytes and numpy array of faces 
    '''
    picture = _byte_decode(raw_bin_pic)
    face = _byte_decode(face_encoding)
    return person_id, picture, face

def insert_picture_directory(path: str):
    '''
    Loops through directory of pictures and inserts them into the database
    '''
    for root,_,files in os.walk(path,topdown=True):
        for name in files:
            pic_address = os.path.join(root, name)
            person_id, picture_bytes, face_bytes = process_picture(pic_address,True)
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
    person_id, picture_bytes, face_bytes = process_picture(pic_address,True)
    newPicture = classes.Picture(person_id=person_id,picture_bytes=picture_bytes,face_bytes=face_bytes)
    if crud.get_entry(classes.Person, person_id):
        crud.add_entry(newPicture)
    else:
        print(f'No hay una persona registrada con el id {person_id}')
        sys.exit(1)

def insert_picture_discovered(name, picture_frame, face_encoding):
    '''
    Inserts single picture into database. Used for frames taken live.
    Bothe the picture_frame and the face_encoding must be arrays
    '''
    picture_bytes = to_bytes(picture_frame)
    face_bytes = to_bytes(face_encoding)
    newPicture = Picture(name=name,picture_bytes=picture_bytes,face_bytes=face_bytes)
    crud.add_entry(newPicture)

def get_work_data():
    '''
    Returns list of pictures in the format (name, picture, face_encoding)
    '''
    pic_list = []
    for pic in crud.get_entries(Picture):
        name = pic.name
        byte_picture = pic.picture_bytes
        face_encoding = pic.face_bytes
        pic_list.append(_unprocess_picture(name,byte_picture,face_encoding))
    return pic_list


