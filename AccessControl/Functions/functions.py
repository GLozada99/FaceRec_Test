import sys
import time
from datetime import datetime
import numpy as np
import face_recognition
from cv2 import cv2
from PIL import Image
import AccessControl.Data.crud as crud
import AccessControl.Data.classes as classes
import AccessControl.Data.data_manipulation as dm
import AccessControl.Functions.matrix_functions as mx
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import asyncio


def show_pic_from_array(picture_array):
    '''
    Shows picture given numpy array
    '''
    Image.fromarray(picture_array).show()


def show_from_database():
    '''
    Shows all pictures from database
    '''
    pics = dm.get_pictures()
    # list of tuples (person_id, face_enconding)
    for pictures in pics:
        _ = input('Presione enter')
        show_pic_from_array(pictures)


def has_time_passed(time_since, interval):
    # returns true if interval of time has passed since a specific time
    return True if (time.time() - time_since) > interval else False


def detect_and_predict_mask(frame, faceNet, maskNet):
    # grab the dimensions of the frame and then construct a blob
    # from it
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))

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

    # return a 2-tuple of the face locations
    # and their corresponding predictions
    return (locs, preds)


async def has_mask(frame, faceNet, maskNet):
    has_mask = None
    _, preds = detect_and_predict_mask(frame, faceNet, maskNet)

    if len(preds) > 0:
        # each pred is a tuple of probability of having and not having mask.
        # Only first face is taken
        mask, without_mask = preds[0]
        has_mask = True if mask > without_mask else False
    # True means it has mask, False means it doesn't
    # None means there's no face on the picture
    return has_mask


async def face_recog(frame, encodings):
    rgb_frame = frame[:, :, ::-1]
    face_locations = face_recognition.face_locations(rgb_frame)
    unknown_face_encondings = face_recognition.face_encodings(
        rgb_frame, face_locations)
    result = False
    best_match_index = 0
    if unknown_face_encondings:
        unknown_face_enconding = unknown_face_encondings[0]
        results = face_recognition.compare_faces(
            encodings, unknown_face_enconding)
        face_distances = face_recognition.face_distance(
            encodings, unknown_face_enconding)
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            result = results[best_match_index]

    return (result, best_match_index)


def face_recog_file(picture_path, show_pictures=False):
    '''
    Applies face recognition to a picture given its path
    Uses a database of previously known pictures
    '''
    # loading picture from file
    picture_loaded = face_recognition.load_image_file(picture_path)

    # getting face locations of picture so that face encoding can be faster
    face_locations = face_recognition.face_locations(picture_loaded)
    unknown_face_encondings = face_recognition.face_encodings(
        picture_loaded, face_locations)

    if unknown_face_encondings:
        # analizing only principal face in picture
        unknown_face_enconding = unknown_face_encondings[0]
    else:
        # exiting program if there are no faces on picture
        print('No se ha detectado una cara')
        sys.exit(1)

    # getting data of known pictures through database
    # list of tuples (person_id, face_enconding)
    pics = dm.get_pictures_encodings()
    person_ids = []
    encodings = []
    pic_ids = []
    for person_id, encoding, pic_id in pics:
        person_ids.append(person_id)
        encodings.append(encoding)
        pic_ids.append(pic_id)

    # comparing and finding out if there's a match
    results = face_recognition.compare_faces(
        encodings, unknown_face_enconding, 0.6)

    face_distances = face_recognition.face_distance(
        encodings, unknown_face_enconding)

    best_match_index = np.argmin(face_distances)

    if results[best_match_index]:
        p_id = person_ids[best_match_index]
        if p_id:
            person = crud.get_entry(classes.Person, p_id)
            print(f'Se reconoció a la persona {person}')
        else:
            print('No se reconoció a nadie')

    if show_pictures:
        # showing unknown image and its better match
        pic_id = pic_ids[best_match_index]
        pic = crud.get_entry(classes.Picture, pic_id)
        if pic:
            picture_array = dm.unprocess_picture(pic.picture_bytes)
            show_pic_from_array(picture_array)


async def face_recog_live(faceNet, maskNet, camera_address=0):

    pics = dm.get_pictures_encodings()
    # list of tuples (person_id, face_enconding)
    person_ids = []
    encodings = []
    for person_id, encoding, _ in pics:
        person_ids.append(person_id)
        encodings.append(encoding)

    # timestamp for last time since has_mask was called,
    # to only call every 'MASK_DETECT_INTERVAL' seconds
    time_mask_detection = time.time()

    # timestamp for last time compare_faces was called,
    # to only call every 'FACE_RECOG_INTERVAL' seconds
    time_face_recognition = time.time()

    # timestamp for last time temp_okay was called,
    # to only call every 'TEMP_COMPROBATION_INTERVAL' seconds
    time_temp_comprobation = time.time()

    # timestamp for mask being detected, to allow for a
    # window in which mask_detection_flag will be true
    time_since_mask = time.time()

    # timestamp for face being recognized, to allow for a
    # window in which face_recognition_flag will be true
    time_since_face = time.time()

    # maximum time since an acceptable temp was taken from the sensor
    acceptable_temp_time = 20

    # timestamp for when person was welcomed (face and mask were approved)
    time_welcomed = time.time()

    video_capture = cv2.VideoCapture(camera_address)  # starting camera

    server = 'https://matrix-client.matrix.org'
    user = '@tavo9:matrix.org'
    password = 'O1KhpTBn7D47'
    device_id = 'LYTVJFQRJG'
    temper_room_name = '#temper:matrix.org'
    speaker_room_name = '#speaker:matrix.org'

    client = await mx.matrix_login(server, user, password, device_id)
    temper_room_id = await mx.matrix_get_room_id(client, temper_room_name)
    speaker_room_id = await mx.matrix_get_room_id(client, speaker_room_name)

    mask_detection_flag = False  # indicates a mask has been detected
    face_recognition_flag = False  # indicates a face has been recognized
    # indicates temperature has been comprobated and aprooved
    temp_comprobation_flag = False

    # time interval in seconds: TIIS
    MASK_DETECT_INTERVAL = 5  # TIIS for calling mask detection function
    FACE_RECOG_INTERVAL = 8  # TIIS for calling face recognition function
    TEMP_COMPROBATION_INTERVAL = 10  # TIIS for calling temp comprobation function
    TIME_START_AGAIN = 13  # TIIS for start again after opening a door
    WINDOW_TIME_SINCE = 30  # TIIS a person has to remove it's mask
    # after it has been detected for face recog
    # or time it has to put a mask on after it's face has been recognized
    messages = []
    message_task = None
    while True:

        _, frame = video_capture.read()  # getting frame
        cv2.imshow('Video', frame)  # showing video
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        mask = None
        if messages:
            message_task = asyncio.create_task(mx.matrix_send_message(
                client, speaker_room_id, '\n'.join(messages)))
            await message_task
            print(messages)
            messages.clear()

        # if time since last welcome is less than TIME_START_AGAIN,
        # continue with the loop
        if not has_time_passed(time_welcomed, TIME_START_AGAIN):
            continue

        # mask detection and face recognition flags will only stay true
        # for WINDOW_TIME_SINCE seconds
        if has_time_passed(time_since_mask, WINDOW_TIME_SINCE):
            mask_detection_flag = False
        if has_time_passed(time_since_face, WINDOW_TIME_SINCE):
            face_recognition_flag = False

        # only making mask (and person) comprobation
        # every MASK_DETECT_INTERVAL seconds
        if has_time_passed(time_mask_detection, MASK_DETECT_INTERVAL):
            has_mask_task = asyncio.create_task(
                has_mask(frame, faceNet, maskNet))
            mask = await has_mask_task
            time_mask_detection = time.time()

        if mask is None:  # if no face was detected, get another frame
            continue

        if has_time_passed(time_temp_comprobation, TEMP_COMPROBATION_INTERVAL):
            temp_okay_task = asyncio.create_task(
                temp_okay(client, acceptable_temp_time, temper_room_id))
            temp_comprobation_flag, _ = await temp_okay_task
            time_temp_comprobation = time.time()
            if temp_comprobation_flag is False:
                messages.append('7TempIsGreaters')
                print('Temperatura superior al rango designado')
            elif temp_comprobation_flag is None:
                print('Por favor, tome su temperatura en el sensor')
                messages.append('8TakeTempSens')

        if mask:
            mask_detection_flag = True
            # Takes time since mask was detected to allow for
            # 'FACE_RECOG_INTERVAL' seconds at most for face recognition
            time_since_mask = time.time()
            if not face_recognition_flag:
                # No face recog flag means that's the only thing left for welcoming.
                # Because there's a mask, the person is asked to remove it for the face_recognition to begin
                print('Se ha detectado mascarilla. Remuevala momentaneamente.')
                messages.append('1MaskWasDetected')

        # Only if there's no mask, a face hadn't been recognized
        # and time has passed since last face recognition there'll be a face recognition
        elif has_time_passed(time_face_recognition, FACE_RECOG_INTERVAL) and not face_recognition_flag:
            face_recog_task = asyncio.create_task(face_recog(
                frame, encodings))
            face_recognition_flag, best_match_index = await face_recog_task
            if face_recognition_flag:
                p_id = person_ids[best_match_index]

                now = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime())
                person = crud.get_entry(classes.Person, p_id)

                print(
                    f'Se reconoció a la persona {person}, en la fecha {now}')
                messages.append('2PersonWasRecognized')

                face_recognition_flag = True
                time_since_face = time.time()
                # dm.insert_picture_discovered(person_id,
                # rgb_frame, unknown_face_enconding)
                if mask_detection_flag:
                    print('Recuerde subir su mascarilla')
                    messages.append('3PutMaskOn')
                else:
                    print('No se ha detectado mascarilla. Póngasela')
                    messages.append('4MaskWasNotDetected')

            else:
                print('Persona desconocida en la puerta')
                messages.append('6UnknownPerson')
        # After a face has been recognized and a mask has been detected, the door will open if temperature is good
        # and all control variables will reset to original state
        if face_recognition_flag and mask_detection_flag:
            if temp_comprobation_flag:
                mask_detection_flag = False
                face_recognition_flag = False
                temp_comprobation_flag = False

                time_mask_detection = time.time()
                time_face_recognition = time.time()
                time_temp_comprobation = time.time()
                time_since_mask = time.time()
                time_since_face = time.time()
                time_welcomed = time.time()
                print('Bienvenido')
                messages.append('5Welcome')
                # open door
    # if message_task is not None:
    #     await message_task
    video_capture.release()
    cv2.destroyAllWindows()


async def temp_okay(client, acceptable_time, room_id):
    temp_threshold = 38  # in degrees celcius

    data = await mx.matrix_get_messages(client, room_id)
    good_value_flag = False
    answer = None
    temp = 0
    time = 0
    if data:
        last_entry = data[-1]
        try:
            info, time, _ = last_entry
            temp = float(info)
            good_value_flag = True
        except ValueError:
            print('Ultima entrada no es un número')

        if good_value_flag:
            if not has_time_passed(time, acceptable_time):
                answer = temp < temp_threshold

        data.clear()

    return (answer, temp)
