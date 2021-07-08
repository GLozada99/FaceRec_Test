import database as db, encoder as enc
import os, sys, io
import face_recognition
from PIL import Image
import numpy
import time
from icecream import ic
from cv2 import cv2

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

def show_pics(unknown, known):
    pic = Image.fromarray(unknown)
    pic.show()
    for _,_,img,_ in known:
        img.show()

def main():
    #getting encoding of unknown picture
    #ic.disable()
    picture_address = sys.argv[1]
    picture = face_recognition.load_image_file(picture_address)

    face_locations = face_recognition.face_locations(picture)
    picture_enconding = face_recognition.face_encodings(picture,face_locations)[0]
    
    #getting encoding and name of known pictures through database
    # dat is (Person_Name, Number, Bytes, Encoding)
    dat = get_data()
    faces_data = list(zip(*dat))[3]

    #comparing and finding out if there's a match
    results = face_recognition.compare_faces(faces_data, picture_enconding,0.6)
    recognized = [dat[i] for i,result in enumerate(results) if result]

    #showing unknown image whith its matches
    #show_pics(picture, recognized)    
        
    recognized = set([name for name,_,_,_ in recognized])
    for name in recognized:
        break
        # answer = input(f'{name} was recognized. Do you wish to save that picture? [Y/n]')
        
        # print(answer.upper())

def main2():
    enc.populate_table_with_directory('./KnownIMGs')

def main3():
    dat = get_data()
    faces_data = list(zip(*dat))[3]

    process_this_frame = True

    #IP Camera
    video_capture = cv2.VideoCapture('rtsp://gustavo:123456789Gu@10.0.0.121:554/Streaming/Channels/102')
    
    #Laptop Camera
    #video_capture = cv2.VideoCapture(0)
    last_time = time.time()
    while True:
        _, frame = video_capture.read()
        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]

        if process_this_frame and (time.time() - last_time) > 5:
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encoding = face_recognition.face_encodings(rgb_small_frame, face_locations)

            if face_encoding:
                face_encoding = face_encoding[0]
                results = face_recognition.compare_faces(faces_data, face_encoding)
                face_distances = face_recognition.face_distance(faces_data, face_encoding)
                best_match_index = numpy.argmin(face_distances)
                if results[best_match_index]:
                    name = dat[best_match_index][0]
                    if name:
                        print(f'{name} was recognized')
                        last_time = time.time()
        
        process_this_frame = not process_this_frame

        cv2.imshow('Video', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    video_capture.release()
    cv2.destroyAllWindows()

                
        




    
if __name__ == "__main__":
    try:
        main3()
    except KeyboardInterrupt:
        print('\nbye')
    
    