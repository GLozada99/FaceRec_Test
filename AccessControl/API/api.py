import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.crud as crud
import base64
from PIL import Image
import io
from flatten_json import flatten
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route('/list/persons', methods=['GET'])
def list_persons():
    all_persons = crud.get_entries(classes.Person)
    only_persons = [person for person in all_persons if not person.is_employee]
    json_persons = []
    for dat in only_persons:
        json_persons.append(dat.to_dict(
            only=('id', 'first_name', 'last_name', 'identification_document', 'birth_date')))

    return jsonify(json_persons)

@app.route('/list/employees', methods=['GET'])
def list_employees():
    data = crud.get_entries(classes.Employee)
    json_employees = []

    for dat in data:
        print(dat.person)
        json_employees.append(flatten(dat.to_dict(
            only=('id', 'person.first_name', 'person.last_name',
                  'person.identification_document', 'person.birth_date',
                  'position', 'salary', 'email', 'start_date'))))

    print(json_employees)
    return jsonify(json_employees)

@app.route('/regist/employees', methods=['POST'])
def regist_employees():
    data = request.get_json(force=True)
    if data:
        #Person data
        identification_doc = data['identification_doc']
        first_name = data['first_name']
        last_name = data['last_name']
        birth_date = data['birth_date']
        person = classes.Person(identification_document=identification_doc,
                                first_name=first_name, last_name=last_name, 
                                birth_date=birth_date, is_employee=True)
        # Empleado
        position = data['position']
        salary = data['salary']
        email = data['email']
        start_date = data['start_date']
        
        employee = classes.Employee(id=person.id, position=position,
            salary=salary, email=email, start_date=start_date, person=person)
        
        #Picture data
        # Developer        |  50000 | wdiaz@devland.com | 2019-05-18
        # 5 | 412-9999999-8           | Waldry     | Diaz      | 1996-05-10 | t           | t

        base64_pics = data['pictures']
        picture_list = []
        for base64_pic in base64_pics:
            pic_bytes = base64.b64decode(base64_pic.split(",")[1])
            pic_io = io.BytesIO(pic_bytes)
            picture_data_constructor = dm.process_picture_file(pic_io)
            if picture_data_constructor:
                raw_bin_pic, face_encoding = picture_data_constructor
                picture = classes.Picture(person_id=person.id,
                                          picture_bytes=raw_bin_pic,
                                          face_bytes=face_encoding,
                                          person=person)
                picture_list.append(picture)
            else:
                print('This picture does not contains a face')
        
        if picture_list:
            crud.add_entry(employee)
            for picture in picture_list:
                crud.add_entry(picture)

    return {'Name': 'Gus'}
    if data:
    # Persona
        identification_doc = data['identification_doc']
        first_name = data['first_name']
        last_name = data['last_name']
        birth_date = data['birth_date']

        # Empleado
        position = data['position']
        salary = data['salary']
        email = data['email']
        start_date = data['start_date']

        # Foto
        # image = request.files['picture']
        # image_data = image.read()
        # bytes, encoding = dm.process_picture_file(image_data)

        # Aqui no se si tomar el archivo y convertirlo a bytes o se hace en otro lado

        person = classes.Person(identification_document=identification_doc, first_name=first_name,
                                last_name=last_name, birth_date=birth_date, is_employee=True)
        # crud.add_entry(person)
        employee = classes.Employee(
            id=person.id, position=position,
            salary=salary, email=email, start_date=start_date, person=person)
        print(employee, person)
        #crud.add_entry(employee)

@app.route('/regist/persons', methods=['POST'])
def regist_persons():
    data = request.get_json(force=True)
    if data:
    # Persona
        identification_doc = data['identification_doc']
        first_name = data['first_name']
        last_name = data['last_name']
        birth_date = data['birth_date']
        # Foto
        # image = request.files['picture']
        # image_data = image.read()
        # bytes, encoding = dm.process_picture_file(image_data)

        person = classes.Person(identification_document=identification_doc, first_name=first_name,
                                last_name=last_name, birth_date=birth_date, is_employee=True)
        #crud.add_entry(person)


@app.route('/vaccine/regist', methods=['POST', 'GET'])
def vacuna():
    vacc = None
    if request.method == 'POST':
        person_id = request.form['person_id']
        dose_type = request.form['dose_type']
        dose_date = request.form['dose_date']

        vacc = classes.Vaccine(person_id, dose_type, dose_date)

    crud.add_entry(vacc)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
