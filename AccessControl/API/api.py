import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.crud as crud
import base64
from PIL import Image
import io
from datetime import datetime, timedelta
from flatten_json import flatten
from flask import Flask, jsonify, request
from flask_cors import CORS
from icecream import ic
import requests

app = Flask(__name__)
CORS(app)


@app.route('/list/persons', methods=['GET'])
def list_persons():
    all_persons = crud.get_entries(classes.Person)
    only_persons = [person for person in all_persons if not person.is_employee]
    json_data = []
    for dat in only_persons:
        json_data.append(dat.to_dict(
            only=('id', 'first_name', 'last_name', 'identification_document', 'birth_date', 'email')))

    return jsonify(json_data)

@app.route('/list/employees', methods=['GET'])
def list_employees():
    data = crud.get_entries(classes.Employee)
    json_data = []

    for dat in data:
        json_data.append(flatten(dat.to_dict(
            only=('id', 'person.first_name', 'person.last_name',
                  'person.identification_document', 'person.birth_date',
                  'position', 'person.email', 'start_date'))))
    return jsonify(json_data)

@app.route('/list/vaccines/', methods=['POST'])
def person_by_ident_doc():
    data = request.get_json(force=True)
    if data:
        identification_document = data["identification_doc"]
        person = crud.person_by_ident_doc(identification_document)
        json_data = []
        if person:
            person = person[0]
            json_data.append(flatten(person.to_dict(
                only=('id', 'first_name', 'last_name', 'identification_document', 'birth_date',))))
            vaccines = crud.vaccines_by_person(person)

            for vaccine in vaccines:
                json_data.append(flatten(vaccine.to_dict(only=("dose_lab", "dose_date", "lot_num"))))
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

@app.route('/list/person', methods=['POST'])
def person_by_id():
    data = request.get_json(force=True)
    if data:
        id = data["id"]
        person = crud.get_entry(classes.Person, id)
        json_data = []
        if person:
            person = person[0]
            json_data.append(flatten(person.to_dict(
                only=('id', 'first_name', 'last_name', 'identification_document', 'birth_date', 'email'))))
            vaccines = crud.vaccines_by_person(person)

            for vaccine in vaccines:
                json_data.append(flatten(vaccine.to_dict(only=("dose_lab", "dose_date", "lot_num"))))

        return jsonify(json_data)

@app.route('/list/employee', methods=['POST'])
def employee_by_id():
    data = request.get_json(force=True)
    if data:
        id = data["id"]
        employee = crud.get_entry(classes.Employee, id)
        json_data = []
        if employee:
            employee = employee[0]
            json_data.append(flatten(employee.to_dict(
                only=('id', 'person.first_name', 'person.last_name',
                      'person.identification_document', 'person.birth_date',
                      'position', 'person.email', 'start_date',))))
            vaccines = crud.vaccines_by_person(employee)

            for vaccine in vaccines:
                json_data.append(flatten(vaccine.to_dict(only=("dose_lab", "dose_date", "lot_num"))))

            comments = crud.comments_by_employee(employee)

            for comments in comments:
                json_data.append(flatten(comments.to_dict(only=("timestamp", "text"))))

            json_data.insert(0, {"comment_start_possition": (len(vaccines) + 2)})

        return jsonify(json_data)

@app.route('/list/entries', methods=['GET'])
def get_time_entry():
    data = request.get_json(force=True)
    if data:
        id = data["id"]
        data = crud.get_entry(classes.Time_Entry, id=id)
        json_data = None
        if data:
            json_data = flatten(data.to_dict(
                only=('id', 'action', 'action_time', 'person.id', 'person.first_name',
                      'person.last_name', 'person.position', 'picture.picture_bytes')))

        return jsonify(json_data)

@app.route('/regist/employees', methods=['POST'])
def regist_employees():
    data = request.get_json(force=True)
    if data:
        # Person data
        identification_doc = data['identification_doc']
        first_name = data['first_name']
        last_name = data['last_name']
        birth_date = data['birth_date']
        email = data['email']
        person = classes.Person(identification_document=identification_doc,
                                first_name=first_name, last_name=last_name,
                                email=email, birth_date=birth_date, is_employee=True)
        # Employee data
        position = data['position']
        start_date = data['start_date']

        employee = classes.Employee(id=person.id, position=position,
                                    start_date=start_date, person=person)

        # Picture data
        base64_pics = data['pictures']
        picture_list = []
        for base64_pic in base64_pics:
            try:
                pic_bytes = base64.b64decode(base64_pic.split(",")[1])
            except IndexError:
                pic_bytes = base64.b64decode(base64_pic)
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

        if picture_list:
            crud.add_entry(employee)
            for picture in picture_list:
                crud.add_entry(picture)
            for vaccine in vaccine_list:
                crud.add_entry(vaccine)
        else:
            return jsonify(success=False)

    return jsonify(success=True)

@app.route('/regist/bulk', methods=['POST'])
def regist_bulk():
    json_data = request.get_json(force=True)
    if json_data:
        b64_string = json_data.get('base64_doc')
        if b64_string:
            b64_doc = base64.b64decode(b64_string.split(",")[1])
            csv_data = b64_doc.decode('utf-8').splitlines()

            header = csv_data[0].split(',')
            rows = [entry.split(',') for entry in csv_data[1:]]

            final_data = []
            for row in rows:
                row_dict = {}
                for k, v in zip(header, row):
                    if k != 'pictures':
                        row_dict[k] = v
                    else:
                        row_dict[k] = [v]
                final_data.append(row_dict)
            print(len(final_data))
            for data in final_data:
                requests.post('http://localhost:5000/regist/employees', json=data)

            # print(final_data)
    return jsonify(success=True)

@app.route('/appointment', methods=['POST'])
def make_appointment():
    data = request.get_json(force=True)
    if data:
        # Person data
        identification_doc = data['identification_doc']
        first_name = data['first_name']
        last_name = data['last_name']
        birth_date = data['birth_date']
        email = data['email']
        person = classes.Person(identification_document=identification_doc,
                                first_name=first_name, last_name=last_name,
                                email=email, birth_date=birth_date)
        # Picture data
        base64_pics = data['pictures']
        picture_list = []
        for base64_pic in base64_pics:
            pic_bytes = base64.b64decode(base64_pic.split(",")[1])
            pic_io = io.BytesIO(pic_bytes)
            # Image.open(pic_io).show()
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

        employee_id = int(data['employee_id'])
        employee = crud.get_entry(classes.Employee, employee_id)

        # Appointment data
        date = data['appointment_date']
        time = data['appointment_time']
        full_date = f"{date} {time}:00"
        appointment_start = datetime.strptime(full_date, "%Y-%m-%d %H:%M:%S")

        appointment = classes.Appointment(
            appointment_start=appointment_start,
            appointment_end=appointment_start + timedelta(hours=1),
            person=person, employee=employee)

        if picture_list:
            crud.add_entry(appointment)
            for picture in picture_list:
                crud.add_entry(picture)
            for vaccine in vaccine_list:
                crud.add_entry(vaccine)
        else:
            return jsonify(success=False)

    return jsonify(success=True)


@app.route('/foo', methods=['GET'])
def foo():
    data = request.get_json(force=True)
    if data:
        print(data["foo1"])
        print(data.get("foo2"))
        print(data["foo3"])

    return jsonify(data)


@app.route('/vaccine/regist', methods=['POST', 'GET'])
def vaccine():
    vacc = None
    if request.method == 'POST':
        person_id = request.form['person_id']
        dose_type = request.form['dose_type']
        dose_date = request.form['dose_date']

        vacc = classes.Vaccine(person_id, dose_type, dose_date)

    crud.add_entry(vacc)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
