import database as db, encoder as enc
import os, sys
import face_recognition
from PIL import Image
import numpy
import time

def get_data():
    data = []
    conn = db.connect()
    encoded_data = db.get_encondings(conn)
    for enc_dat in encoded_data:
        data.append(enc.byte_decode(enc_dat))
    conn.close()
    return data

def get_img(face_image: numpy.ndarray):
    print(face_image)
    face_image = face_recognition.load_image_file(sys.argv[1])
    print(face_image)
    image = Image.fromarray(face_image)
    return image

def main():
    #getting encoding of unknown picture
    picture_address = sys.argv[1]
    picture = face_recognition.load_image_file(picture_address)
    picture_enconding = face_recognition.face_encodings(picture)[0]
    
    #getting encoding and name of known pictures through database
    # dat is (Person_Name, Number, Bytes, Encoding)
    dat = get_data()
    faces_data = list(zip(*dat))[3]

    #comparing and finding out if there's a match
    results = face_recognition.compare_faces(faces_data, picture_enconding,0.5)
    recognized = [dat[i] for i,result in enumerate(results) if result]

    #showing unknown image whith its matches
    get_img(picture_enconding).show()
    for _,face in recognized:
        get_img(face).show()
        
    recognized = set([name.split('_')[0] for name,_ in recognized])
    for name in recognized:
        answer = input(f'{name} was recognized. Do you wish to save that picture? [Y/n]')
        
        print(answer.upper())

def main2():
    enc.populate_table_with_directory('./KnownIMGs')


    
if __name__ == "__main__":
    main()
    
    
    