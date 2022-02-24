import json
from fastapi import FastAPI
app = FastAPI()
@app.get("/partnerHandcontext")
async def root():
    data=open("partner.json","r")
    json_data=json.load(data)
    return json_data

@app.get("/cutomerdata")
async def customer_data():
    data=open("partner.json","r")
    json_data=json.load(data)
    return(json_data['enrollmentDTO']['customer'])