import data_manipulation as dm
import numpy as np
import sys, time, os, argparse
import face_recognition
import crud, classes
from PIL import Image
from icecream import ic
from cv2 import cv2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input #pylint: disable=no-name-in-module
from tensorflow.keras.preprocessing.image import img_to_array #pylint: disable=no-name-in-module
from tensorflow.keras.models import load_model #pylint: disable=no-name-in-module

def show_pics(unknown, known):
    '''
    Shows unknown picture and the known picture that it resembles the most
    '''
    k_pic = Image.fromarray(known)
    u_pic = Image.fromarray(unknown)
    k_pic.show()
    u_pic.show()

def show_from_database():
    dat = dm.get_pictures() #returns name, picture in bytes and numpy array of faces 
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
    pics = dm.get_pictures() #list of tuples (person_id, face_enconding)
    person_ids = []
    encodings = []
    for person_id, encoding in pics:
        person_ids.append(person_id)
        encodings.append(encoding)

    #comparing and finding out if there's a match
    results = face_recognition.compare_faces(encodings, unknown_face_enconding,0.6)
    face_distances = face_recognition.face_distance(encodings, unknown_face_enconding)
    best_match_index = np.argmin(face_distances)
    ic(results,person_ids, face_distances, best_match_index)
    
    if results[best_match_index]:
        p_id = person_ids[best_match_index]
        if p_id:
            person = crud.get_entry(classes.Person, p_id)
            print(f'Se reconoció a la persona {person}')
        else:
            print(f'No se reconoció a nadie')


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

    # return a 2-tuple of the face locations and their corresponding predictions
    return (locs, preds)

def has_mask(frame, faceNet, maskNet):
    has_mask = None
    _, preds = detect_and_predict_mask(frame, faceNet, maskNet)

    if len(preds) > 0:
        mask, without_mask = preds[0] #each pred is a tuple of probability of having and not having mask in a face. Only first face is taken
        has_mask = True if mask > without_mask else False
    
    return has_mask #True means it has mask, False means it doesn't and None means there's no face on the picture

def has_time_passed(time_since, interval): #returns true if interval of time has passed since a specific time
    return True if (time.time() - time_since) > interval else False


def face_recog_live(camera_address=0):
    
    pics = dm.get_pictures() #list of tuples (person_id, face_enconding)
    person_ids = []
    encodings = []
    for person_id, encoding in pics:
        person_ids.append(person_id)
        encodings.append(encoding)

    video_capture = cv2.VideoCapture(camera_address)#starting camera
    time.sleep(2.0)

    
    mask_detection_flag = False #indicates a mask has been detected
    face_recognition_flag = False #indicates a face has been recognized

    MASK_DETECT_INTERVAL = 5 #time interval in seconds for calling mask detection function
    FACE_RECOG_INTERVAL = 5 #time interval in seconds for calling face recognition function
    TIME_START_AGAIN = 5 #time interval in seconds for start everything again after opening a door
    WINDOW_TIME_SINCE = 20 #time interval in seconds a person has to remove it's mask after it has been detected for face recog, o time it has to put a mask on after it's face has been recognized  

    time_mask_detection = time.time() #timestamp for last time since has_mask was called, to only call every 'MASK_DETECT_INTERVAL' seconds
    time_face_recognition = time.time() #timestamp for last time compare_faces was called, to only call every 'FACE_RECOG_INTERVAL' seconds
    time_since_mask = time.time() #timestamp for mask being detected, to allow for a window in which mask_detection_flag will be true
    time_since_face = time.time() #timestamp for face being recognized, to allow for a window in which face_recognition_flag will be true
    time_welcomed = time.time() #timestamp for when person was welcomed (face and mask were approved)
    
    while True:

        _, frame = video_capture.read()#getting frame
        cv2.imshow('Video', frame) #showing video
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        mask = None

        if not has_time_passed(time_welcomed,TIME_START_AGAIN): #if time since last welcome is less than TIME_START_AGAIN, continue with the loop
            continue
        
        #mask detection and face recognition flags will only stay true for WINDOW_TIME_SINCE seconds
        if has_time_passed(time_since_mask,WINDOW_TIME_SINCE): 
            mask_detection_flag = False
        if has_time_passed(time_since_face,WINDOW_TIME_SINCE):
            face_recognition_flag = False
        
        #only making mask (and person) comprobation every MASK_DETECT_INTERVAL seconds
        if has_time_passed(time_mask_detection, MASK_DETECT_INTERVAL):
            mask = has_mask(frame, faceNet, maskNet)
            time_mask_detection = time.time()

        if mask == None: #if no face was detected, get another frame
            continue
        
        if mask:
            mask_detection_flag = True
            time_since_mask = time.time() #takes time since mask was detected to allow for 'FACE_RECOG_INTERVAL' seconds at most for face recognition
            if not face_recognition_flag: #No face recog flag means that's the only thing left for welcoming. Because there's a mask, the person is asked to remove it for the face_recognition to begin
                print('Se ha detectado mascarilla. Remuevala momentaneamente')
        elif has_time_passed(time_face_recognition, FACE_RECOG_INTERVAL) and not face_recognition_flag: #only if there's no mask, a face hadn't been recognized and time has passed since last face recognition there'll be a face recognition
            rgb_frame = frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_frame)
            unknown_face_encondings = face_recognition.face_encodings(rgb_frame, face_locations)
            if unknown_face_encondings:
                unknown_face_enconding = unknown_face_encondings[0]
                results = face_recognition.compare_faces(encodings, unknown_face_enconding)
                face_distances = face_recognition.face_distance(encodings, unknown_face_enconding)
                best_match_index = np.argmin(face_distances)
                if results[best_match_index]:
                    p_id = person_ids[best_match_index]    
                    
                    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    person = crud.get_entry(classes.Person, p_id)
                    print(f'Se reconoció a la persona {person}, en la fecha {now}')
                    
                    face_recognition_flag = True
                    time_since_face = time.time()
                    #dm.insert_picture_discovered(person_id, rgb_frame, unknown_face_enconding)
                    if mask_detection_flag:
                        print('Recuerde subir su mascarilla')
                    else:
                        print('No se ha detectado mascarilla. Póngasela')
        
        if face_recognition_flag and mask_detection_flag: #after a face has been recognized and a mask has been detected, the door will open and all control variables will reset to original state
            mask_detection_flag = False
            face_recognition_flag = False

            time_mask_detection = time.time() 
            time_face_recognition = time.time() 
            time_since_mask = time.time() 
            time_since_face = time.time() 
            time_welcomed = time.time()
            print('Bienvenido')
            #open door
    
    video_capture.release()
    cv2.destroyAllWindows()

faceNet = None
maskNet = None

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--face", type=str,default="MaskDetection/face_detector",
        help="path to face detector model directory")
    ap.add_argument("-m", "--model", type=str,default="MaskDetection/mask_detector.model",
        help="path to trained face mask detector model")
    ap.add_argument("-c", "--confidence", type=float, default=0.5,
        help="minimum probability to filter weak detections")
    ap.add_argument('--add-picture-file', action='store')
    ap.add_argument('--add-picture-directory', action='store')
    ap.add_argument('--face-recog-live', action='store_true')
    ap.add_argument('--face-recog-file', action='store')
    
    args = vars(ap.parse_args())    

    if args['face_recog_live']:
        # load our serialized face detector model from disk
        prototxtPath = os.path.sep.join([args["face"], "deploy.prototxt"])
        weightsPath = os.path.sep.join([args["face"],
        "res10_300x300_ssd_iter_140000.caffemodel"])
        faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

        # load the face mask detector model from disk
        maskNet = load_model(args["model"])
        
        # IP_camera_address = 'rtsp://gustavo:123456789Gu@10.0.0.121:554/Streaming/Channels/102'
        # face_recog_live(IP_camera_address)
        face_recog_live()
    elif args['add_picture_directory']:
        dm.insert_picture_directory(args['add_picture_directory'])
    elif args['face_recog_file']:
        face_recog_file(args['face_recog_file'])