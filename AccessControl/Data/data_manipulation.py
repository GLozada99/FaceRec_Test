import os
import sys
import face_recognition as fr
import numpy as np
import AccessControl.Data.crud as crud
import AccessControl.Data.enums as enums
import AccessControl.Data.classes as classes

from PIL import Image
from numpy_serializer import to_bytes, from_bytes
import base64
import io
from datetime import datetime
import hashlib


def process_picture_path(path: str, large: bool = False):
    '''
    Given path of image, takes the face, and encodes it into bytes for storing.
    Returns raw picture in bytes, face enconding of numpy array in bytes
    '''
    data = None
    mod = 'large' if large else 'small'
    try:
        person_id = int(path.split('/')[-1].split('.')[0].split('_')[0])
    except Exception as error:
        print(error)
        return None
    pic = fr.load_image_file(path)
    face_encodings = fr.face_encodings(pic, model=mod)
    if face_encodings:
        face_encoding = to_bytes(face_encodings[0])
        raw_bin_pic = to_bytes(pic)
        data = (person_id, raw_bin_pic, face_encoding)
    return data


def process_picture_file(img_data, large: bool = False):
    '''
    Given image, takes the face, and encodes it into bytes for storing.
    Returns raw picture in bytes, face enconding of numpy array in bytes
    '''
    data = None
    mod = 'large' if large else 'small'
    image = Image.open(img_data)
    pic = np.array(image)
    face_encodings = fr.face_encodings(pic, model=mod)
    if face_encodings:
        face_encoding = to_bytes(face_encodings[0])
        raw_bin_pic = to_bytes(pic)
        data = (raw_bin_pic, face_encoding)
    return data


def unprocess_picture(coded_data):
    '''
    Decodes data, works for pictures and face encodings
    '''
    return from_bytes(coded_data)


def image_to_byte_array(image):
    imgByteArr = io.BytesIO()
    image.save(imgByteArr, format="png")
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr


def img_bytes_to_base64(img_bytes):
    img_array = unprocess_picture(img_bytes)
    img = Image.fromarray(img_array)
    img_in_mem = io.BytesIO()
    img.save(img_in_mem, format="png")
    img_in_mem.seek(0)
    bytes_img = img_in_mem.read()
    return base64.b64encode(bytes_img).decode('ascii')


def insert_picture_directory(path: str):
    '''
    Loops through directory of pictures and inserts them into the database
    '''
    for root, _, files in os.walk(path, topdown=True):
        for name in files:
            pic_address = os.path.join(root, name)
            data = process_picture_path(pic_address, True)
            if data:
                person_id, picture_bytes, face_bytes = data
            else:
                continue
            newPicture = classes.Picture(
                person_id=person_id, picture_bytes=picture_bytes,
                face_bytes=face_bytes)
            if crud.get_entry(classes.Person, person_id):
                crud.add_entry(newPicture)
            else:
                print(f'No hay una persona registrada con el id {person_id}')


def insert_picture_file(path: str):
    '''
    Inserts single picture into database, given it's path
    '''
    pic_address = path
    data = process_picture_path(pic_address, True)
    if not data:
        return

    person_id, picture_bytes, face_bytes = data
    newPicture = classes.Picture(
        person_id=person_id, picture_bytes=picture_bytes,
        face_bytes=face_bytes)
    if crud.get_entry(classes.Person, person_id):
        crud.add_entry(newPicture)
    else:
        print(f'No hay una persona registrada con el id {person_id}')
        sys.exit(1)


def insert_picture_discovered(person_id, picture_frame, face_encoding, action):
    '''
    Inserts single picture into database. Used for frames taken live.
    Both the the picture_frame and the face_encoding must be arrays
    '''
    picture_bytes = to_bytes(picture_frame)
    face_bytes = to_bytes(face_encoding)
    person = crud.get_entry(classes.Person, person_id)

    newPicture = classes.Picture(picture_bytes=picture_bytes,
                                 face_bytes=face_bytes, person=person)
    newTimeEntry = classes.Time_Entry(
        action=action, action_time=datetime.now(), picture=newPicture, person=person)

    crud.add_entry(newPicture)
    crud.add_entry(newTimeEntry)


def get_pictures_encodings():
    '''
    Returns list of tuples in the format (person_id, face_encoding, pic_id)
    '''
    pic_list = []
    for pic in crud.get_entries(classes.Picture):
        person_id = pic.person_id
        pic_id = pic.id
        face_encodings = unprocess_picture(pic.face_bytes)
        pic_list.append((person_id, face_encodings, pic_id))

    return pic_list


def get_pictures_encodings_by_type(profile):
    '''
    Returns list of tuples in the format (person_id, face_encoding, pic_id)
    '''
    pics = None
    if profile == enums.PictureClassification.ALL_ACTIVE:
        pics = crud.get_all_pictures()
    elif profile == enums.PictureClassification.EMPLOYEES_ACTIVE:
        pics = crud.get_employees_pictures()
    elif profile == enums.PictureClassification.ACCEPTED_APPOINTMENTS:
        pics = crud.get_accepted_appointments_pictures()

    pic_list = []
    for pic in pics:
        person_id = pic.person_id
        pic_id = pic.id
        face_encodings = unprocess_picture(pic.face_bytes)
        pic_list.append((person_id, face_encodings, pic_id))

    return pic_list


def get_pictures():
    pics = []
    for pic in crud.get_entries(classes.Picture):
        pic_encodings = unprocess_picture(pic.picture_bytes)
        pics.append(pic_encodings)

    return pics


def compute_hash(raw_string: str):
    return hashlib.sha256(raw_string.encode()).hexdigest()


def compare_hash(raw_string: str, hash_string: str):
    return compute_hash(raw_string) == hash_string


def has_available_appointment(person_id):
    return crud.appointments_by_person_time(
        crud.get_entry(classes.Person, person_id))
