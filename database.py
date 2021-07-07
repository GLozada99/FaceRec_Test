import mariadb
import sys
from os import environ
import numpy

def connect():
    try:
        db_conn = mariadb.connect(
        user=environ.get('MARIADB_USER'),
        password=environ.get('MARIADB_PASSWORD'),
        host='localhost',
        port=3306,
        database='FaceRecog'
        )
        return db_conn
    except mariadb.Error as e:
        print(f'Error al conectar a la base de datos: {e}')
        sys.exit(1)

def insert_code(connection, raw_name, raw_image, face_bytes):
    name, raw_num = raw_name.split('_')
    num = raw_num.split('.')[0]
    cursor = connection.cursor()
    cursor.execute(
    'INSERT INTO pictures(Person_Name, Number, Bytes, Encoding) VALUES (?, ?, ?, ?)',(name, num, raw_image,face_bytes))
    connection.commit()

def get_encondings(connection):
    connection = connect()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM pictures')
    data = cursor.fetchall()
    return data




