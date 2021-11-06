import csv
import AccessControl.Data.crud as crud
import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes

from AccessControl.API.api import _generate_person_picture_vaccines

def admin_init():
    with open('./employees.csv') as file:
        reader = csv.DictReader(file)
        for row in reader:
            person, picture, vaccine_list = _generate_person_picture_vaccines(row)
            person.role = classes.Role.SUPER_ADMIN
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
