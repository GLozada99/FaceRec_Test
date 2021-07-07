import database as db, encoder as enc
import os, sys, io
import face_recognition
from PIL import Image
import numpy
import time
from icecream import ic

def get_data():
    '''
    Gets data from db, turns picture and face data (in bytes) into the usable data objects
    '''
    data = []
    conn = db.connect()
    encoded_data = db.get_encondings(conn)
    for name, num, picture, enc_dat, in encoded_data:
        image = Image.open(io.BytesIO(picture))
        decoded_face = enc.byte_decode(enc_dat)
        data.append((name, num, image, decoded_face))
    conn.close()
    return data

def main():
    #getting encoding of unknown picture
    #ic.disable()
    picture_address = sys.argv[1]
    picture = face_recognition.load_image_file(picture_address)

    picture_enconding = face_recognition.face_encodings(picture)[0]
    
    #getting encoding and name of known pictures through database
    # dat is (Person_Name, Number, Bytes, Encoding)
    dat = get_data()
    faces_data = list(zip(*dat))[3]

    #comparing and finding out if there's a match
    results = face_recognition.compare_faces(faces_data, picture_enconding,0.6)
    recognized = [dat[i] for i,result in enumerate(results) if result]

    #showing unknown image whith its matches
    pic = Image.fromarray(picture)
    pic.show()
    for _,_,img,_ in recognized:
        ic(img)
        img.show()
        
    recognized = set([name for name,_,_,_ in recognized])
    for name in recognized:
        answer = input(f'{name} was recognized. Do you wish to save that picture? [Y/n]')
        
        print(answer.upper())

def main2():
    enc.populate_table_with_directory('./KnownIMGs')

def main3():
    with open(sys.argv[1], 'rb') as fil:
        raw_bin_pic = fil.read()
    Image.open(io.BytesIO(raw_bin_pic)).show()

    
if __name__ == "__main__":
    main()
    
    
    