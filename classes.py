import sqlalchemy, os
from sqlalchemy.ext.declarative import declarative_base

#setting up parameters
_user = os.environ.get('MARIADB_USER')
_password =  os.environ.get('MARIADB_PASSWORD')
_host = '127.0.0.1'
_port = '3306'
_database = 'Face_Recognition'


#getting engine
engine = sqlalchemy.create_engine(f'mariadb+mariadbconnector://{_user}:{_password}@{_host}:{_port}/{_database}')

#getting base for classes
Base = declarative_base()

#creating clases

class Person(Base):
    __tablename__ = 'persons'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    identification_document = sqlalchemy.Column(sqlalchemy.String(length=20), unique=True)
    first_name = sqlalchemy.Column(sqlalchemy.String(length=30))
    last_name = sqlalchemy.Column(sqlalchemy.String(length=30))
    birth_date = sqlalchemy.Column(sqlalchemy.Date)
    is_employee = sqlalchemy.Column(sqlalchemy.Boolean)
    active = sqlalchemy.Column(sqlalchemy.Boolean)
    
    employee = sqlalchemy.orm.relationship("Employee", back_populates="person")
    pictures = sqlalchemy.orm.relationship("Picture", back_populates="person")
    vaccines = sqlalchemy.orm.relationship("Vaccine", back_populates="person")
    time_entries = sqlalchemy.orm.relationship("Time_Entry", back_populates="person")
    

class Employee(Base):
    __tablename__ = 'employees'
    id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'), primary_key=True)
    position = sqlalchemy.Column(sqlalchemy.String(length=30))
    salary = sqlalchemy.Column(sqlalchemy.Float)
    email = sqlalchemy.Column(sqlalchemy.String(length=30))
    start_date = sqlalchemy.Column(sqlalchemy.Date)
    vacations_since = sqlalchemy.Column(sqlalchemy.Date) 

    person = sqlalchemy.orm.relationship("Person", back_populates="employee")
    #Sintomas y lo demas referente a enfermedades y/o covid pendiente
    
class Picture(Base):
    __tablename__ = 'pictures'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    person_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    picture_bytes = sqlalchemy.Column(sqlalchemy.dialects.mysql.LONGBLOB)
    face_bytes = sqlalchemy.Column(sqlalchemy.dialects.mysql.LONGBLOB)
    
    person = sqlalchemy.orm.relationship("Person", back_populates="pictures")

class Vaccine(Base):
    __tablename__ = 'vaccines'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    person_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    dose_type = sqlalchemy.Column(sqlalchemy.String(length=30))
    dose_date = sqlalchemy.Column(sqlalchemy.Date)

    person = sqlalchemy.orm.relationship("Person", back_populates="vaccines")

class Time_Entry(Base):
    __tablename__ = 'time_entries'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    person_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    action = sqlalchemy.Column(sqlalchemy.String(length=7)) #entrada o salida
    action_time = sqlalchemy.Column(sqlalchemy.DateTime) #sea entrada o salida, tendra la hora de este

    person = sqlalchemy.orm.relationship("Person", back_populates="time_entries")

if __name__ == '__main__':
    #when runned as file, it'll to create all clases as tables on the database
    Base.metadata.create_all(engine)
    # import datetime, crud
    # per = Person(identification_document='001-1-0', first_name='Gus', last_name='Loz', birth_date=datetime.datetime.now(), is_employee=True, active=True )
    # crud.add_entry(per)
    # vac = Vaccine(person_id=1,dose_type='Pfizer2',dose_date=datetime.datetime.now())
    # crud.add_entry(vac)


