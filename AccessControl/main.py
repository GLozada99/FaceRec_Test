import numpy as np
import os
import argparse

import AccessControl.Functions.functions as func
import AccessControl.Data.data_manipulation as dm
from cv2 import cv2
from tensorflow.keras.models import load_model
import asyncio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--face", type=str,
                    default="../MaskDetection/face_detector",
                    help="path to face detector model directory")

    ap.add_argument("-m", "--model", type=str,
                    default="../MaskDetection/mask_detector.model",
                    help="path to trained face mask detector model")
    ap.add_argument("-c", "--confidence", type=float,
                    default=0.5,
                    help="minimum probability to filter weak detections")

    ap.add_argument('--add-picture-file', action='store')
    ap.add_argument('--add-picture-directory', action='store')
    ap.add_argument('--face-recog-live', action='store_true')
    ap.add_argument('--face-recog-file', action='store')
    ap.add_argument('--show-pictures-database', action='store_true')

    args = vars(ap.parse_args())

    if args['face_recog_live']:
        # load our serialized face detector model from disk
        print(os.path.abspath(args["face"]), os.path.abspath(args["model"]))
        prototxtPath = os.path.sep.join(
            [os.path.abspath(args["face"]), "deploy.prototxt"])
        weightsPath = os.path.sep.join([os.path.abspath(args["face"]),
                                        "res10_300x300_ssd_iter_140000.caffemodel"])
        faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)
        # load the face mask detector model from disk
        maskNet = load_model(os.path.abspath(args["model"]))

        IP_camera_address = 'rtsp://gustavo:123456789Gu@10.0.0.121:554/Streaming/Channels/102'
        # face_recog_live(faceNet,maskNet,IP_camera_address)
        asyncio.run(func.face_recog_live(faceNet, maskNet, IP_camera_address))
    elif args['add_picture_directory']:
        dm.insert_picture_directory(args['add_picture_directory'])
    elif args['face_recog_file']:
        func.face_recog_file(args['face_recog_file'])
    elif args['show_pictures_database']:
        func.show_from_database()


if __name__ == "__main__":
    main()
