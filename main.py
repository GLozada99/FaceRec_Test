import data_manipulation as dm
import sys, numpy, time
import face_recognition
from PIL import Image
from icecream import ic
from cv2 import cv2

def show_pics(unknown, known):
    '''
    Shows unknown picture and the known picture that it resembles the most
    '''
    pic = Image.fromarray(unknown)
    pic.show()
    known.show()

def face_recog_file(picture_path):
    '''
    Applies face recognition to a picture given its path, using a database of previously known pictures
    '''
    #loading picture from file
    picture_loaded = face_recognition.load_image_file(picture_path)

    #getting face locations of picture so that face encoding can be faster
    face_locations = face_recognition.face_locations(picture_loaded)
    unknown_face_encondings = face_recognition.face_encodings(picture_loaded,face_locations)
    
    if unknown_face_encondings:
        #analizing only principal face in picture
        unknown_face_enconding = unknown_face_encondings[0]
    else:
        #exiting program if there are no faces on picture 
        print('No se ha detectado una cara')
        sys.exit(1)

    #getting data of known pictures through database
    #dat is a list of (Person_Name, Number, Picture, Face Encoding)
    dat = dm.get_work_data()
    known_faces_encoding = list(zip(*dat))[3]

    #comparing and finding out if there's a match
    results = face_recognition.compare_faces(known_faces_encoding, unknown_face_enconding,0.6)

    face_distances = face_recognition.face_distance(known_faces_encoding, unknown_face_enconding)
    best_match_index = numpy.argmin(face_distances)
    if results[best_match_index]:
        name = dat[best_match_index][0] 
        if name:
            print(f'{name} was recognized')

    #showing unknown image and its better match
    # best_known_picture = dat[best_match_index][2]
    # show_pics(picture_loaded, best_known_picture)

def face_recog_live(camera_address=0):
    '''
    Applies face recognition to live streaming from camera using rtsp
    If theres no camera the PC's camera will be used
    '''
    dat = dm.get_work_data() #returns name, picture in bytes and numpy array of faces 
    faces_data = list(zip(*dat))[2] #

    #getting VideoCapture object from device
    video_capture = cv2.VideoCapture(camera_address)
    
    last_time = time.time()
    while True:
        #getting and resizing frame of video to 1/4 size for faster face recognition processing
        _, frame = video_capture.read()
        resized_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        #converting the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_frame = resized_frame[:, :, ::-1]

        #procesing image only every 5 seconds   
        if (time.time() - last_time) > 5:
            face_locations = face_recognition.face_locations(rgb_frame)
            unknown_face_encondings = face_recognition.face_encodings(rgb_frame, face_locations)
            if unknown_face_encondings:
                unknown_face_enconding = unknown_face_encondings[0]
                results = face_recognition.compare_faces(faces_data, unknown_face_enconding)
                face_distances = face_recognition.face_distance(faces_data, unknown_face_enconding)
                best_match_index = numpy.argmin(face_distances)
                if results[best_match_index]:
                    name = dat[best_match_index][0]
                    if name:
                        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        print(f'{name} was recognized at {now}')
                        #enc.populate_table_with_picture(picture_data=(name, frame.tobytes(), unknown_face_enconding))
            last_time = time.time()


        cv2.imshow('Video', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    video_capture.release()
    cv2.destroyAllWindows()

    
if __name__ == "__main__":
    try:
        if len(sys.argv) == 3:
            if sys.argv[1] == '--add-directory':
                dm.insert_picture_directory(sys.argv[2])
            elif sys.argv[1] == '--add-file':
                dm.insert_picture_file(sys.argv[2])
            elif sys.argv[1] == '--face-recognition':
                face_recog_file(sys.argv[2])
        else:
            IP_camera_address = 'rtsp://gustavo:123456789Gu@10.0.0.121:554/Streaming/Channels/102'
            face_recog_live(IP_camera_address)
    except KeyboardInterrupt:
        print('\nbye')
    
    