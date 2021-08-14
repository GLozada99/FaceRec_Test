import AccessControl.Data.classes as classes
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
    _session.add(entry)
    _session.commit()


def get_entry(Class, id: int):
    '''
    Returns entry in table of given class based on id.
    If class uses soft delete, returns only if it's active
    '''
    entry = _session.query(Class).get(id)

    if hasattr(entry, 'active'):
        if not entry.active:
            entry = None

    return entry


def get_entries(Class):
    '''
    Returns all entries in table of given class.
    If class uses soft delete, returns only active entries
    '''
    entry = _session.query(Class).get(0)
    entries = None
    if hasattr(entry, 'active'):
        entries = _session.query(Class).filter_by(active=True)
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
        _session.query(Class).get(id).delete()
        _session.commit()


def reactivate_entry(Class, id: int):
    '''
    Sets active attribute to True, only for classes that use soft delete
    '''
    entry = _session.query(Class).get(id)
    if hasattr(entry, 'active'):
        _set_entry_status(entry, False)


def update_entry(Class, entry):
    # not very sure about this one...
    current_entry = _session.query(Class).get(entry.id)
    current_entry.__dict__.update(entry.__dict__)
    _session.commit()
