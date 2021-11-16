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
            person, picture, vaccine_list, _ = _generate_person_picture_vaccines(row)
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
