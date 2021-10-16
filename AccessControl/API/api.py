import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.crud as crud
import requests
import argparse
import base64
import os
import io
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
from flatten_json import flatten
from flask_cors import CORS
from icecream import ic

ACCESS_EXPIRES = timedelta(hours=1)
_secret = os.environ.get('SECRET')

app = Flask(__name__)
jwt = JWTManager(app)
app.config["JWT_SECRET_KEY"] = _secret
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = ACCESS_EXPIRES
CORS(app)

def _generate_person_picture_vaccines(data):
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

    return (person, picture, vaccine_list)

@app.route('/list/persons', methods=['GET'])
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

    return jsonify(json_data)

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

@app.route('/list/entries', methods=['GET'])
@jwt_required()
def list_time_entries():
    '''Returns a list of all the entries'''
    data = crud.get_entries(classes.Time_Entry)
    json_data = []
    for dat in data:
        json_data.append(flatten(dat.to_dict(
            only=('id', 'action', 'action_time', 'person.id', 'person.first_name', 'person.last_name',
                  ))))

    return jsonify(json_data)

@app.route('/info/person', methods=['POST'])
@jwt_required()
def person_by_id():
    '''Returns the picture and vaccine list of a specific person given it's ID'''
    data = request.get_json(force=True)
    if data:
        id = data["id"]
        person = crud.get_entry(classes.Person, id)
        print(person)
        json_data = []
        if person:
            first_picture = crud.pictures_by_person(person)[0]
            pic = dm.img_bytes_to_base64(first_picture.picture_bytes)
            json_data.append({"picture": pic})

            vaccines = crud.vaccines_by_person(person)

            for vaccine in vaccines:
                json_data.append(flatten(vaccine.to_dict(only=("dose_lab", "dose_date", "lot_num"))))

            pic_sp = 1
            vac_sp = 2
            json_data.insert(0, {"pic_sp": pic_sp, "vac_sp": vac_sp})
        return jsonify(json_data)

@app.route('/info/entry', methods=['POST'])
@jwt_required()
def entry_by_id():
    '''Returns the picture of a specific entry given it's ID'''
    data = request.get_json(force=True)
    if data:
        id = data["id"]
        entry = crud.get_entry(classes.Time_Entry, id)
        json_data = []
        if entry:
            picture = entry.picture
            pic = dm.img_bytes_to_base64(picture.picture_bytes)
            json_data.append({"picture": pic})
        return jsonify(json_data)

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

@app.route('/regist/employee', methods=['POST'])
@jwt_required()
def regist_employees():
    '''Receives employee data and inserts it to the database'''
    data = request.get_json(force=True)
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
            return jsonify(success=True), 201

    return jsonify(msg="No correct picture"), 401

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
            for data in final_data:
                requests.post('http://localhost:5000/regist/employee', json=data)
            else:
                return jsonify(success=True), 201

        return jsonify(msg="Errors in the file"), 401

@app.route('/appointment', methods=['POST'])
def make_appointment():
    '''
    Recieves data regarding an appointment and creates one,
    also creating the person making the appointment and the picture of the person
    '''
    data = request.get_json(force=True)
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
            return jsonify(success=True), 201

    return jsonify(msg="No correct picture"), 401

@app.route('/password/first', methods=['POST'])
def set_first_password():
    '''
    Sets a first password for an account given the id
    '''
    data = request.get_json(force=True)
    if data:
        id = data['id']
        password = data['password']
        employee = crud.get_entry(classes.Employee, id)
        msg = ''
        if employee:
            if not employee.password:
                hashed_password = dm.compute_hash(password)
                employee.password = hashed_password
                crud.update_entry(classes.Employee, employee)
                return jsonify(success=True), 201
            msg = 'The account already has a password'
        msg = 'No employee with this ID'

        return jsonify(msg=msg)

@app.route('/password/new', methods=['POST'])
def set_password():
    '''
    Sets a new password for an account given the id
    '''
    data = request.get_json(force=True)
    if data:
        id = data['id']
        password = data['password']
        employee = crud.get_entry(classes.Employee, id)
        msg = ''
        if employee:
            hashed_password = dm.compute_hash(password)
            employee.password = hashed_password
            crud.update_entry(classes.Employee, employee)
            return jsonify(success=True), 201
        msg = 'No employee with this ID'

        return jsonify(msg=msg), 401

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    if data:
        id = data['userId']
        password = data['password']
        employee = crud.get_entry(classes.Employee, id)
        if employee:
            if employee.password:
                if dm.compare_hash(password, employee.password):
                    access_token = create_access_token(identity=id)
                    return jsonify(access_token=access_token)

    return jsonify(msg='Bad username or password'), 401

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

    return jsonify(username=username, is_admin=is_admin, id=current_user_id), 200

@app.route('/vaccine/regist', methods=['POST', 'GET'])
def vaccine():
    vacc = None
    if request.method == 'POST':
        person_id = request.form['person_id']
        dose_type = request.form['dose_type']
        dose_date = request.form['dose_date']

        vacc = classes.Vaccine(person_id, dose_type, dose_date)

    crud.add_entry(vacc)
