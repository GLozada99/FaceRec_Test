import AccessControl.Data.classes as classes
import AccessControl.Data.enums as enums
import sqlalchemy
import time

Session = sqlalchemy.orm.sessionmaker()
Session.configure(bind=classes.engine)
_session = Session()


def add_entry(entry):
    '''
    Adds an entry to de database
    Entry must be a class object that derives from
    DeclarativeMeta class on sqlalchemy
    '''
    # print('inicio', entry)
    # if entry.__class__ == classes.Person:  # Spaghetti code
    #     print('person')
    #     person = person_by_ident_doc(entry.identification_document)
    #     if person:
    #         person.__dict__.update(entry.__dict__)
    # elif entry.__class__ == classes.Employee:
    #     person = person_by_ident_doc(entry.person.identification_document)[0]
    #     print(person)
    #     if person:
    #         employee = get_entry(classes.Employee, person.id)
    #         if employee:
    #             employee.__dict__.update(entry.__dict__)
    # else:
    #     print('else')
    _session.add(entry)
    _session.commit()
    return True


def get_entry(Class, id: int, inactive=False):
    '''
    Returns entry in table of given class based on id.
    If class uses soft delete, returns only if it's active or inactive flag is True
    '''
    entry = _session.query(Class).get(id)

    if hasattr(entry, 'active'):
        if not entry.active:
            entry = None
    elif Class == classes.Employee:  # Not proud
        entry = entry if _session.query(classes.Person).get(
            id).active or inactive else None

    return entry


def get_entries(Class):
    '''
    Returns all entries in table of given class.
    If class uses soft delete, returns only active entries
    '''
    entry = _session.query(Class).get(1)
    entries = None
    if hasattr(entry, 'active'):
        entries = _session.query(Class).filter_by(active=True)
    elif Class == classes.Employee:  # this elif is awful, but I was desperate
        person_entries = _session.query(classes.Person).filter_by(active=True)
        person_ids = [person.id for person in person_entries]
        entries = [employee for employee in _session.query(
            Class).all() if employee.id in person_ids]
    else:
        entries = _session.query(Class).all()

    return entries


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
    '''
    Returns all persons who are not employees
    '''
    return (_session.query(classes.Person).
            filter(classes.Person.role == enums.PersonRole.PERSON).filter(classes.Person.active).all())


def person_by_ident_doc(identification_document):
    return _session.query(classes.Person).filter_by(identification_document=identification_document).all()


def vaccines_by_person(person):
    return _session.query(classes.Vaccine).filter_by(person_id=person.id).all()


def comments_by_employee(employee):
    return reversed(_session.query(classes.Comment).filter_by(employee_id=employee.id).all())


def pictures_by_person(person):
    return _session.query(classes.Picture).filter_by(person_id=person.id).all()


def get_all_pictures():
    return (_session.query(classes.Picture).join(classes.Picture.person).
            filter(classes.Person.active).all())


def get_employees_pictures():
    return (_session.query(classes.Picture).join(classes.Picture.person).
            filter(classes.Person.role >= enums.PersonRole.PERSON).filter(classes.Person.active).all())


def get_accepted_appointments_pictures():
    return (_session.query(classes.Person).join(classes.Person.pictures).
            join(classes.Person.appointments).filter(classes.Appointment.status == enums.AppointmentStatus.ACCEPTED).all())
