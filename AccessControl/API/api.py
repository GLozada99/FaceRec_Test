import asyncio
import base64
import csv
import io
import re
import sys
from decouple import config
from datetime import datetime, timedelta
from http import HTTPStatus

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import (JWTManager, create_access_token,
                                get_jwt_identity, jwt_required)
from flatten_json import flatten

import AccessControl.Data.classes as classes
import AccessControl.Data.crud as crud
import AccessControl.Data.generators as gn
import AccessControl.Data.data_manipulation as dm
import AccessControl.Functions.matrix_functions as mx
import AccessControl.Data.enums as enums


ACCESS_EXPIRES = timedelta(hours=1)
_secret = config('FLASK_SECRET')

app = Flask(__name__)
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = _secret
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES
CORS(app)


def _get_person_picture(person):
    picture = crud.first_picture_person(person)
    return dm.img_bytes_to_base64(picture.picture_bytes)

def _get_person_vaccines(person):
    return [flatten(vaccine.to_dict()) for vaccine in crud.vaccines_by_person(person)]

def _get_employee_comments(employee):
    return [flatten(comment.to_dict()) for comment in crud.comments_by_employee(employee)]

def _set_appointment_status(appointment, status):
    appointment.status = status
    if status in {enums.AppointmentStatus.FINALIZED, enums.AppointmentStatus.REJECTED}:
        appointment.end = datetime.now()
    crud.commit()

@app.route('/persons', methods=['GET']) #
@jwt_required()
def list_persons():
    '''Returns all persons who are not employees'''
    json_data = [flatten(person.to_dict()) for person in crud.get_persons()]
    msg = '' if len(json_data) else 'No entries'
    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/employees', methods=['GET']) #
def list_employees():
    '''Returns all employees'''
    json_data = [flatten(employee.to_dict()) for employee in crud.get_employees()]
    msg = '' if len(json_data) else 'No entries'
    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/appointments', methods=['GET']) #
@jwt_required()
def list_appointments():
    '''Returns all appointments'''
    json_data = [flatten(appointment.to_dict()) for appointment in crud.get_entries(classes.Appointment)]
    msg = '' if len(json_data) else 'No entries'
    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/entries', methods=['GET']) #
@jwt_required()
def list_time_entries():
    '''Returns a list of all the entries'''
    json_data = [flatten(entry.to_dict(
            only=('id', 'action_type', 'action_time', 'person.full_name',
                  ))) for entry in crud.get_time_entries()]
    msg = '' if len(json_data) else 'No entries'
    return jsonify(result=json_data, msg=msg), HTTPStatus.OK

@app.route('/current-employee', methods=['GET']) #
@jwt_required()
def auth_employee_info():
    '''Returns the picture, and comment and vaccine list of the current employee'''
    id = get_jwt_identity()
    employee = crud.get_entry(classes.Employee, int(id))
    json_data = {}
    if employee:
        json_data['picture'] = _get_person_picture(employee.person)
        json_data['vaccines'] = _get_person_vaccines(employee.person)
        json_data['comments'] = _get_employee_comments(employee)
        json_data['employee'] = flatten(employee.to_dict())

    return jsonify(result=json_data), HTTPStatus.OK

@app.route('/person/<id>', methods=['GET']) #
@jwt_required()
def get_person_by_id(id):
    '''Returns the picture and vaccine list of a specific person given it's ID'''
    person = crud.get_person(int(id))
    json_data = {}
    msg = 'No entry with this ID'
    status = HTTPStatus.BAD_REQUEST
    if person:
        json_data['picture'] = _get_person_picture(person)
        json_data['vaccines'] = [flatten(vaccine.to_dict()) for vaccine in crud.vaccines_by_person(person)]
        msg = ''
        status = HTTPStatus.OK

    return jsonify(person=json_data, msg=msg), status

@app.route('/employee/<id>', methods=['GET', 'DELETE'])
@jwt_required()
def employee_methods(id):
    '''
    GET: Returns the picture, vaccine list and comment list of a specific employe given it's ID
    DELETE: Deletes employee
    '''
    if request.method == 'GET':
        employee = crud.get_employee(int(id))
        json_data = {}
        msg = 'No entry with this ID'
        status = HTTPStatus.BAD_REQUEST
        if employee:
            json_data['picture'] = _get_person_picture(employee.person)
            json_data['vaccines'] = _get_person_vaccines(employee.person)
            json_data['comments'] = _get_employee_comments(employee)
            msg = ''
            status = HTTPStatus.OK
        return jsonify(result=json_data, msg=msg), status
    else:
        crud.delete_entry(classes.Person, int(id))
        return jsonify(msg='Employee deleted successfully'), HTTPStatus.OK

@app.route('/employee/<id>/weekly-payment/<year_week>', methods=['GET'])
@jwt_required()
def weekly_payment(id, year_week):
    '''
    GET: Returns data regarding entries on a week, as well as calculated payment
    '''
    employee_id = int(id)
    employee = crud.get_employee(employee_id)
    year, week = [int(data) for data in year_week.split('-W')]
    json_data = {}
    data = crud.get_week_work_hours(year, week, employee)

    week_time = 0
    date_entries = []
    for day, (day_entries, time) in data.items():
        time = round(time,2)
        week_time += time
        json_entries = {
            'date': day,
            'hours': time,
            'wage': f'{round(time * employee.hourly_wage, 2)}$',
            'holiday': time == crud.REGULAR_WORK_HOURS and not day_entries,
            'entries': [
                flatten(
                    entry.to_dict(only=('id', 'action_type', 'action_time'))
                )
                for entry in day_entries[::-1]
            ],
        }

        date_entries.append(json_entries)

    json_data['week_time'] = week_time
    json_data['week_wage'] = f'{round(week_time * employee.hourly_wage, 2)}$'
    json_data['week_entries'] = date_entries
    json_data['picture'] = _get_person_picture(employee.person)
    json_data['employee'] = flatten(employee.to_dict())


    msg = 'Good'
    status = HTTPStatus.OK

    return jsonify(result=json_data, msg=msg), status

@app.route('/appointment/<id>', methods=['GET'])
def get_appointment_by_id(id):
    '''Returns appointment data regarding the person who made the appointment'''
    appointment = crud.get_entry(classes.Appointment, int(id))
    json_data = {}
    msg = 'No entry with this ID'
    status = HTTPStatus.BAD_REQUEST
    if appointment:
        person = appointment.person
        json_data['picture'] = _get_person_picture(person)
        json_data['person'] = flatten(person.to_dict())
        json_data['vaccines'] = [flatten(vaccine.to_dict()) for vaccine in crud.vaccines_by_person(person)]
        msg = ''
        status = HTTPStatus.OK
    return jsonify(result=json_data, msg=msg), status

@app.route('/entry/<id>', methods=['GET'])
@jwt_required()
def get_picture_entry_by_id(id):
    '''Returns the picture of a specific entry given it's ID'''
    entry = crud.get_entry(classes.Time_Entry, int(id))
    msg = 'No entry with this ID'
    status = HTTPStatus.BAD_REQUEST
    json_data = {}
    if entry:
        json_data['picture'] = dm.img_bytes_to_base64(entry.picture.picture_bytes)
        msg = ''
        status = HTTPStatus.OK
    return jsonify(result=json_data, msg=msg), status

@app.route('/person-doc/<identification_doc>', methods=['GET'])
def person_by_identdoc(identification_doc):
    '''Returns list of all the vaccines of a specific person given the identification_document number'''
    person = crud.person_by_ident_doc(identification_doc)
    msg = 'No person with this identification document'
    status = HTTPStatus.BAD_REQUEST
    json_data = {}
    if person:
        json_data['person'] = [flatten(person.to_dict())]
        json_data['vaccines'] = [flatten(vaccine.to_dict()) for vaccine in crud.vaccines_by_person(person)]
        msg = ''
        status = HTTPStatus.OK

    return jsonify(result=json_data, msg=msg), status

@app.route('/appointment-status', methods=['PATCH'])
@jwt_required()
def set_appointment_status():
    '''Sets the status of a specified appointment'''
    data = request.get_json(force=True)
    msg = 'Error with data sent'
    status = HTTPStatus.BAD_REQUEST
    if data:
        appointment = crud.get_entry(classes.Appointment, int(data['id']))
        appointment_status = enums.AppointmentStatus(int(data['status']))
        if appointment:
            _set_appointment_status(appointment, appointment_status)
            msg = 'Status set successfully'
            status = HTTPStatus.OK
        else:
            msg = 'No appointment with that ID'
    return jsonify(msg=msg), status

@app.route('/new-password', methods=['PATCH'])
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
                elif not password or not confirm_password:
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

@app.route('/employee', methods=['POST'])
@jwt_required()
def add_employee():
    '''Receives employee data and inserts it to the database'''
    data = request.get_json(force=True)
    msg = 'No correct data'
    status = HTTPStatus.BAD_REQUEST
    if data:
        error = False
        try:
            person, picture, vaccine_list, existent = gn.generate_person_picture_vaccines(data)
        except ValueError as e:
            msg = str(e)
            status = HTTPStatus.NOT_ACCEPTABLE
            error = True

        if not error:
            employee = gn.generate_employee(data, person, existent)

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
                crud.rollback()
    return jsonify(msg=msg), status

@app.route('/employees', methods=['POST'])
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

@app.route('/first-appointment', methods=['POST'])
def first_appointment():
    '''
    Recieves data regarding an appointment and creates one,
    also creating the person making the appointment and the picture of the person
    '''
    data = request.get_json(force=True)
    msg = 'No correct data'
    status = HTTPStatus.BAD_REQUEST
    if data:
        try:
            person, picture, vaccine_list, _ = gn.generate_person_picture_vaccines(
                data)
            employee_id = int(data['employee_id'])
            appointment = gn.generate_appointment(data, employee_id, person)
            if picture:
                crud.add_entry(appointment)
                crud.add_entry(picture)
                for vaccine in vaccine_list:
                    crud.add_entry(vaccine)
                msg = 'Appointment set successfully'
                status = HTTPStatus.OK
            else:
                msg = 'No correct picture'
                crud.rollback()
        except Exception as e:
            print(e)
            msg = 'Error setting appointment'

    return jsonify(msg=msg), status

@app.route('/new-appointment', methods=['POST'])
def new_appointment():
    '''
    Sets a new appointment
    '''
    data = request.get_json(force=True)
    msg = 'No correct data'
    status = HTTPStatus.BAD_REQUEST
    if data:
        appointment = gn.generate_appointment(data, int(data['employee_id']), crud.get_all(int(data['person_id'])))
        crud.add_entry(appointment)
        msg = 'Appointment set successfully'
        status = HTTPStatus.OK
    return jsonify(msg=msg), status

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    if data:
        try:
            employee = crud.get_entry(classes.Employee, int(data["id"]))
            password = data['password']
        except ValueError:
            employee = None

        access_token = ''
        # if there is no employee or the password is wrong, this will be the msg
        msg = 'Bad username or password'
        status = HTTPStatus.BAD_REQUEST
        if employee:
            if employee.password:
                if dm.compare_hash(password, employee.password):
                    access_token = create_access_token(identity=int(data["id"]))
                    status = HTTPStatus.OK
                    msg = 'Welcome'
            else:
                msg = 'There is no password set for this user'
                status = HTTPStatus.SEE_OTHER
    return jsonify(msg=msg, access_token=access_token), status

@app.route('/open-door', methods=['GET'])
@jwt_required()
async def openDoor():
    time_out = 10
    server = config('MATRIX_SERVER')
    user = config('MATRIX_USER')
    password = config('MATRIX_PASSWORD')
    device_id = config('MATRIX_DEVICE_ID_FACERECOG')
    door_room_name = config('MATRIX_ROOM_NAME_DOOR')
    try:
        client = await asyncio.wait_for(mx.matrix_login(server, user, password, device_id), time_out)
        door_room_id = await asyncio.wait_for(mx.matrix_get_room_id(client, door_room_name), time_out)
        message = '1'
        await asyncio.wait_for(mx.matrix_send_message(client, door_room_id, message), time_out)
        msg = 'Door oppened correctly'
        code = HTTPStatus.OK
        await asyncio.wait_for(mx.matrix_logout_close(client), time_out)
    except asyncio.TimeoutError:
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
        employee = crud.get_entry(classes.Employee, int(get_jwt_identity()))
        try:
            lab_num = int(data.get('dose_lab'))
        except ValueError:
            lab_num = -1
        dose_lab = enums.VaccineLab(lab_num) if lab_num > -1 else ""
        dose_date = data['dose_date']
        lot_num = data['lot_num']

        if dose_lab and dose_date and lot_num:
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
        employee = crud.get_entry(classes.Employee, int(get_jwt_identity()))
        comment_text = data['commentText']

        if comment_text:
            comment = classes.Comment(
                text=comment_text, employee=employee, timestamp=datetime.now())
            crud.add_entry(comment)
            msg = 'Comment Added Successfully'
            status = HTTPStatus.OK

    return jsonify(msg=msg), status

@app.route('/set-config', methods=['PATCH'])
# @jwt_required()
async def set_config():
    server = config('MATRIX_SERVER')
    user = config('MATRIX_USER')
    password = config('MATRIX_PASSWORD')
    device_id = config('MATRIX_DEVICE_ID_BACKEND')
    lang_room_name = config('MATRIX_ROOM_NAME_LANGUAGE')

    data = request.get_json(force=True)
    msg = 'Incorrect Data'
    status = HTTPStatus.BAD_REQUEST

    if data:
        start_time = data['start_time']
        end_time = data['end_time']
        profile = enums.PictureClassification(int(data['profile']))
        country = enums.CountryCodes(int(data['country']))

        configuration = crud.get_config()
        configuration.start_time = start_time
        configuration.end_time = end_time
        configuration.profile = profile
        configuration.country = country
        crud.commit()

        time_out = 20
        language = enums.SpeakerLanguages(int(data['language'])).name
        try:
            client = await asyncio.wait_for(
                mx.matrix_login(server, user, password, device_id), time_out)
            lang_room_id = await asyncio.wait_for(
                mx.matrix_get_room_id(client, lang_room_name), time_out)
            await asyncio.wait_for(
                mx.matrix_send_message(client, lang_room_id, language), time_out)
            await asyncio.wait_for(mx.matrix_logout_close(client), time_out)
            msg = 'Configuration Set Succesfully'
            code = HTTPStatus.OK
        except asyncio.TimeoutError:
            msg = 'Error Setting Configuration'
            code = HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(msg=msg), code


if __name__ == '__main__':
    import sys
    import argparse
    ap = argparse.ArgumentParser()

    ap.add_argument('--debug', action='store_true')
    args = vars(ap.parse_args())


    if args['debug']:
        app.run(host='0.0.0.0', debug=True)
    else:
        from gevent.pywsgi import WSGIServer
        http_server = WSGIServer(('', 5000), app)
        http_server.serve_forever()
