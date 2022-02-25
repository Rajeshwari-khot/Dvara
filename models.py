from pydantic import BaseModel
class User(BaseModel):
    sm_user_id : int
    name:str
    father_name:str
    marital_status:str
    mobile_number:int
    email_id:str
    res_city:str
    res_state:str
    res_pin_code:int
    pan_number:str
            #   "date_of_birth":Year-Value-day,
    res_address:str