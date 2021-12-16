import os
import argparse
import asyncio
import AccessControl.Functions.functions as func
import AccessControl.Data.crud as crud
import AccessControl.Data.classes as classes

from decouple import config
from cv2 import cv2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--face", type=str,
                    default="../MaskDetection/face_detector",
                    help="path to face detector model directory")

    ap.add_argument("-m", "--model", type=str,
                    default="../MaskDetection/mask_detector.model",
                    help="path to trained face mask detector model")

    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--camera', action='store')
    # ap.add_argument('--pc', action='store_true')

    args = vars(ap.parse_args())

    maskNet, faceNet = func.get_mask_face_net(config('FACE'), config('MODEL'))

    camera = crud.get_entry(classes.Camera, args['camera'])

    asyncio.run(func.face_recog_live(faceNet, maskNet,camera))

if __name__ == "__main__":
    main()
