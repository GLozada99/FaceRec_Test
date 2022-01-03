import AccessControl.Data.classes as classes
import AccessControl.Data.enums as enums
import numpy as np
import sqlalchemy
import time
import datetime
import holidays

Session = sqlalchemy.orm.sessionmaker()
Session.configure(bind=classes.engine)
_session = Session()
REGULAR_WORK_HOURS = 8


def add_entry(entry):
    '''
    Adds an entry to de database
    Entry must be a class object that derives from
    DeclarativeMeta class on sqlalchemy
    '''
    _session.add(entry)
    _session.commit()
    return True


def get_entry(Class, id: int):
    '''
    Returns entry in table of given class based on id.
    '''
    return _session.query(Class).get(id)


def get_entries(Class):
    '''
    Returns all entries in table of given class.
    '''
    return _session.query(Class).all()


def _set_entry_status(entry, status: bool):
    entry.active = status
    if status:
        entry.deactivated_on = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime())
    else:
        entry.deactivated_on = None

    _session.commit()


def delete_entry(Class, id: int):
    '''
    Deletes entry in table of given class based on id.
    If class uses soft delete, sets "active" field to False
    '''
    entry = _session.query(Class).get(id)
    if hasattr(entry, 'active'):
        _set_entry_status(entry, False)
    else:
        _session.delete(entry)
    _session.commit()


def reactivate_entry(Class, id: int):
    '''
    Sets active attribute to True, only for classes that use soft delete
    '''
    entry = _session.query(Class).get(id)
    if hasattr(entry, 'active'):
        _set_entry_status(entry, False)


def commit():
    _session.commit()


def update_entry_with_entry(Class, source, destination):
    # not very sure about this one...
    destination.__dict__.update(source.__dict__)
    _session.commit()


def get_persons():
    return (_session.query(classes.Person).
            filter(classes.Person.role == enums.PersonRole.PERSON).
            filter(classes.Person.active).all())

def get_employees():
    return (_session.query(classes.Employee).
            join(classes.Person).filter(classes.Person.active).all())

def get_person(id):
    return (_session.query(classes.Person).
            filter(classes.Person.role == enums.PersonRole.PERSON).
            filter(classes.Person.active, classes.Person.id == id)).first()

def get_all(id):
    return (_session.query(classes.Person).
            filter(classes.Person.active, classes.Person.id == id)).first()

def get_employee(id):
    return (_session.query(classes.Employee).
            join(classes.Person).filter(
                classes.Person.id == id, classes.Person.active)).first()

def person_by_ident_doc(identification_document):
    return _session.query(classes.Person).filter(
        classes.Person.identification_document == identification_document).first()


def vaccines_by_person(person):
    return _session.query(classes.Vaccine).filter(classes.Vaccine.person_id==person.id).all()


def comments_by_employee(employee):
    return reversed(_session.query(classes.Comment).filter(
        classes.Comment.employee_id==employee.id).all())


def first_picture_person(person):
    return _session.query(classes.Picture).filter(classes.Picture.person_id==person.id).first()


def appointments_by_person(person):
    return _session.query(classes.Appointment).filter(classes.Appointment.person_id==person.id).all()

def appointments_by_person_time(person):
    return _session.query(classes.Appointment).filter(classes.Appointment.person_id==person.id).filter(classes.Appointment.status==enums.AppointmentStatus.ACCEPTED).filter((classes.Appointment.start + datetime.timedelta(hours=1)) >= datetime.now()).first()

def get_all_pictures():
    return (_session.query(classes.Picture).join(classes.Picture.person).
            filter(classes.Person.active).all())

def get_employees_pictures():
    return (_session.query(classes.Picture).join(classes.Picture.person).
            filter(classes.Person.role >= enums.PersonRole.PERSON).filter(classes.Person.active).all())

def get_accepted_appointments_pictures():
    return (_session.query(classes.Picture).join(classes.Person).join(classes.Appointment).filter(classes.Appointment.status == enums.AppointmentStatus.ACCEPTED).all())

def grouped(iterable, n):
    return zip(*[iter(iterable)]*n)

def _get_day_entries_employee(employee, date):
    entries = _session.query(classes.Time_Entry).filter(classes.Time_Entry.person_id == employee.id).order_by(classes.Time_Entry.action_time.asc()).all()
    return [entrie for entrie in entries if entrie.action_time.date() == date]

def _get_day_time_employee(employee, date_time):
    date = date_time.date()
    entries = _get_day_entries_employee(employee, date)
    country_holidays = holidays.DominicanRepublic(years = date.year)

    return (sum(
        (out.action_time - entry.action_time).total_seconds()/3600
        for entry, out in grouped(entries, 2)
        if ((entry.action is enums.EntryTypes.ENTRY)
        and (out.action in {enums.EntryTypes.EXIT, enums.EntryTypes.PC}))
    ) if date not in country_holidays else REGULAR_WORK_HOURS), entries

def get_week_work_hours(year, week, employee=1):
    start = datetime.datetime.fromisocalendar(year, week, 1)
    end = start + datetime.timedelta(days=5)
    delta = datetime.timedelta(days=1)

    all_entries = {}
    for day in np.arange(start, end, delta).astype(datetime.datetime):
        time, entries = _get_day_time_employee(employee, day)
        all_entries[str(day.date())] = entries, time

    return all_entries
