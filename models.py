import sqlalchemy
metadata = sqlalchemy.MetaData()
perdix=sqlalchemy.Table(
    "Perdixdata",
     metadata,
     sqlalchemy.Column("details", sqlalchemy.String(length=255), nullable=False)
   
)