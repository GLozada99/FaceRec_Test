import csv
import sys
import requests
import traceback
import AccessControl.Data.crud as crud
import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.generators as gn
import AccessControl.Data.enums as enums
import base64

from decouple import config


auth = None

maxInt = sys.maxsize
try:
    csv.field_size_limit(maxInt)
except OverflowError:
    maxInt = int(maxInt / 10)

def admin_init():
    with open('./CSVs/admin.csv') as file:
        reader = csv.DictReader(file)
        for row in reader:
            person, picture, vaccine_list, _ = gn.generate_person_picture_vaccines(
                row)
            employee = gn.generate_employee(row, person, False)
            if picture:
                crud.add_entry(employee)
                crud.add_entry(picture)
                for vaccine in vaccine_list:
                    crud.add_entry(vaccine)
    return employee.id, row['password']

def camera_init():
    camera = classes.Camera(
        ip_address="0.0.0.0", user="admin", password="admin",
        route="/", entry_type=enums.EntryTypes(2),
        ask_mask=True, ask_temp=True)
    crud.add_entry(camera)

    with open('./CSVs/cameras.csv') as file:
        reader = csv.DictReader(file)
        for row in reader:
            ip = row['ip']
            user = row['user']
            password = row['password']
            route = row['route']
            entry_type = enums.EntryTypes(int(row['entry_type']))
            ask_mask = bool(int(row['ask_mask']))
            ask_temp = bool(int(row['ask_temp']))

            camera = classes.Camera(
                ip_address=ip, user=user, password=password,
                route=route, entry_type=entry_type,
                ask_mask=ask_mask, ask_temp=ask_temp)
            crud.add_entry(camera)


def employees_init():
    with open('./CSVs/employees.csv','rb') as file:
        data = file.read()
    base64_doc = base64.b64encode(data).decode('utf-8')
    requests.post('http://localhost:5000/employees', json={"base64_doc": base64_doc}, headers={'Authorization': f'Bearer {auth}'})


def appointment_init():
    with open('./CSVs/appointments.csv') as file:
        reader = csv.DictReader(file)
        for row in reader:
            requests.post('http://localhost:5000/first-appointment', json=row)

def init():
    try:
        print('camera...')
        camera_init()
        print('admin...')
        emp_id, password = admin_init()
        print('login...')
        response = requests.post('http://localhost:5000/login', json={'id': emp_id, 'password': password})

        global auth
        auth = response.json()['access_token']

        print('employee...')
        employees_init()
        print('appointment...')
        appointment_init()
    except Exception as e:
        traceback.print_exc()
