import face_recognition as fr
import numpy as np
import io
from PIL import Image

def process_picture(path: str, large: bool=False) -> tuple[str, bytes, bytes]:
    '''
    Given path of image, takes the face, and encodes it into bytes for storing. Returns name of image, raw picture in bytes, face enconding of numpy array in bytes
    '''
    mod = 'large' if large else 'small'
    name = path.split('/')[-1].split('.')[0].split('_')
    pic = fr.load_image_file(path)
    face_encodings = fr.face_encodings(pic,model=mod).tobytes()
    if face_encodings:
        face_encoding = face_encodings
        with open(path, 'rb') as fil:
            raw_bin_pic = fil.read()
        return name, raw_bin_pic, face_encoding
    else:
        print('A face was not found on {path}')

def _byte_decode(face_bytes: bytes) -> np.ndarray:
    '''
    Decodes bytes into numpy array that represents a face. Returns decoded numpy array
    '''
    face_encoding = np.frombuffer(face_bytes)
    return face_encoding

def unprocess_picture(name, raw_bin_pic, face_encoding):
    picture = Image.open(io.BytesIO(raw_bin_pic))
    face = _byte_decode(face_encoding)
    return name, picture, face



