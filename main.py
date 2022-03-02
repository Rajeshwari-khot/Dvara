import json
from fastapi import Body, FastAPI
from pydantic import BaseModel
from pymysql import Date
from database import get_database, sqlalchemy_engine
from models import metadata



app = FastAPI()

@app.on_event("startup")
async def startup():
    await get_database().connect()
    metadata.create_all(sqlalchemy_engine)

@app.on_event("shutdown")
async def shutdown():
    await get_database().disconnect()
# @app.get("/partnerHandcontext")
# async def root():
#     data=open("partner.json","r")
#     response=json.load(data)
#     return response





@app.post('/')
async def root(
        payload: dict = Body(...)
):
    return payload

@app.get("/customerdata")
async def customer_data():
    customer_request=await root()
    json_data=(customer_request['enrollmentDTO']['customer'])
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
    
    data=(customer_request['enrollmentDTO']['customer']['customerBankAccounts'])
    for ln in data:
       
      bankname=(ln['customerBankName'])
      accno=(ln['accountNumber'])
      ifsccode=(ln['ifscCode'])
      acctype=(ln['accountType'])
    # date_data=(customer_request['enrollmentDTO']['customer']['dateOfBirth'])
    # for ln in [date_data]:
       
    #     Year=(ln['year'])
    #     Month=(ln['month'])
    #     Value=(ln['monthValue'])
    #     day=(ln['dayOfMonth'])
    #     week=(ln['dayOfWeek'])
    #     era=(ln['era'])
    #     dayyear=(ln['dayOfYear'])
    #     leap=(ln['leapYear'])
    #     sample=(str(Year)+str(Month)+str(Value)+str(day)+str( week)+str(era)+str(dayyear)+str(leap))
    

    if lastname or middlename is None:
         if LastName or MiddleName is None:
             if street or post is " ":
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
              "bank_name":bankname,
              "account_number":accno,
              "ifsc_code":ifsccode,
              "account_type":acctype,
            #   "date_of_birth":sample
            
             

              }
@app.get("/loandata")
async def loan_data():
    loan_request=await root()
    json_data=(loan_request['loanDTO']['loanAccount'])
    loanamount=(json_data['loanAmount'])
    interest=(json_data['interestRate'])
   
    tenure=(json_data['tenure'])
    processfee=(json_data['processingFeeInPaisa'])
    
    insurance=(json_data['insuranceFee'])
    additional=(json_data['otherFee'])
    none='not found'
    loan=(loan_request['loanDTO']['loanAccount']['disbursementSchedules'])
    for ln in loan:
       d_amount=(ln['disbursementAmount'])
    return {
        "loan_amount":loanamount,
        "interest_rate":interest,
        "disbursement_amount":d_amount,
        "tenure":tenure,
        "repayment_schedule_json":none,
        "am_user_token":none,
        "sm_user_id":none,
        "sm_loan_id":none,
        "processing_fee":processfee,
         "additional_charges":additional,
        "insurance_charges":insurance,
        "number_of_edis":none
        



    }

   

        
       