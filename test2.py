from PIL import Image
import face_recognition
import os
# Load the jpg file into a numpy array
face_locations = []
images = []
for root,dirs,files in os.walk('./KnownIMGs',topdown=True):
    for name in files:
        # img = Image.open(f'KnownIMGs/{name}')
        # img.resize((300,400))
        # img.save(f'KnownIMGs/{name}')
        image = face_recognition.load_image_file(f'KnownIMGs/{name}')
        face_location = face_recognition.face_locations(image, number_of_times_to_upsample=0, model='hog')[0]
        face_locations.append(face_location)
        images.append(image)
        # print("I found {} face(s) in this photograph."))
        

# Find all the faces in the image using a pre-trained convolutional neural network.
# This method is more accurate than the default HOG model, but it's slower
# unless you have an nvidia GPU and dlib compiled with CUDA extensions. But if you do,
# this will use GPU acceleration and perform well.
# See also: find_faces_in_picture.py


for i,face_location in enumerate(face_locations):
    
    print(face_location)
    # Print the location of each face in this image
    top, right, bottom, left = face_location
    print(f'A face is located at pixel location Top: {top}, Left: {left}, Bottom: {bottom}, Right: {right}')

    # You can access the actual face itself like this:
    face_image = images[i][top:bottom, left:right]
    pil_image = Image.fromarray(face_image)
    pil_image.show()