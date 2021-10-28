import argparse
import base64
import csv
import io
import os
import re
from datetime import datetime, timedelta

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from http import HTTPStatus
from flask_jwt_extended import (JWTManager, create_access_token,
                                get_jwt_identity, jwt_required)
from flatten_json import flatten
from icecream import ic
from psycopg2.errorcodes import INVALID_TEXT_REPRESENTATION

import AccessControl.Data.classes as classes
import AccessControl.Data.crud as crud
import AccessControl.Data.data_manipulation as dm
import AccessControl.Functions.matrix_functions as mx

ACCESS_EXPIRES = timedelta(hours=1)
_secret = os.environ.get('SECRET')

app = Flask(__name__)
jwt = JWTManager(app)
app.config["JWT_SECRET_KEY"] = _secret
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = ACCESS_EXPIRES
CORS(app)

def _generate_person_picture_vaccines(data):
    # Person data
    identification_doc = re.sub('[^a-zA-Z0-9]', '', data['identification_doc'])
    first_name = data['first_name']
    last_name = data['last_name']
    birth_date = data['birth_date']
    email = data['email']
    person = classes.Person(identification_document=identification_doc,
                            first_name=first_name, last_name=last_name,
                            email=email, birth_date=birth_date)
    # Picture data
    base64_pic = data['base64_doc']
    picture = None
    try:
        pic_bytes = base64.b64decode(base64_pic.split(",")[1])
    except IndexError:
        pic_bytes = base64.b64decode(base64_pic)
    pic_io = io.BytesIO(pic_bytes)
    picture_data_constructor = dm.process_picture_file(pic_io)
    if picture_data_constructor:
        raw_bin_pic, face_encoding = picture_data_constructor
        picture = classes.Picture(picture_bytes=raw_bin_pic,
                                  face_bytes=face_encoding, person=person)

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

    return (person, picture, vaccine_list)

@app.route('/persons', methods=['GET'])  # Done
@jwt_required()
def list_persons():
    '''Returns all persons who are not employees'''
    all_persons = crud.get_entries(classes.Person)
    only_persons = [person for person in all_persons if not person.is_employee]
    json_data = []
    for dat in only_persons:
        json_data.append(dat.to_dict(
            only=('id', 'first_name', 'last_name',
                  'identification_document', 'birth_date', 'email')))
    msg = '' if len(json_data) else 'No entries'
    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/list/employees', methods=['GET'])
def list_employees():
    '''Returns all employees'''
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
    '''Returns list of all the vaccines of a specific person given the identification_document number'''
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

@app.route('/entries', methods=['GET'])  # Done
@jwt_required()
def list_time_entries():
    '''Returns a list of all the entries'''
    data = crud.get_entries(classes.Time_Entry)
    json_data = []
    for dat in data:
        json_data.append(flatten(dat.to_dict(
            only=('id', 'action', 'action_time', 'person.id', 'person.first_name', 'person.last_name',
                  ))))
    msg = '' if len(json_data) else 'No entries'
    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/person/<id>', methods=['GET'])  # Done
@jwt_required()
def person_by_id(id):
    '''Returns the picture and vaccine list of a specific person given it's ID'''
    person = crud.get_entry(classes.Person, int(id))
    json_data = {}
    if person:
        first_picture = crud.pictures_by_person(person)[0]
        pic = dm.img_bytes_to_base64(first_picture.picture_bytes)
        json_data["picture"] = pic
        vaccines = crud.vaccines_by_person(person)
        json_data["vaccines"] = [flatten(vaccine.to_dict(only=("dose_lab", "dose_date", "lot_num")))
                                 for vaccine in vaccines]
        msg = ''
        status = HTTPStatus.OK
    else:
        msg = 'No entry with this ID'
        status = HTTPStatus.BAD_REQUEST
    return jsonify(person=json_data, msg=msg), status

@app.route('/pictureEntry/<id>', methods=['GET'])  # Done
@jwt_required()
def entry_by_id(id):
    '''Returns the picture of a specific entry given it's ID'''
    entry = crud.get_entry(classes.Time_Entry, int(id))
    pic = None
    if entry:
        picture = entry.picture
        pic = dm.img_bytes_to_base64(picture.picture_bytes)
        msg = ''
        status = HTTPStatus.OK
    else:
        msg = 'No entry with this ID'
        status = HTTPStatus.BAD_REQUEST

    return jsonify(picture=pic, msg=msg), status

@app.route('/info/employee', methods=['POST'])
@jwt_required()
def employee_by_id():
    '''Returns the picture, vaccine list and comment list of a specific employe given it's ID'''
    data = request.get_json(force=True)
    print(data)
    if data:
        id = data["id"]
        employee = crud.get_entry(classes.Employee, id)
        json_data = []
        if employee:
            first_picture = crud.pictures_by_person(employee.person)[0]
            pic = dm.img_bytes_to_base64(first_picture.picture_bytes)
            json_data.append({"picture": pic})

            vaccines = crud.vaccines_by_person(employee)

            for vaccine in vaccines:
                json_data.append(flatten(vaccine.to_dict(only=("dose_lab", "dose_date", "lot_num"))))

            comments = crud.comments_by_employee(employee)

            for comments in comments:
                json_data.append(flatten(comments.to_dict(only=("timestamp", "text"))))

            pic_sp = 1
            vac_sp = 2
            com_sp = vac_sp + len(vaccines)
            json_data.insert(0, {"pic_sp": pic_sp, "com_sp": com_sp,
                                 "vac_sp": vac_sp})

        return jsonify(json_data)

@app.route('/info/currentEmployee', methods=['GET'])
@jwt_required()
def auth_employee_info():
    '''Returns the picture and vaccine list of a specific person given it's ID'''
    id = get_jwt_identity()
    person = crud.get_entry(classes.Person, id)
    json_data = []
    if person:
        first_picture = crud.pictures_by_person(person)[0]
        pic = dm.img_bytes_to_base64(first_picture.picture_bytes)
        json_data.append({"picture": pic})

        vaccines = crud.vaccines_by_person(person)

        for vaccine in vaccines:
            json_data.append(flatten(vaccine.to_dict(only=("dose_lab", "dose_date", "lot_num"))))

        comments = crud.comments_by_employee(crud.get_entry(classes.Employee, id))

        for comments in comments:
            json_data.append(flatten(comments.to_dict(only=("timestamp", "text"))))

        json_data.append(flatten(person.to_dict(
            only=('first_name', 'last_name', 'identification_document', 'birth_date'))))

        pic_sp = 1
        vac_sp = 2
        com_sp = vac_sp + len(vaccines)
        per_sp = com_sp + len(comments)

        json_data.insert(0, {"pic_sp": pic_sp, "vac_sp": vac_sp, "per_sp": per_sp})
    return jsonify(json_data)

@app.route('/regist/employee', methods=['POST'])
@jwt_required()
def regist_employees():
    '''Receives employee data and inserts it to the database'''
    data = request.get_json(force=True)
    msg = 'No correct data'
    if data:
        person, picture, vaccine_list = _generate_person_picture_vaccines(data)
        person.is_employee = True
        # Employee data
        position = data['position']
        start_date = data['start_date']
        employee = classes.Employee(id=person.id, position=position,
                                    start_date=start_date, person=person)
        employee.is_admin = bool(data['is_admin'])

        if picture:
            crud.add_entry(employee)
            crud.add_entry(picture)
            for vaccine in vaccine_list:
                crud.add_entry(vaccine)
            return jsonify(success=True), HTTPStatus.OK
        else:
            msg = 'No correct picture'

    return jsonify(msg=msg), 406

@app.route('/regist/bulk', methods=['POST'])
@jwt_required()
def regist_bulk():
    '''Receives a CSV file (on base encoding) containing
    multiple employees and inserts them into the database'''
    json_data = request.get_json(force=True)
    if json_data:
        b64_string = json_data.get('base64_doc')
        if b64_string:
            try:
                b64_doc = base64.b64decode(b64_string.split(",")[1])
            except IndexError:
                b64_doc = base64.b64decode(b64_string)

            reader = csv.DictReader(io.StringIO(b64_doc.decode('utf-8')))
            for row in reader:
                requests.post('http://localhost:5000/regist/employee', json=row)
            else:
                return jsonify(success=True), HTTPStatus.OK

        return jsonify(msg="Errors in the file"), 406

@app.route('/appointment', methods=['POST'])
def make_appointment():
    '''
    Recieves data regarding an appointment and creates one,
    also creating the person making the appointment and the picture of the person
    '''
    data = request.get_json(force=True)
    msg = 'No correct data'
    if data:
        person, picture, vaccine_list = _generate_person_picture_vaccines(data)

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

        if picture:
            crud.add_entry(appointment)
            crud.add_entry(picture)
            for vaccine in vaccine_list:
                crud.add_entry(vaccine)
            return jsonify(success=True), HTTPStatus.OK
        else:
            msg = 'No correct picture'

    return jsonify(msg=msg), 406

@app.route('/newPassword', methods=['PUT'])  # Done
def set_first_password():
    '''
    Sets a first password for an account given the id
    '''
    data = request.get_json(force=True)
    if data:
        id = data.get('id')
        password = data.get('password')
        confirm_password = data.get('confirm_password')

        try:
            id = int(id)
            employee = crud.get_entry(classes.Employee, id)
        except ValueError:
            employee = None

        if employee:
            if not employee.password:
                if (password and confirm_password) and (password.strip() == confirm_password.strip()):
                    hashed_password = dm.compute_hash(password)
                    employee.password = hashed_password
                    crud.update_entry(classes.Employee, employee)
                    msg = 'Password set successfully'
                    status = HTTPStatus.OK
                elif not (password and confirm_password):
                    msg = 'No password was given'
                    status = HTTPStatus.BAD_REQUEST
                else:
                    msg = 'Passwords must be the same'
                    status = HTTPStatus.BAD_REQUEST

            else:
                msg = 'The account already has a password'
                status = HTTPStatus.UNPROCESSABLE_ENTITY
        else:
            msg = 'No employee with this ID'
            status = HTTPStatus.UNPROCESSABLE_ENTITY
    else:
        msg = 'No data was given'
        status = HTTPStatus.BAD_REQUEST

    return jsonify(msg=msg), status

@app.route("/login", methods=["POST"])  # Done
def login():
    data = request.get_json(force=True)
    if data:
        id = data['id']
        password = data['password']

        try:
            id = int(id)
            employee = crud.get_entry(classes.Employee, id)
        except ValueError:
            employee = None

        access_token = ''
        msg = 'Bad username or password'  # if there is no employee or the password is wrong, this will be the msg
        status = HTTPStatus.BAD_REQUEST

        if employee:
            if employee.password:
                if dm.compare_hash(password, employee.password):
                    access_token = create_access_token(identity=id)
                    status = HTTPStatus.OK
                    msg = 'Welcome'
            else:
                msg = 'There is no password set for this user'
                status = HTTPStatus.SEE_OTHER

    return jsonify(msg=msg, access_token=access_token), status

@app.route("/openDoor", methods=['GET'])  # Done
@jwt_required()
async def openDoor():
    try:
        message = '1'
        server = 'https://matrix-client.matrix.org'
        user = '@tavo9:matrix.org'
        password = 'O1KhpTBn7D47'
        device_id = 'LYTVJFQRJG'
        door_room_name = '#doorLock:matrix.org'

        client = await mx.matrix_login(server, user, password, device_id)
        door_room_id = await mx.matrix_get_room_id(client, door_room_name)

        await mx.matrix_send_message(client, door_room_id, message)
        msg = 'Door oppened correctly'
        code = HTTPStatus.OK
        await mx.matrix_logout_close(client)
    except Exception:
        msg = 'Error opening door'
        code = HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(msg=msg), code

@app.route("/user", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    username = ''
    is_admin = False
    current_user_id = get_jwt_identity()
    user = crud.get_entry(classes.Employee, current_user_id)
    if user:
        username = f'{user.person.first_name} {user.person.last_name}'
        is_admin = user.is_admin

    return jsonify(username=username, is_admin=is_admin, id=current_user_id), HTTPStatus.OK

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
