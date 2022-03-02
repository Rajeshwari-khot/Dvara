import sqlalchemy
from databases import Database


DATABASE_URL = "mysql+pymysql://rajeshwari:rajeshwari@database-2.cekazfzvpdz3.us-east-2.rds.amazonaws.com:3306/sys"
database = Database(DATABASE_URL)
sqlalchemy_engine = sqlalchemy.create_engine(DATABASE_URL)


def get_database() -> Database:
    return database