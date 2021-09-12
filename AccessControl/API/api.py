import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.crud as crud
import base64
from PIL import Image
import io
import json
from flatten_json import flatten
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route('/list/persons', methods=['GET'])
def list_persons():
    all_persons = crud.get_entries(classes.Person)
    only_persons = [person for person in all_persons if not person.is_employee]
    json_data = []
    for dat in only_persons:
        json_data.append(dat.to_dict(
            only=('id', 'first_name', 'last_name', 'identification_document', 'birth_date')))

    return jsonify(json_data)

@app.route('/list/employees', methods=['GET'])
def list_employees():
    data = crud.get_entries(classes.Employee)
    json_data = []

    for dat in data:
        print(dat.person)
        json_data.append(flatten(dat.to_dict(
            only=('id', 'person.first_name', 'person.last_name',
                  'person.identification_document', 'person.birth_date',
                  'position', 'email', 'start_date'))))
    return jsonify(json_data)

@app.route('/list/entries', methods=['GET'])
def list_time_entries():
    data = crud.get_entries(classes.Time_Entry)
    json_data = []
    for dat in data:
        json_data.append(flatten(dat.to_dict(
            only=('id', 'action', 'action_time', 'person.id', 'person.first_name', 'person.last_name',
                  ))))

    return jsonify(json_data)

@app.route('/list/entries/<id_entry>', methods=['GET'])
def get_time_entry(id_entry):
    data = crud.get_entry(classes.Time_Entry, id=id_entry)
    json_data = None
    if data:
        json_data = flatten(data.to_dict(
            only=('id', 'action', 'action_time', 'person.id', 'person.first_name',
                  'person.last_name', 'person.position', 'picture.picture_bytes')))

    return jsonify(json_data)

@app.route('/foo', methods=['GET'])
def foo():
    data = request.get_json(force=True)
    if data:
        print(data["foo1"])
        print(data.get("foo2"))
        print(data["foo3"])

    return jsonify(data)

@app.route('/regist/employees', methods=['POST'])
def regist_employees():
    data = request.get_json(force=True)
    if data:
        # Person data
        identification_doc = data['identification_doc']
        first_name = data['first_name']
        last_name = data['last_name']
        birth_date = data['birth_date']
        person = classes.Person(identification_document=identification_doc,
                                first_name=first_name, last_name=last_name,
                                birth_date=birth_date, is_employee=True)
        # Employee data
        position = data['position']
        email = data['email']
        start_date = data['start_date']

        employee = classes.Employee(id=person.id, position=position,
                                    email=email, start_date=start_date, person=person)

        # Picture data
        base64_pics = data['pictures']
        picture_list = []
        for base64_pic in base64_pics:
            pic_bytes = base64.b64decode(base64_pic.split(",")[1])
            pic_io = io.BytesIO(pic_bytes)
            picture_data_constructor = dm.process_picture_file(pic_io)
            if picture_data_constructor:
                raw_bin_pic, face_encoding = picture_data_constructor
                picture = classes.Picture(picture_bytes=raw_bin_pic,
                                          face_bytes=face_encoding,
                                          person=person)
                picture_list.append(picture)
            else:
                print('This picture does not contains a face')
        # Vaccine data
        vaccine_list = []
        for i in range(1, 4):
            dose_lab = data.get(f'dose_lab_{i}')
            dose_date = data.get(f'dose_date_{i}')
            lot_num = data.get(f'lot_num_{i}')
            if dose_lab and dose_date and lot_num:
                vaccine = classes.Vaccine(
                    dose_lab=dose_lab, dose_date=dose_date, lot_num=lot_num, person=person)
                vaccine_list.append(vaccine)
                
                # crud.add_entry(vaccine)

        if picture_list:
            crud.add_entry(employee)
            print(employee)
            for picture in picture_list:
                crud.add_entry(picture)
                print(picture)
            for vaccine in vaccine_list:
                crud.add_entry(vaccine)
                print(vaccine)
        else:
            return jsonify(success=False)

    return jsonify(success=True)


# @app.route('/regist/persons', methods=['POST'])
# def regist_persons():
#     data = request.get_json(force=True)
#     if data:
#     # Persona
#         identification_doc = data['identification_doc']
#         first_name = data['first_name']
#         last_name = data['last_name']
#         birth_date = data['birth_date']
#         # Foto
#         # image = request.files['picture']
#         # image_data = image.read()
#         # bytes, encoding = dm.process_picture_file(image_data)

#         person = classes.Person(identification_document=identification_doc, first_name=first_name,
#                                 last_name=last_name, birth_date=birth_date, is_employee=True)
#         #crud.add_entry(person)


@app.route('/vaccine/regist', methods=['POST', 'GET'])
def vacuna():
    vacc = None
    if request.method == 'POST':
        person_id = request.form['person_id']
        dose_type = request.form['dose_type']
        dose_date = request.form['dose_date']

        vacc = classes.Vaccine(person_id, dose_type, dose_date)

    crud.add_entry(vacc)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
