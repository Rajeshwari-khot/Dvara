import json
from fastapi import FastAPI
from pydantic import BaseModel
from pymysql import Date
from models import User
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
   
@app.get("/user")
async def user_data():
    json_data=await customer_data()
    id =(json_data["id"])
    firstname=(json_data["firstName"])
    lastname=(json_data["lastName"])
    middlename=(json_data["middleName"])
    FirstName=(json_data['fatherFirstName'])
    LastName=(json_data['fatherLastName'])
    MiddleName=(json_data['fatherMiddleName'])
    maritalstatus=(json_data['maritalStatus'])
    mobileno=(json_data['mobilePhone'])
    email=(json_data['email'])
    city=(json_data['mailingDistrict'])
    state=(json_data['mailingState'])
    pincode=(json_data['mailingPincode'])
    panno=(json_data['panNo'])
    # Gender=(json_data['gender'])
    doorno=(json_data['mailingDoorNo'])
    street=(json_data['mailingStreet'])
    post=(json_data['mailingPostoffice'])
    local=(json_data['mailingLocality'])
    bankname=(json_data[''])
    # Year=(json_data['year'])
    # Month=(json_data['month'])
    # Value=(json_data['monthValue'])
    # day=(json_data['dayOfMonth'])
    # week=(json_data['dayOfWeek'])
    # era=(json_data['era'])
    # dayyear=(json_data['dayOfYear'])
    # leap=(json_data['leapYear'])
   

    final=(firstname+ str(middlename)+str(lastname))
    addr=(doorno+str(street)+str(post))
    # sample=(Year+str(Month)+str(Value)+str(day)+str( week)+str(era)+str(dayyear)+str(leap))
    

    if lastname or middlename is None:
         if LastName or MiddleName is None:
             if street or post is "":
              return {
             "sm_user_id" : id,
             "name":firstname,
            "father_name":FirstName,
             "marital_status":maritalstatus,
              "mobile_number":mobileno,
              "email_id":email,
               "res_address":doorno+local,
              "res_city":city,
              "res_state":state,
              "res_pin_code":pincode,
              "pan_number":panno,
            #   "date_of_birth":Year-Value-day,
             

              }
@app.get("/loandata")
async def loan_data():
    json_data=await root()
    return (json_data['loanDTO']['loanAccount'])

@app.get("/loan_request")
async def loan_request():
    json_data=await loan_data()
    loanamount=(json_data['loanAmount'])
    interest=(json_data['interestRate'])
    tenure=(json_data['tenure'])
    return {
        "loan_amount":loanamount,
        "interest_rate":interest,
        "tenure":tenure,


    }

   
@app.post('/userdata')
async def create_user(user:User):
     
     return user

        
       