import sys
import os
import time
from datetime import datetime
import numpy as np
import face_recognition
from cv2 import cv2
from PIL import Image
from decouple import config
import AccessControl.Data.crud as crud
import AccessControl.Data.enums as enums
import AccessControl.Data.classes as classes
import AccessControl.Data.data_manipulation as dm
import AccessControl.Functions.matrix_functions as mx
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.models import load_model

import asyncio


def get_mask_face_net(face, model):
    prototxtPath = os.path.sep.join(
        [os.path.abspath(face), "deploy.prototxt"])
    weightsPath = os.path.sep.join([os.path.abspath(face),
                                    "res10_300x300_ssd_iter_140000.caffemodel"])
    faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)
    # load the face mask detector model from disk
    maskNet = load_model(os.path.abspath(model))

    return maskNet, faceNet


def has_time_passed(time_since, interval):
    # returns true if interval of time has passed since a specific time
    return (time.time() - time_since) > interval


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
    for i in range(detections.shape[2]):
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
    if faces:
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
        has_mask = mask > without_mask
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
    unknown_face_enconding = None
    if unknown_face_encondings:
        unknown_face_enconding = unknown_face_encondings[0]
        tolerance = 0.5
        results = face_recognition.compare_faces(
            encodings, unknown_face_enconding, tolerance)
        face_distances = face_recognition.face_distance(
            encodings, unknown_face_enconding)
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            result = results[best_match_index]

    return (result, best_match_index, unknown_face_enconding, rgb_frame)


async def temp_okay(client, acceptable_time, room_id):
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

        if good_value_flag and not has_time_passed(time, acceptable_time):
            temp_threshold = 38  # in degrees celcius

            answer = temp < temp_threshold

        data.clear()

    return (answer, temp)


async def get_profile(client, room_id):
    data = await mx.matrix_get_messages(client, room_id)
    error = True
    if data:
        data = data[0]
        try:
            profile = enums.PictureClassification[data[0]]
            error = False
        except KeyError:
            pass
    if error:
        profile = enums.PictureClassification(0)

    return profile


async def face_recog_live(faceNet, maskNet, camera_address, ask_mask, ask_temp, action):
    time_mask_detection = time.time()
    time_face_recognition = time.time()
    time_temp_comprobation = time.time()

    time_since_mask = time.time()
    time_since_face = time.time()

    # timestamp for when person was welcomed (face and mask were approved)
    time_welcomed = time.time()

    # maximum time since an acceptable temp was taken from the sensor
    acceptable_temp_time = 20

    video_capture = cv2.VideoCapture(camera_address)  # starting camera

    server = config('MATRIX_SERVER')
    user = config('MATRIX_USER')
    password = config('MATRIX_PASSWORD')
    device_id = config('MATRIX_DEVICE_ID_FACERECOG')
    temper_room_name = config('MATRIX_ROOM_NAME_TEMPERATURE')
    speaker_room_name = config('MATRIX_ROOM_NAME_SPEAKER')
    door_room_name = config('MATRIX_ROOM_NAME_DOOR')
    profile_room_name = config('MATRIX_ROOM_NAME_PROFILE')

    client = await mx.matrix_login(server, user, password, device_id)
    temper_room_id = await mx.matrix_get_room_id(client, temper_room_name)
    speaker_room_id = await mx.matrix_get_room_id(client, speaker_room_name)
    door_room_id = await mx.matrix_get_room_id(client, door_room_name)
    profile_room_id = await mx.matrix_get_room_id(client, profile_room_name)

    mask_detection_flag = False  # indicates a mask has been detected
    face_recognition_flag = False  # indicates a face has been recognized
    # indicates temperature has been comprobated and aprooved
    temp_comprobation_flag = False

    MASK_DETECT_INTERVAL = 5
    FACE_RECOG_INTERVAL = 8
    TEMP_COMPROBATION_INTERVAL = 10
    TIME_START_AGAIN = 13
    WINDOW_TIME_SINCE = 30

    messages = []
    message_task = None
    profile = await get_profile(client, profile_room_id)
    pics = dm.get_pictures_encodings_by_type(profile)

    # list of tuples (person_id, face_enconding)
    person_ids = []
    encodings = []
    for person_id, encoding, _ in pics:
        person_ids.append(person_id)
        encodings.append(encoding)
    print(profile)
    while True:
        time.sleep(0.02)
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

        if mask:
            mask_detection_flag = True
            # Takes time since mask was detected to allow for
            # 'FACE_RECOG_INTERVAL' seconds at most for face recognition
            time_since_mask = time.time()
            if not face_recognition_flag:
                # No face recog flag means that's the only thing left for welcoming.
                # Because there's a mask, the person is asked to remove it for the face_recognition to begin
                messages.append('1MaskWasDetected')

        # Only if there's no mask, a face hasn't been recognized
        # and time has passed since last face recognition there'll be a face recognition
        elif has_time_passed(time_face_recognition, FACE_RECOG_INTERVAL) and not face_recognition_flag:
            face_recog_task = asyncio.create_task(face_recog(
                frame, encodings))
            face_recognition_flag, best_match_index, unknown_face_encoding, rgb_frame = await face_recog_task
            if face_recognition_flag:
                p_id = person_ids[best_match_index]

                now = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime())
                person = crud.get_entry(classes.Person, p_id)

                print(f'{person}, en la fecha {now}')
                messages.append('2PersonWasRecognized')

                face_recognition_flag = True
                time_since_face = time.time()
                # dm.insert_picture_discovered(person_id,
                # rgb_frame, unknown_face_enconding)
                if mask_detection_flag:
                    messages.append('3PutMaskOn')
                elif ask_mask:
                    messages.append('4MaskWasNotDetected')

            else:
                messages.append('6UnknownPerson')
        # After a face has been recognized and a mask has been detected, the door will open if temperature is good
        # and all control variables will reset to original state

        if has_time_passed(time_temp_comprobation, TEMP_COMPROBATION_INTERVAL) and ask_mask:
            temp_okay_task = asyncio.create_task(
                temp_okay(client, acceptable_temp_time, temper_room_id))
            temp_comprobation_flag, _ = await temp_okay_task
            time_temp_comprobation = time.time()

            if temp_comprobation_flag is False:
                messages.append('7TempIsGreater')
            elif temp_comprobation_flag is None:
                messages.append('8TakeTempSens')

        print(face_recognition_flag, mask_detection_flag, temp_comprobation_flag)
        if face_recognition_flag and (mask_detection_flag or not ask_mask) and (temp_comprobation_flag or not ask_temp):
            open_door = True
            if profile == enums.PictureClassification.ACCEPTED_APPOINTMENTS:
                available_appointment = dm.has_available_appointment(p_id)
                open_door = available_appointment
            if open_door:
                await mx.matrix_send_message(client, door_room_id, '1')
                messages.append('5Welcome')
                dm.insert_picture_discovered(
                    p_id, rgb_frame, unknown_face_encoding, action)
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
            else:
                messages.append('9Appointment')

            # open door
    # if message_task is not None:
    #     await message_task
    video_capture.release()
    cv2.destroyAllWindows()
