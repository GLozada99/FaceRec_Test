import argparse
import base64
import csv
import io
import os
import re
import sys
from datetime import datetime, timedelta
from http import HTTPStatus

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
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
app.config['JWT_SECRET_KEY'] = _secret
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES
CORS(app)

def _generate_person_picture_vaccines(data):
    # Person data
    identification_doc = re.sub('[^a-zA-Z0-9]', '', data['identification_doc'])
    first_name = data['first_name']
    last_name = data['last_name']
    birth_date = data['birth_date']
    email = data['email']

    person = crud.person_by_ident_doc(identification_doc)
    existent = False
    if person:
        person = person[0]
        if not person.active:
            person.identification_document = identification_doc
            person.first_name = first_name
            person.last_name = last_name
            person.email = email
            person.birth_date = birth_date
            person.active = True
            existent = True
        else:
            raise ValueError('The employee already exists')
    else:
        person = classes.Person(identification_document=identification_doc,
                                first_name=first_name, last_name=last_name,
                                email=email, birth_date=birth_date)

    base64_pic = data['base64_doc']
    picture = None
    try:
        pic_bytes = base64.b64decode(base64_pic.split(',')[1])
    except IndexError:
        pic_bytes = base64.b64decode(base64_pic)
    pic_io = io.BytesIO(pic_bytes)
    picture_data_constructor = dm.process_picture_file(pic_io)

    if picture_data_constructor:
        raw_bin_pic, face_encoding = picture_data_constructor
        if existent:
            picture = crud.pictures_by_person(person)[0]
            picture.picture_bytes = raw_bin_pic
            picture.face_bytes = face_encoding
            picture.person = person
        else:
            picture = classes.Picture(
                picture_bytes=raw_bin_pic, face_bytes=face_encoding, person=person)

    # Vaccine data
    vaccine_list = []
    old_vaccines = crud.vaccines_by_person(person)
    for vac in old_vaccines:
        crud.delete_entry(classes.Vaccine, vac.id)

    for i in range(1, 4):
        dose_lab = data.get(f'dose_lab_{i}')
        dose_date = data.get(f'dose_date_{i}')
        lot_num = data.get(f'lot_num_{i}')
        if dose_lab and dose_date and lot_num:
            vaccine = classes.Vaccine(
                dose_lab=dose_lab, dose_date=dose_date, lot_num=lot_num, person=person)
            vaccine_list.append(vaccine)
    return (person, picture, vaccine_list, existent)

@app.route('/persons', methods=['GET'])  # Done
@jwt_required()
def list_persons():
    '''Returns all persons who are not employees'''
    persons = crud.get_persons()
    json_data = []
    for dat in persons:
        json_data.append(dat.to_dict(
            only=('id', 'first_name', 'last_name',
                  'identification_document', 'birth_date', 'email')))
    msg = '' if len(json_data) else 'No entries'
    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/employees', methods=['GET'])
def list_employees():
    '''Returns all employees'''
    employees = crud.get_entries(classes.Employee)
    json_data = []

    for emp in employees:
        data = flatten(emp.to_dict(
            only=('id', 'person.first_name', 'person.last_name',
                  'person.identification_document', 'person.birth_date',
                  'position', 'person.email', 'start_date')))
        data["person_role_name"] = emp.person.role.name
        data["person_role_value"] = emp.person.role.value
        json_data.append(data)
    msg = '' if len(json_data) else 'No entries'

    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/appointments', methods=['GET'])
def list_appointments():
    '''Returns all appointments'''
    appointments = crud.get_entries(classes.Appointment)
    json_data = []

    for appointment in appointments:
        data = flatten(appointment.to_dict(
            only=('id', 'appointment_start', 'appointment_end',
                  'employee.person.first_name', 'employee.person.last_name',
                  'employee.id', 'employee.position')))
        data["appointment_status_name"] = appointment.status.name
        data["appointment_status_value"] = appointment.status.value
        json_data.append(data)
    msg = '' if len(json_data) else 'No entries'

    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/appointment/<id>', methods=['GET'])
def appointment_by_id(id):
    '''Returns appointment data regarding the person who made the appointment'''
    appointment = crud.get_entry(classes.Appointment, int(id))
    json_data = {}

    if appointment:
        first_picture = crud.pictures_by_person(appointment.person)[0]
        pic = dm.img_bytes_to_base64(first_picture.picture_bytes)
        json_data['picture'] = pic
        json_data['person_info'] = flatten(appointment.person.to_dict(
            only=('identification_document', 'first_name', 'last_name', 'email')))
        vaccines = crud.vaccines_by_person(appointment.person)
        json_data['vaccines'] = [flatten(vaccine.to_dict(
            only=('dose_lab', 'dose_date', 'lot_num'))) for vaccine in vaccines]
        msg = ''
        status = HTTPStatus.OK
    else:
        msg = 'No entry with this ID'
        status = HTTPStatus.BAD_REQUEST
    return jsonify(result=json_data, msg=msg), status

@app.route('/appointment-status', methods=['PUT'])
def set_appointment_status():
    '''Returns appointment data regarding the person who made the appointment'''
    data = request.get_json(force=True)
    msg = 'Error with data sent'
    status = HTTPStatus.BAD_REQUEST
    if data:
        appointment = crud.get_entry(classes.Appointment, int(data['id']))
        appointment_status = classes.AppointmentStatus(int(data['status']))

        if appointment:
            appointment.status = appointment_status
            if appointment_status == classes.AppointmentStatus.FINALIZED:
                appointment.appointment_end = datetime.now()
            crud.commit()
            msg = 'Status set successfully'
            status = HTTPStatus.OK
        else:
            msg = 'No appointment with that ID'

    return jsonify(msg=msg), status


@app.route('/list/vaccines/', methods=['POST'])
def person_by_ident_doc():
    '''Returns list of all the vaccines of a specific person given the identification_document number'''
    data = request.get_json(force=True)
    if data:
        identification_document = data['identification_doc']
        person = crud.person_by_ident_doc(identification_document)
        json_data = []
        if person:
            person = person[0]
            json_data.append(flatten(person.to_dict(
                only=('id', 'first_name', 'last_name', 'identification_document', 'birth_date',))))
            vaccines = crud.vaccines_by_person(person)
            for vaccine in vaccines:
                json_data.append(flatten(vaccine.to_dict(only=('dose_lab', 'dose_date', 'lot_num'))))
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
        json_data['picture'] = pic
        vaccines = crud.vaccines_by_person(person)
        json_data['vaccines'] = [flatten(vaccine.to_dict(
            only=('dose_lab', 'dose_date', 'lot_num'))) for vaccine in vaccines]
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

@app.route('/employee/<id>', methods=['GET', 'DELETE'])  # Done
@jwt_required()
def employee_methods(id):
    '''
    GET: Returns the picture, vaccine list and comment list of a specific employe given it's ID
    DELETE: Deletes employee
    '''
    if request.method == 'GET':
        employee = crud.get_entry(classes.Employee, int(id))
        json_data = {}
        if employee:
            first_picture = crud.pictures_by_person(employee)[0]
            pic = dm.img_bytes_to_base64(first_picture.picture_bytes)
            json_data['picture'] = pic

            vaccines = crud.vaccines_by_person(employee)

            json_data['vaccines'] = [flatten(vaccine.to_dict(
                only=('dose_lab', 'dose_date', 'lot_num'))) for vaccine in vaccines]

            comments = crud.comments_by_employee(employee)
            json_data['comments'] = [flatten(comment.to_dict(
                only=('timestamp', 'text'))) for comment in comments]
        return jsonify(result=json_data), HTTPStatus.OK
    else:
        crud.delete_entry(classes.Person, int(id))
        return jsonify(msg='Employee deleted successfully'), HTTPStatus.OK

@app.route('/currentEmployee', methods=['GET'])  # Done
@jwt_required()
def auth_employee_info():
    '''Returns the picture, and comment and vaccine list of the current employee'''
    id = get_jwt_identity()
    employee = crud.get_entry(classes.Employee, int(id))
    json_data = {}
    if employee:
        first_picture = crud.pictures_by_person(employee)[0]
        pic = dm.img_bytes_to_base64(first_picture.picture_bytes)
        json_data['picture'] = pic

        vaccines = crud.vaccines_by_person(employee)

        json_data['vaccines'] = [flatten(vaccine.to_dict(
            only=('dose_lab', 'dose_date', 'lot_num'))) for vaccine in vaccines]

        comments = crud.comments_by_employee(employee)

        json_data['comments'] = [flatten(comment.to_dict(
            only=('timestamp', 'text'))) for comment in comments]

        person = employee.person
        json_data['person'] = flatten(person.to_dict(
            only=('first_name', 'last_name', 'identification_document', 'birth_date', 'email', 'employee.position')))

    return jsonify(result=json_data), HTTPStatus.OK

@app.route('/employee', methods=['POST'])
@jwt_required()
def regist_employees():
    '''Receives employee data and inserts it to the database'''
    data = request.get_json(force=True)
    error = False

    msg = 'No correct data'
    status = HTTPStatus.BAD_REQUEST
    if data:
        try:
            person, picture, vaccine_list, existent = _generate_person_picture_vaccines(data)
        except ValueError as e:
            msg = str(e)
            status = HTTPStatus.NOT_ACCEPTABLE
            error = True

        if not error:
            person.role = classes.Role(int(data['role']))
            # Employee data
            position = data['position']
            start_date = data['start_date']
            password = data.get('password', '')
            password = dm.compute_hash(password) if password else password
            if existent:
                employee = crud.get_entry(classes.Employee, person.id, inactive=True)
                employee.position = position
                employee.start_date = start_date
                employee.password = password
            else:
                employee = classes.Employee(id=person.id, position=position,
                                            start_date=start_date, person=person, password=password)

            if picture:
                if not existent:
                    crud.add_entry(employee)
                    crud.add_entry(picture)
                else:
                    crud.commit()

                for vaccine in vaccine_list:
                    crud.add_entry(vaccine)

                msg = 'Employee added succesfully'
                status = HTTPStatus.OK
            else:
                msg = 'No correct picture'

    return jsonify(msg=msg), status

@app.route('/bulk', methods=['POST'])
@jwt_required()
def regist_bulk():
    '''Receives a CSV file (on base64 encoding) containing
    multiple employees and inserts them into the database'''
    json_data = request.get_json(force=True)
    msg = 'Error reading the file'
    if json_data:
        maxInt = sys.maxsize
        try:
            csv.field_size_limit(maxInt)
        except OverflowError:
            maxInt = int(maxInt / 10)
        b64_string = json_data.get('base64_doc')
        if b64_string:
            try:
                b64_doc = base64.b64decode(b64_string.split(',')[1])
            except IndexError:
                b64_doc = base64.b64decode(b64_string)

            reader = csv.DictReader(io.StringIO(b64_doc.decode('utf-8')))
            statuses = set()
            for row in reader:
                response = requests.post(
                    'http://localhost:5000/employee', json=row,
                    headers={'Authorization': request.headers['Authorization']})
                # print(a.status_code)
                statuses.add(response.status_code)
            if statuses.intersection({HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_ACCEPTABLE}):
                msg = 'There was a problem importing employees, \
                either at least one employee already exists, or one picture is not correct'
                status = HTTPStatus.NOT_ACCEPTABLE
            elif statuses.intersection({HTTPStatus.OK}):
                msg = 'Employees imported succesfully'
                status = HTTPStatus.OK
            else:
                msg = 'Unknown Error'
                status = HTTPStatus.INTERNAL_SERVER_ERROR

        return jsonify(msg=msg), status

@app.route('/appointment', methods=['POST'])
def make_appointment():
    '''
    Recieves data regarding an appointment and creates one,
    also creating the person making the appointment and the picture of the person
    '''
    data = request.get_json(force=True)
    msg = 'No correct data'
    if data:
        person, picture, vaccine_list, _ = _generate_person_picture_vaccines(data)

        person.role = classes.Role.PERSON
        employee_id = int(data['employee_id'])
        employee = crud.get_entry(classes.Employee, employee_id)

        # Appointment data
        date = data['appointment_date']
        time = data['appointment_time']
        full_date = f'{date} {time}:00'
        appointment_start = datetime.strptime(full_date, '%Y-%m-%d %H:%M:%S')

        appointment = classes.Appointment(
            appointment_start=appointment_start,
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
                    crud.commit()
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

@app.route('/login', methods=['POST'])  # Done
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

@app.route('/openDoor', methods=['GET'])  # Done
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

@app.route('/user', methods=['GET'])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user_id = get_jwt_identity()
    user = crud.get_entry(classes.Employee, current_user_id)
    fullname, role, status = (
        (f'{user.person.first_name} {user.person.last_name}',
         {'name': user.person.role.name, 'value': user.person.role.value},
         HTTPStatus.OK)
        if user else ('', {'name': '', 'value': ''}, HTTPStatus.UNAUTHORIZED))

    return jsonify(result={'fullname': fullname, 'role': role, 'id': current_user_id}), status

@app.route('/vaccine', methods=['POST'])
@jwt_required()
def add_vaccine():
    data = request.get_json(force=True)
    msg = 'Incorrect Data'
    status = HTTPStatus.BAD_REQUEST
    if data:
        id = get_jwt_identity()
        employee = crud.get_entry(classes.Employee, int(id))

        dose_lab = data['dose_lab']
        dose_date = data['dose_date']
        lot_num = data['lot_num']

        vaccine = classes.Vaccine(
            dose_lab=dose_lab, dose_date=dose_date, lot_num=lot_num, person=employee.person)
        crud.add_entry(vaccine)

        msg = 'Vaccine Added Successfully'
        status = HTTPStatus.OK

    return jsonify(msg=msg), status

@app.route('/comment', methods=['POST'])
@jwt_required()
def add_comment():
    data = request.get_json(force=True)
    msg = 'Incorrect Data'
    status = HTTPStatus.BAD_REQUEST
    if data:
        id = get_jwt_identity()
        employee = crud.get_entry(classes.Employee, int(id))

        commentText = data['commentText']

        comment = classes.Comment(text=commentText, employee=employee, timestamp=datetime.now())
        crud.add_entry(comment)

        msg = 'Comment Added Successfully'
        status = HTTPStatus.OK

    return jsonify(msg=msg), status


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
