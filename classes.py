import sqlalchemy, os
from sqlalchemy.ext.declarative import declarative_base

#setting up parameters
_user = os.environ.get('MARIADB_USER')
_password =  os.environ.get('MARIADB_PASSWORD')
_host = '127.0.0.1'
_port = '3306'
_database = 'FaceRecog'


#getting engine
engine = sqlalchemy.create_engine(f'mariadb+mariadbconnector://{_user}:{_password}@{_host}:{_port}/{_database}')

#getting base for classes
Base = declarative_base()

#creating clases
class Picture(Base):
    __tablename__ = 'pictures2'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(length=30))
    picture_bytes = sqlalchemy.Column(sqlalchemy.dialects.mysql.LONGBLOB)
    face_bytes = sqlalchemy.Column(sqlalchemy.dialects.mysql.LONGBLOB)

class Employee(Base):
    __tablename__ = 'empleado'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    first_name = sqlalchemy.Column(sqlalchemy.String(length=40))
    last_name = sqlalchemy.Column(sqlalchemy.String(length=50))
    cedula = sqlalchemy.Column(sqlalchemy.String(length=13))
    vacations_since = sqlalchemy.Column(sqlalchemy.DateTime) #tambien hacer una de tiempo de licencia
    active = sqlalchemy.Column(sqlalchemy.Boolean) 
    #Sintomas y lo demas referente a enfermedades y/o covid pendiente

class Tarjeta_vacuna(Base):
    __tablename__ = 'vacuna'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    cedula_employee = sqlalchemy.Column(sqlalchemy.Integer)
    first_dose_date = sqlalchemy.Column(sqlalchemy.DateTime)
    second_dose_date = sqlalchemy.Column(sqlalchemy.DateTime)

class Poncheo(Base):
    __tablename__ = 'poncheo'
    id_empleado = sqlalchemy.Column(sqlalchemy.Integer)
    action = sqlalchemy.Column(sqlalchemy.String(length=7)) #entrada o salida
    time_action = sqlalchemy.Column(sqlalchemy.DateTime) #sea entrada o salida, tendra la hora de este


if __name__ == '__main__':
    #when runned as file, it'll to create all clases as tables on the database
    Base.metadata.create_all(engine)


