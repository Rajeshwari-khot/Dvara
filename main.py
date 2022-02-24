import json
from fastapi import FastAPI
from pydantic import BaseModel
from pymysql import Date
app = FastAPI()
@app.get("/partnerHandcontext")
async def root():
    data=open("partner.json","r")
    response=json.load(data)
    return response

@app.get("/customerdata")
async def customer_data():
    json_data=await root()
    return (json_data['enrollmentDTO']['customer'])



