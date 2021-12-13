import csv
import sys
import AccessControl.Data.crud as crud
import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.enums as enums
from decouple import config
import AccessControl.Data.generators as gn


def employee_init():
    maxInt = sys.maxsize
    try:
        csv.field_size_limit(maxInt)
    except OverflowError:
        maxInt = int(maxInt / 10)

    with open('./CSVs/employees.csv') as file:
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

def person_init():
    maxInt = sys.maxsize
    try:
        csv.field_size_limit(maxInt)
    except OverflowError:
        maxInt = int(maxInt / 10)

    with open('./CSVs/persons.csv') as file:
        reader = csv.DictReader(file)
        for row in reader:
            person, picture, vaccine_list, _ = gn.generate_person_picture_vaccines(
                row)
            if picture:
                crud.add_entry(person)
                crud.add_entry(picture)
                for vaccine in vaccine_list:
                    crud.add_entry(vaccine)

def appointment_init():
    maxInt = sys.maxsize
    try:
        csv.field_size_limit(maxInt)
    except OverflowError:
        maxInt = int(maxInt / 10)

    with open('./CSVs/appointments.csv') as file:
        reader = csv.DictReader(file)
        for row in reader:
            person_id = int(row['person_id'])
            employee_id = int(row['employee_id'])
            appointment = gn.generate_appointment(row, employee_id, crud.get_person(person_id))
            crud.add_entry(appointment)
