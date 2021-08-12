import AccessControl.Data.data_manipulation as dm
import AccessControl.Data.classes as classes
import AccessControl.Data.crud as crud

import requests, json, base64
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
@app.route("/list")
def api_prueba():
    persons = crud.get_entries(classes.Person)
    json_persons = []
    for per in persons:
        json_persons.append(classes.as_dict(per))
    
    return jsonify(json_persons)
    
@app.route("/person/regist", methods=['POST', 'GET'])
def api_reg():
    person = None
    pict = None
    if request.method == 'POST':
        #Persona
        identification_doc = request.form['identification_doc']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        birth_date = request.form['birth_date']
        is_employee = request.form['is_employee']
        
        #Foto
        image = request.files['picture']
        image_data = image.read()
        bytes, encoding = dm.process_picture_file(pic_data)

        #Aqui no se si tomar el archivo y convertirlo a bytes o se hace en otro lado
        
        person = classes.Person(identifiacion_document = identification_doc, first_name = first_name, last_name = last_name, birth_date = birth_date, is_employee = is_employee)
        crud.add_entry(person)

        if is_employee == True:
            #Empleado
            position = request.form['position']
            salary = request.form['salary']
            email = request.form['email']
            start_date = request.form['start_date']

            employee = classes.Employee(id = person.id, position = position, salary = salary, email = email, start_date = start_date)
            crud.add_entry(employee)

        pict = classes.Picture(id = person.id, picture_bytes = '', face_bytes = '') #Valores pendientes
        crud.add_entry(pict)

        if request.form['agregar_v4cun4']:
            person_id = person.id
            vaccines = request.form['vaccines']


@app.route("/vaccine/regist", methods=['POST', 'GET'])
def vacuna():
    vacc = None
    if request.method == 'POST':
        person_id = request.form['person_id']
        dose_type = request.form['dose_type']
        dose_date = request.form['dose_date']

        vacc = classes.Vaccine(person_id, dose_type, dose_date)
    
    crud.add_entry(vacc)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
    

