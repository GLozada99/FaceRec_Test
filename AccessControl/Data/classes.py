import os
from datetime import datetime, timedelta
from decouple import config

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_serializer import SerializerMixin
import AccessControl.Data.enums as enums

# setting up parameters
_user = config('DB_USER')
_password = config('DB_PASSWORD')
_host = '127.0.0.1'
_port = '5432'  # database port
_database = config('DB_NAME')


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
    cellphone = sqlalchemy.Column(sqlalchemy.String(length=20))
    role = sqlalchemy.Column(sqlalchemy.Enum(enums.PersonRole))
    active = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    serialize_rules = ('-employee','-pictures',
                       '-appointments','-vaccines',
                       '-time_entries','get_role', '-role','full_name')

    employee = sqlalchemy.orm.relationship(
        "Employee", back_populates="person")
    pictures = sqlalchemy.orm.relationship("Picture", back_populates="person")
    appointments = sqlalchemy.orm.relationship(
        "Appointment", back_populates="person")
    vaccines = sqlalchemy.orm.relationship("Vaccine", back_populates="person")
    time_entries = sqlalchemy.orm.relationship(
        "Time_Entry", back_populates="person")

    def __str__(self) -> str:
        return f'Person... id: {self.id}, name: {self.first_name} {self.last_name}'

    def get_role(self):
        return {"name":self.role.name, "value": self.role.value}

    def full_name(self) ->str:
        return f'{self.first_name} {self.last_name}'


class Employee(Base, SerializerMixin):
    __tablename__ = 'employees'
    id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(
        'persons.id'), primary_key=True)
    password = sqlalchemy.Column(sqlalchemy.String(length=64))
    position = sqlalchemy.Column(sqlalchemy.String(length=30))
    birth_date = sqlalchemy.Column(sqlalchemy.Date)
    email = sqlalchemy.Column(sqlalchemy.String(length=30))
    start_date = sqlalchemy.Column(sqlalchemy.Date)
    hourly_wage = sqlalchemy.Column(sqlalchemy.Float)

    serialize_rules = ('-person.employee','-appointments','-comments', '-password')

    person = sqlalchemy.orm.relationship("Person", back_populates="employee")
    appointments = sqlalchemy.orm.relationship(
        "Appointment", back_populates="employee")
    comments = sqlalchemy.orm.relationship(
        "Comment", back_populates="employee")


    def __str__(self) -> str:
        return f'Employee... id: {self.id}, name: {self.person.first_name} {self.person.last_name}'


class Picture(Base, SerializerMixin):
    __tablename__ = 'pictures'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    picture_bytes = sqlalchemy.Column(sqlalchemy.dialects.postgresql.BYTEA)
    face_bytes = sqlalchemy.Column(sqlalchemy.dialects.postgresql.BYTEA)

    person_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))

    serialize_rules = ('-person','-time_entry','-person_id')

    person = sqlalchemy.orm.relationship("Person", back_populates="pictures")
    time_entry = sqlalchemy.orm.relationship(
        "Time_Entry", back_populates="picture")

    def __str__(self) -> str:
        return f'Picture... id: {self.id}, person name: {self.person.first_name} {self.person.last_name}'


class Vaccine(Base, SerializerMixin):
    __tablename__ = 'vaccines'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    dose_lab = sqlalchemy.Column(sqlalchemy.Enum(enums.VaccineLab))
    lot_num = sqlalchemy.Column(sqlalchemy.String(length=20))
    dose_date = sqlalchemy.Column(sqlalchemy.Date)

    person_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))

    serialize_rules = ('-person', 'lab', '-dose_lab', '-person_id')

    person = sqlalchemy.orm.relationship("Person", back_populates="vaccines")

    def __str__(self) -> str:
        return f'Vaccine... id: {self.id}, person name: {self.person.first_name} \
            lab: {self.dose_lab} date:{self.dose_date}'

    def lab(self):
        return {"name":self.dose_lab.name, "value": self.dose_lab.value}


class Time_Entry(Base, SerializerMixin):
    __tablename__ = 'time_entries'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    action = sqlalchemy.Column(sqlalchemy.Enum(enums.EntryTypes))
    action_time = sqlalchemy.Column(sqlalchemy.DateTime)

    person_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    picture_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('pictures.id'))

    serialize_rules = ('-picture','-person_id','-picture_id')

    person = sqlalchemy.orm.relationship(
        "Person", back_populates="time_entries")
    picture = sqlalchemy.orm.relationship(
        "Picture", back_populates="time_entry")

    def action_type(self):
        return f'{self.action.name}'

    def __str__(self) -> str:
        return f'Time Entry... id: {self.id}\nperson name: {self.person.first_name}\
            \naction: {self.action} \ntime:{self.action_time}\n'


class Appointment(Base, SerializerMixin):
    __tablename__ = 'appointments'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    start = sqlalchemy.Column(sqlalchemy.DateTime)
    end = sqlalchemy.Column(sqlalchemy.DateTime)
    status = sqlalchemy.Column(sqlalchemy.Enum(
        enums.AppointmentStatus), default=enums.AppointmentStatus.PENDING)

    person_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('persons.id'))
    employee_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('employees.id'))

    serialize_rules = ('-person','-status', 'person_id', 'employee_id', 'get_status')

    person = sqlalchemy.orm.relationship(
        "Person", back_populates="appointments")
    employee = sqlalchemy.orm.relationship(
        "Employee", back_populates="appointments")

    def get_status(self):
        return {"name":self.status.name, "value": self.status.value}



class Comment(Base, SerializerMixin):
    __tablename__ = 'comments'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    timestamp = sqlalchemy.Column(sqlalchemy.DateTime)
    text = sqlalchemy.Column(sqlalchemy.String(length=250))
    employee_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('employees.id'))

    serialize_rules = ('-employee','-employee_id')

    employee = sqlalchemy.orm.relationship(
        "Employee", back_populates="comments")


class Camera(Base, SerializerMixin):
    __tablename__ = "cameras"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    ip_address = sqlalchemy.Column(sqlalchemy.String(15))
    user = sqlalchemy.Column(sqlalchemy.String(35))
    password = sqlalchemy.Column(sqlalchemy.String(35))
    route = sqlalchemy.Column(sqlalchemy.String(35))
    entry_type = sqlalchemy.Column(sqlalchemy.Enum(enums.EntryTypes))
    ask_mask = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    ask_temp = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    def connection_string(self):
        return (0 if self.ip_address == '0.0.0.0' else
                f'rtsp://{self.user}:{self.password}@{self.ip_address}:554{self.route}')


if __name__ == '__main__':
    # when runned as file, it'll to create all clases as tables on the database
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    import AccessControl.Data.inits as inits
    inits.init()
