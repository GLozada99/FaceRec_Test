import data_manipulation as dm
import sys, time, os
import face_recognition
from PIL import Image
from icecream import ic
from cv2 import cv2

from tensorflow.keras.applications.mobilenet_v2 import preprocess_input #pylint: disable=no-name-in-module
from tensorflow.keras.preprocessing.image import img_to_array #pylint: disable=no-name-in-module
from tensorflow.keras.models import load_model #pylint: disable=no-name-in-module
import numpy as np
import argparse

def show_pics(unknown, known):
    '''
    Shows unknown picture and the known picture that it resembles the most
    '''
    k_pic = Image.fromarray(known)
    u_pic = Image.fromarray(unknown)
    k_pic.show()
    u_pic.show()

def show_from_database():
    dat = dm.get_work_data() #returns name, picture in bytes and numpy array of faces 
    faces_data = list(zip(*dat))[1]
    print(len(faces_data))
    for i in range(15,len(faces_data)):
        face = faces_data[i]
        pic = Image.fromarray(face)
        print(i)
        pic.show()

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
    #dat is a list of (Name, Picture, Face array)
    dat = dm.get_work_data()
    known_faces_encoding = list(zip(*dat))[2]

    #comparing and finding out if there's a match
    results = face_recognition.compare_faces(known_faces_encoding, unknown_face_enconding,0.6)

    face_distances = face_recognition.face_distance(known_faces_encoding, unknown_face_enconding)
    best_match_index = np.argmin(face_distances)
    if results[best_match_index]:
        name = dat[best_match_index][0] 
        if name:
            print(f'{name} was recognized')

    #showing unknown image and its better match
    # best_known_picture = dat[best_match_index][1]
    # show_pics(picture_loaded, best_known_picture)

def detect_and_predict_mask(frame, faceNet, maskNet):
	# grab the dimensions of the frame and then construct a blob
	# from it
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300),(104.0, 177.0, 123.0))

	# pass the blob through the network and obtain the face detections
    faceNet.setInput(blob)
    detections = faceNet.forward()

    # initialize our list of faces, their corresponding locations,
    # and the list of predictions from our face mask network
    faces = []
    locs = []
    preds = []

    # loop over the detections
    for i in range(0, detections.shape[2]):
        # extract the confidence (i.e., probability) associated with
        # the detection
        confidence = detections[0, 0, i, 2]

        # filter out weak detections by ensuring the confidence is
        # greater than the minimum confidence
        if confidence > 0.5:
            # compute the (x, y)-coordinates of the bounding box for
            # the object
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # ensure the bounding boxes fall within the dimensions of
            # the frame
            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            # extract the face ROI, convert it from BGR to RGB channel
            # ordering, resize it to 224x224, and preprocess it
            face = frame[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = img_to_array(face)
            face = preprocess_input(face)

            # add the face and bounding boxes to their respective
            # lists
            faces.append(face)
            locs.append((startX, startY, endX, endY))

    # only make a predictions if at least one face was detected
    if len(faces) > 0:
        # for faster inference we'll make batch predictions on *all*
        # faces at the same time rather than one-by-one predictions
        # in the above `for` loop
        faces = np.array(faces, dtype="float32")
        preds = maskNet.predict(faces, batch_size=32)

    # return a 2-tuple of the face locations and their corresponding
    # locations
    return (locs, preds)

        

def face_recog_live(camera_address=0):
    '''
    Applies face recognition to live streaming from camera using rtsp
    If theres no camera the PC's camera will be used
    '''

    dat = dm.get_work_data() #returns name, picture in bytes and numpy array of faces 
    faces_data = list(zip(*dat))[2] #

    #getting VideoCapture object from device
    video_capture = cv2.VideoCapture(camera_address)
    time.sleep(2.0)
    
    last_time = time.time()
    last_time2 = time.time()
    #mask_flag = False
    #face_flag = False
    while True:
        #getting frame of video 
        _, frame = video_capture.read()

        if (time.time() - last_time2) > 2:
            _, preds = detect_and_predict_mask(frame, faceNet, maskNet)
            
            mask_detected = None
            pred = None
            if len(preds) > 0:
                pred = preds[0]
                mask, without_mask = pred
                mask_detected = True if mask > without_mask else False

                if mask_detected:
                    print('Mascarilla detectada. Por favor, remuevala momentaneamente')
            last_time2 = time.time()
                

        mask_detected = False
        #procesing image only every 5 seconds and only if there's no mask
        if (time.time() - last_time) > 5 and not mask_detected:
            #converting the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_frame = frame[:, :, ::-1]

            face_locations = face_recognition.face_locations(rgb_frame)
            unknown_face_encondings = face_recognition.face_encodings(rgb_frame, face_locations)
            if unknown_face_encondings:
                unknown_face_enconding = unknown_face_encondings[0]
                results = face_recognition.compare_faces(faces_data, unknown_face_enconding)
                face_distances = face_recognition.face_distance(faces_data, unknown_face_enconding)
                best_match_index = np.argmin(face_distances)
                if results[best_match_index]:
                    name = dat[best_match_index][0]
                    if name:
                        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        print(f'{name} was recognized at {now}')
                        # ic(rgb_frame,unknown_face_enconding)
                        dm.insert_picture_discovered(name, rgb_frame, unknown_face_enconding)
            last_time = time.time()

        cv2.imshow('Video', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    video_capture.release()
    cv2.destroyAllWindows()

faceNet = None
maskNet = None

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--face", type=str,
        default="face_detector",
        help="path to face detector model directory")
    ap.add_argument("-m", "--model", type=str,
        default="mask_detector.model",
        help="path to trained face mask detector model")
    ap.add_argument("-c", "--confidence", type=float, default=0.5,
        help="minimum probability to filter weak detections")
    args = vars(ap.parse_args())

    # load our serialized face detector model from disk
    print("[INFO] loading face detector model...")
    prototxtPath = os.path.sep.join([args["face"], "deploy.prototxt"])
    weightsPath = os.path.sep.join([args["face"],
        "res10_300x300_ssd_iter_140000.caffemodel"])
    faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

    # load the face mask detector model from disk
    print("[INFO] loading face mask detector model...")
    maskNet = load_model(args["model"])

    try:
        if len(sys.argv) == 3:
            if sys.argv[1] == '--add-directory':
                dm.insert_picture_directory(sys.argv[2])
            elif sys.argv[1] == '--add-file':
                dm.insert_picture_file(sys.argv[2])
            elif sys.argv[1] == '--face-recognition':
                face_recog_file(sys.argv[2])
            elif sys.argv[1] == '--show-pics-db':
                show_from_database()
        else:
            IP_camera_address = 'rtsp://gustavo:123456789Gu@10.0.0.121:554/Streaming/Channels/102'
            face_recog_live(IP_camera_address)
            #face_recog_live()

    except KeyboardInterrupt:
        print('\nbye')
    
    