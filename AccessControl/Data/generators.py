import base64
import re
import io

from datetime import datetime

import AccessControl.Data.classes as classes
import AccessControl.Data.crud as crud
import AccessControl.Data.data_manipulation as dm
import AccessControl.Functions.matrix_functions as mx
import AccessControl.Data.enums as enums



def generate_person(data):
    identification_doc = re.sub('[^a-zA-Z0-9]', '', data['identification_doc'])
    first_name = data['first_name']
    last_name = data['last_name']
    cellphone = re.sub('[^a-zA-Z0-9]', '', data['cellphone'])
    role = enums.PersonRole(int(data.get('role', 0)))

    person = crud.person_by_ident_doc(identification_doc)
    existent = False
    if person:
        person = person
        if person.active:
            raise ValueError('The employee already exists')
        person.identification_document = identification_doc
        person.first_name = first_name
        person.last_name = last_name
        person.cellphone = cellphone
        person.role = role
        person.active = True
        existent = True
    else:
        person = classes.Person(identification_document=identification_doc,
                                first_name=first_name, last_name=last_name,
                                cellphone=cellphone, role=role)

    return person, existent

def generate_picture(data, person, existent):
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
    return picture

def generate_vaccines(data, person, picture):
    if not picture:
        return []
    vaccine_list = []

    for vac in crud.vaccines_by_person(person):
        crud.delete_entry(classes.Vaccine, vac.id)

    for i in range(1, 4):
        try:
            lab_num = int(data.get(f'dose_lab_{i}'))
        except ValueError:
            lab_num = -1

        dose_lab = enums.VaccineLab(lab_num) if lab_num > -1 else ""
        dose_date = data.get(f'dose_date_{i}')
        lot_num = data.get(f'lot_num_{i}')
        if dose_lab and dose_date and lot_num:
            vaccine = classes.Vaccine(
                dose_lab=dose_lab, dose_date=dose_date, lot_num=lot_num, person=person)
            vaccine_list.append(vaccine)

    return vaccine_list

def generate_employee(data, person, existent):
    position = data['position']
    start_date = data['start_date']
    email = data['email']
    birth_date = data['birth_date']
    hourly_wage = data['hourly_wage']
    password = data.get('password', '')
    password = dm.compute_hash(password) if password else password
    if existent:
        employee = crud.get_entry(
            classes.Employee, person.id, inactive=True)
        employee.email = email
        employee.birth_date = birth_date
        employee.position = position
        employee.start_date = start_date
        employee.password = password
        employee.hourly_wage = hourly_wage
    else:
        employee = classes.Employee(id=person.id, position=position, birth_date=birth_date,
                                    email=email, start_date=start_date, person=person,
                                    password=password, hourly_wage=hourly_wage)
    return employee

def generate_person_picture_vaccines(data):

    try:
        person, existent = generate_person(data)
    except ValueError as e:
        raise ValueError(str(e))

    picture = generate_picture(data, person, existent)
    vaccines = generate_vaccines(data, person, picture)

    return person, picture, vaccines, existent

def generate_appointment(data, employee_id, person):
    employee = crud.get_entry(classes.Employee, int(employee_id))

    # Appointment data
    date = data['appointment_date']
    time = data['appointment_time']
    full_date = f'{date} {time}:00'
    appointment_start = datetime.strptime(
        full_date, '%Y-%m-%d %H:%M:%S')
    return classes.Appointment(
        start=appointment_start,
        person=person, employee=employee)
