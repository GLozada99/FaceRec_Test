import sqlalchemy, os
from sqlalchemy.ext.declarative import declarative_base

#setting up parameters
_user = os.environ.get('MARIADB_USER')
_password =  os.environ.get('MARIADB_PASSWORD')
_database = 'FaceRecog'

#getting engine
engine = sqlalchemy.create_engine(f'mariadb+mariadbconnector://{_user}:{_password}@127.0.0.1:3306/{_database}')

#getting base for classes
Base = declarative_base()

#creating clases
class Picture(Base):
    __tablename__ = 'pictures2'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(length=30))
    picture_bytes = sqlalchemy.Column(sqlalchemy.dialects.mysql.LONGBLOB)
    face_bytes = sqlalchemy.Column(sqlalchemy.dialects.mysql.LONGBLOB)


if __name__ == '__main__':
    #when runned as file, it'll to create all clases as tables on the database
    Base.metadata.create_all(engine)

