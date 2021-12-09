import csv
import sys
import AccessControl.Data.crud as crud
import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.enums as enums
from decouple import config
from AccessControl.API.api import _generate_person_picture_vaccines


def admin_init():
    maxInt = sys.maxsize
    try:
        csv.field_size_limit(maxInt)
    except OverflowError:
        maxInt = int(maxInt / 10)

    with open('./employees.csv') as file:
        reader = csv.DictReader(file)
        for row in reader:
            person, picture, vaccine_list, _ = _generate_person_picture_vaccines(
                row)
            person.role = enums.PersonRole(int(row['role']))

            # Employee data
            position = row['position']
            start_date = row['start_date']
            password = dm.compute_hash(row['password'])
            employee = classes.Employee(
                position=position, start_date=start_date,
                password=password, person=person)

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

    with open('./cameras.csv') as file:
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
