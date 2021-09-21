from datetime import datetime, timedelta
import sqlalchemy
import os
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_serializer import SerializerMixin

# setting up parameters
_user = os.environ.get('MARIADB_USER')
_password = os.environ.get('MARIADB_PASSWORD')
_host = '127.0.0.1'
_port = '5432'  # database port
_database = 'face_recognition'


# getting engine
engine = sqlalchemy.create_engine(
    f'postgresql+psycopg2://{_user}:{_password}@{_host}:{_port}/{_database}')

# getting base for classes
Base = declarative_base()

# creating clases

class Person(Base, SerializerMixin):
    __tablename__ = 'persons'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    identification_document = sqlalchemy.Column(
        sqlalchemy.String(length=20), unique=True)
    first_name = sqlalchemy.Column(sqlalchemy.String(length=30))
    last_name = sqlalchemy.Column(sqlalchemy.String(length=30))
    birth_date = sqlalchemy.Column(sqlalchemy.Date)
    email = sqlalchemy.Column(sqlalchemy.String(length=30))
    is_employee = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    active = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    employee = sqlalchemy.orm.relationship(
        "Employee", back_populates="person", uselist=False)
    pictures = sqlalchemy.orm.relationship("Picture", back_populates="person")
    appointments = sqlalchemy.orm.relationship("Appointment", back_populates="person")
    vaccines = sqlalchemy.orm.relationship("Vaccine", back_populates="person")
    time_entries = sqlalchemy.orm.relationship(
        "Time_Entry", back_populates="person")

    def __str__(self):
        return f'Person... id: {self.id}, name: {self.first_name} {self.last_name}'


class Employee(Base, SerializerMixin):
    __tablename__ = 'employees'
    id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(
        'persons.id'), primary_key=True)
    position = sqlalchemy.Column(sqlalchemy.String(length=30))
    start_date = sqlalchemy.Column(sqlalchemy.Date)
    # salary = sqlalchemy.Column(sqlalchemy.Float)

    person = sqlalchemy.orm.relationship("Person", back_populates="employee")
    appointments = sqlalchemy.orm.relationship("Appointment", back_populates="employee")
    comments = sqlalchemy.orm.relationship("Comment", back_populates="employee")

    # Sintomas y lo demas referente a enfermedades y/o covid pendiente
    def __str__(self):
        return f'Employee... id: {self.id}, name: {self.person.first_name} {self.person.last_name}'


class Picture(Base, SerializerMixin):
    __tablename__ = 'pictures'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    picture_bytes = sqlalchemy.Column(sqlalchemy.dialects.postgresql.BYTEA)
    face_bytes = sqlalchemy.Column(sqlalchemy.dialects.postgresql.BYTEA)

    person_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    # time_entry_id = sqlalchemy.Column(
    #     sqlalchemy.Integer, sqlalchemy.ForeignKey('time_entries.id'))

    person = sqlalchemy.orm.relationship("Person", back_populates="pictures")
    time_entry = sqlalchemy.orm.relationship(
        "Time_Entry", back_populates="picture", uselist=False)
    
    def __str__(self):
        return f'Picture... id: {self.id}, person name: {self.person.first_name} {self.person.last_name}'


class Vaccine(Base, SerializerMixin):
    __tablename__ = 'vaccines'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    person_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    dose_lab = sqlalchemy.Column(sqlalchemy.String(length=30))
    lot_num = sqlalchemy.Column(sqlalchemy.String(length=20))
    dose_date = sqlalchemy.Column(sqlalchemy.Date)

    person = sqlalchemy.orm.relationship("Person", back_populates="vaccines")

    def __str__(self):
        return f'Vaccine... id: {self.id}, person name: {self.person.first_name} \
            lab: {self.dose_lab} date:{self.dose_date}'

class Time_Entry(Base, SerializerMixin):
    __tablename__ = 'time_entries'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    person_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    picture_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('pictures.id'))
    action = sqlalchemy.Column(sqlalchemy.String(length=7))  # entrada o salida
    # sea entrada o salida, tendra la hora de este
    action_time = sqlalchemy.Column(sqlalchemy.DateTime)

    person = sqlalchemy.orm.relationship(
        "Person", back_populates="time_entries")
    picture = sqlalchemy.orm.relationship(
        "Picture", back_populates="time_entry")

    def __str__(self):
        return f'Time Entry... id: {self.id}, person name: {self.person.first_name} \
            action: {self.action} time:{self.action_time}'

class Appointment(Base, SerializerMixin):
    __tablename__ = 'appointments'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    appointment_start = sqlalchemy.Column(sqlalchemy.DateTime)
    appointment_end = sqlalchemy.Column(sqlalchemy.DateTime)
    accepted = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    accomplished = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

    person_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    employee_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('employees.id'))

    person = sqlalchemy.orm.relationship(
        "Person", back_populates="appointments")
    employee = sqlalchemy.orm.relationship(
        "Employee", back_populates="appointments")

class Comment(Base, SerializerMixin):
    __tablename__ = 'comments'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    timestamp = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.now())
    text = sqlalchemy.Column(sqlalchemy.String(length=250))
    employee_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('employees.id'))

    employee = sqlalchemy.orm.relationship(
        "Employee", back_populates="comments")


if __name__ == '__main__':
    # when runned as file, it'll to create all clases as tables on the database
    Base.metadata.create_all(engine)

    # import datetime
    # import AccessControl.Data.crud as crud
    # per = Person(identification_document='402-1383575-0',
    #              first_name='Gustavo', last_name='Lozada',
    #              birth_date=datetime.datetime(1999, 10, 9))
    # crud.add_entry(per)

    # vac = Vaccine(dose_lab='Pfizer2', lot_num='545',
    #               dose_date=datetime.datetime.now(), person=per)
    # crud.add_entry(vac)
    # per = Person(identification_document='412-6483594-8',
    #              first_name='Diogenes', last_name='Vargas',
    #              birth_date=datetime.datetime(1999, 3, 19))
    # crud.add_entry(per)

    # per = Person(identification_document='412-4597816-8',
    #              first_name='David', last_name='Vazquez',
    #              birth_date=datetime.datetime(1999, 7, 22))
    # crud.add_entry(per)

    # per = Person(identification_document='412-9999999-8',
    #              first_name='Waldry', last_name='Diaz',
    #              birth_date=datetime.datetime(1996, 5, 10), is_employee=True)
    # emp = Employee(position='Developer', salary=50000,
    #                email="wdiaz@devland.com",
    #                start_date=datetime.datetime(2019, 5, 18),
    #                person=per)
    # crud.add_entry(emp)

    # position = sqlalchemy.Column(sqlalchemy.String(length=30))
    # salary = sqlalchemy.Column(sqlalchemy.Float)
    # email = sqlalchemy.Column(sqlalchemy.String(length=30))
    # start_date = sqlalchemy.Column(sqlalchemy.Date)
    # vacations_since = sqlalchemy.Column(sqlalchemy.Date)

    # person = sqlalchemy.orm.
