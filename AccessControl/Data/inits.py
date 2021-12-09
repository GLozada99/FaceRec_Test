import csv
import sys
import AccessControl.Data.crud as crud
import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.enums as enums

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
    for i in range(2):
        ip = config(f'CAMERA_{i}_IP')
        user = config(f'CAMERA_{i}_USER')
        password = config(f'CAMERA_{i}_PASSWORD')
        route = config(f'CAMERA_{i}_ROUTE')
        entry_type = enums.EntryTypes(int(config(f'CAMERA_{i}_EntryType')))

        camera = classes.Camera(
            ip_address=ip, user=user,
            password=password, route=route,
            entry_type=entry_type)
        crud.add_entry(camera)
