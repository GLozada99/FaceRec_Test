from enum import Enum


class PictureClassification(Enum):
    ALL_ACTIVE = 0
    EMPLOYEES_ACTIVE = 1
    ACCEPTED_APPOINTMENTS = 2


class PersonRole(Enum):
    PERSON = 0
    EMPLOYEE = 1
    ADMIN = 2
    SUPER_ADMIN = 3


class AppointmentStatus(Enum):
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2
    ONGOING = 3
    FINALIZED = 4
    RUNNING_LATE = 5
    NEVER_HAPPENED = 6


class VaccineLab(Enum):
    PFIZER = 0
    SINOVAC = 1
    ASTRAZENECA = 2
    SPUTNIK = 3


class SpeakerLanguages(Enum):
    ENGLISH = 0
    SPANISH = 1


class EntryTypes(Enum):
    ENTRY = 0
    EXIT = 1
