import json
import urllib.request

from datetime import datetime

from dm_nac_service.resource.log_config import logger
from fastapi import APIRouter, status,Body
from fastapi.responses import JSONResponse

from dm_nac_service.routes.dedupe import create_dedupe
from dm_nac_service.data.database import get_database
from dm_nac_service.gateway.nac_perdix_automator import  perdix_fetch_loan, perdix_update_loan
from dm_nac_service.gateway.nac_sanction import nac_get_sanction
from dm_nac_service.routes.sanction import create_sanction, find_sanction,  find_loan_id_from_sanction
from dm_nac_service.resource.generics import  hanlde_response_body, hanlde_response_status, fetch_data_from_db
from dm_nac_service.data.sanction_model import sanction
from dm_nac_service.commons import get_env_or_fail
from dm_nac_service.routes.disbursement import find_customer_sanction, create_disbursement
from dm_nac_service.gateway.nac_disbursement import  disbursement_get_status
from dm_nac_service.data.disbursement_model import (disbursement)
from dm_nac_service.data.sanction_model import (sanction)
router = APIRouter()


NAC_SERVER = 'northernarc-server'


@router.post("/nac-dedupe-automator-data", tags=["Automator"])
async def post_automator_data(
    # Below is for Production setup
    # request_info: Request,
    # response: Response

    # Below is to test manually by providing json data in request body
    request_info: dict = Body(...),

):
    """Function which prepares user data and posts"""
    try:
        # Below is for data published from automator
        # payload = await request_info.json()

        # Below is for data published manually
        payload = request_info

        # Data Preparation to post the data to NAC dedupe endpoint
        customer_data = payload["enrollmentDTO"]["customer"]
        loan_data = payload["loanDTO"]["loanAccount"]
        first_name = customer_data.get("firstName")
        middle_name=customer_data.get("middleName")
        last_name = customer_data.get("lastName")
        first_name = first_name if first_name else ""
        middle_name = middle_name if middle_name else ""
        last_name = last_name if last_name else ""
        
        if(middle_name!=None):
             full_name=first_name+' '+middle_name+' '+last_name
        else:
             full_name=first_name+middle_name+last_name

        date_of_birth = customer_data.get("dateOfBirth")
        if "str" != type(date_of_birth).__name__:
            date_of_birth = "{:04d}-{:02d}-{:02d}".format(
                date_of_birth["year"],
                date_of_birth["monthValue"],
                date_of_birth["dayOfMonth"],
            )
        bank_accounts_info = {}
        if len(customer_data["customerBankAccounts"]) > 0:
            bank_accounts_info = customer_data["customerBankAccounts"][0]
        sm_loan_id=str(loan_data.get("id"))
        
        dedupe_data = {
                "accountNumber": bank_accounts_info.get("accountNumber"),
                "contactNumber": str(customer_data.get("mobilePhone"))[-10:],
                "customerName": full_name,
                "dateofBirth": str(date_of_birth),
                "kycDetailsList": [
                    {
                        "type": "PANCARD",
                        "value": customer_data.get("panNo")
                    },
                    {
                        "type": "AADHARCARD",
                        "value": customer_data.get("aadhaarNo")
                    }
                ],
                "loanId": str(loan_data.get("id")),
                "pincode": str(customer_data.get("pincode")),
            }

        print('1 - prepared data from automator function', dedupe_data)

        # Posting the data to the dedupe API
        dedupe_response = await create_dedupe(dedupe_data)
        print('12 - coming back to automator function', dedupe_response)
        dedupe_response_status = hanlde_response_status(dedupe_response)
        dedupe_response_body = hanlde_response_body(dedupe_response)
        if(dedupe_response_status == 200):
            print('12a Success - response from create dedupe')
            dedupe_data_respose = hanlde_response_body(dedupe_response)
            is_dedupe_present = dedupe_data_respose.get('isDedupePresent')
            str_fetch_dedupe_info = dedupe_data_respose.get('dedupeReferenceId')

            if (is_dedupe_present == False):

                message_remarks = ''
                update_loan_info = await update_loan('DEDUPE', sm_loan_id, str_fetch_dedupe_info, 'Dedupe',
                                                         message_remarks,
                                                         'PROCEED', message_remarks)
                if(update_loan_info.status_code == 200):
                    print('14a - updated loan information with dedupe reference to Perdix', update_loan_info)
                    payload['partnerHandoffIntegration']['status'] = 'SUCCESS'
                    payload['partnerHandoffIntegration']['partnerReferenceKey'] = str_fetch_dedupe_info
                else:
                    perdix_update_unsuccess = hanlde_response_body(update_loan_info)
                    result = JSONResponse(status_code=500, content=perdix_update_unsuccess)
                    payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                    payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
            else:
                dedupe_response_result = len(dedupe_data_respose.get('results'))
                is_eligible_flag = dedupe_data_respose.get('results')[dedupe_response_result-1].get('isEligible')
                message_remarks = dedupe_data_respose.get('results')[dedupe_response_result-1].get('message')
                if (is_eligible_flag == False):
                    update_loan_info = await update_loan('DEDUPE', sm_loan_id, str_fetch_dedupe_info, 'Rejected',
                                                         message_remarks,
                                                         'PROCEED', message_remarks)

                    if (update_loan_info.status_code == 200):
                        print('14a - updated loan information with dedupe reference to Perdix', update_loan_info)
                        payload['partnerHandoffIntegration']['status'] = 'SUCCESS'
                        payload['partnerHandoffIntegration']['partnerReferenceKey'] = str_fetch_dedupe_info
                    else:
                        perdix_update_unsuccess = hanlde_response_body(update_loan_info)
                        result = JSONResponse(status_code=500, content=perdix_update_unsuccess)
                        payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                        payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
                    print('14b - updated loan information with dedupe reference to Perdix', update_loan_info)
                else:
                    update_loan_info = await update_loan('DEDUPE', sm_loan_id, str_fetch_dedupe_info, 'Dedupe',
                                                         message_remarks,
                                                         'PROCEED', message_remarks)
                    if (update_loan_info.status_code == 200):
                        print('14a - updated loan information with dedupe reference to Perdix', update_loan_info)
                        payload['partnerHandoffIntegration']['status'] = 'SUCCESS'
                        payload['partnerHandoffIntegration']['partnerReferenceKey'] = str_fetch_dedupe_info
                    else:
                        perdix_update_unsuccess = hanlde_response_body(update_loan_info)
                        result = JSONResponse(status_code=500, content=perdix_update_unsuccess)
                        payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                        payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
                    print('14c - updated loan information with dedupe reference to Perdix', update_loan_info)

            result = payload

        else:
            dedupe_response_body_message = dedupe_response_body.get('message')
            print('12a Failure - response from create dedupe', dedupe_response_body_message)
            update_loan_info = await update_loan('DEDUPE', sm_loan_id, '', 'Rejected',
                                                 str(dedupe_response_body_message),
                                                 'PROCEED', str(dedupe_response_body_message))
            if (update_loan_info.status_code == 200):
                print('14a - updated loan information with dedupe reference to Perdix', update_loan_info)
                payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
            else:
                perdix_update_unsuccess = hanlde_response_body(update_loan_info)
                result = JSONResponse(status_code=500, content=perdix_update_unsuccess)
                payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
            print('14c - updated loan information with dedupe reference to Perdix', update_loan_info)
            logger.error(f"{datetime.now()} - post_automator_data - 150 - {dedupe_response_body}")
            result = payload

    except Exception as e:
        logger.exception(f"{datetime.now()} - Issue with post_automator_data function, {e.args[0]}")
        result = JSONResponse(status_code=500, content={"message": f"Issue with post_automator_data function, {e.args[0]}"})
    return result


@router.post("/nac-sanction-automator-data", status_code=status.HTTP_200_OK, tags=["Automator"])
async def post_sanction_automator_data(
    # request_info: Request,
    # response: Response
    # Below is to test manually by providing json data in request body
    request_info: dict = Body(...),
):
    """Function which prepares user data and posts"""
    try:
        
        # payload = await request_info.json()

        # Below is for data published manually
        payload = request_info

        # customer Data
        customer_data = payload["enrollmentDTO"]["customer"]
        father_first_name = customer_data.get("fatherFirstName")
        father_middle_name = customer_data.get("fatherMiddleName")
        father_last_name = customer_data.get("fatherLastName")
        father_first_name = father_first_name if father_first_name else ""
        father_last_name = father_last_name if father_last_name else ""
        father_middle_name = father_middle_name if father_middle_name else ""
        father_full_name = father_first_name + father_middle_name + father_last_name
        date_of_birth = customer_data.get("dateOfBirth")
        if "str" != type(date_of_birth).__name__:
            date_of_birth = "{:04d}-{:02d}-{:02d}".format(
                date_of_birth["year"],
                date_of_birth["monthValue"],
                date_of_birth["dayOfMonth"],
            )
        bank_accounts_info = {}
        if len(customer_data["customerBankAccounts"]) > 0:
            bank_accounts_info = customer_data["customerBankAccounts"][0]
       
        income_info = {}
        if len(customer_data["familyMembers"]) > 0:
            income_info = customer_data["familyMembers"][0]["incomes"][0]
        

        emi_info = {}
        if len(customer_data["liabilities"]) > 0:
            emi_info = customer_data["liabilities"][0]
        

        repayment_info = {}
        if len(customer_data["verifications"]) > 0:
            repayment_info = customer_data["verifications"][0]

       

        # Loan Data
        loan_data = payload["loanDTO"]["loanAccount"]
        sm_loan_id = loan_data.get("id")
       
        installment_info = {}
        if len(loan_data["disbursementSchedules"]) > 0:
            installment_info = loan_data["disbursementSchedules"][0]
        
       

        schedule_date = loan_data.get("scheduleStartDate")
        if "str" != type(schedule_date).__name__:
            schedule_date = "{:04d}-{:02d}-{:02d}".format(
                schedule_date["year"],
                schedule_date["monthValue"],
                schedule_date["dayOfMonth"],
            )

        frequency = loan_data.get("frequency")
        if(frequency == 'M'):
            
            repayment_frequency = 'WEEKLY'
            tenure_unit = 'MONTHS'
        if(frequency == 'W'):
            repayment_frequency = 'WEEKLY'
            tenure_unit = 'WEEKS'
        if (frequency == 'D'):
            repayment_frequency = 'DAILY'
            tenure_unit = 'DAYS'
        if (frequency == 'Y'):
            tenure_unit = 'YEARS'
        if (frequency == 'F'):
            repayment_frequency = 'FORTNIGHTLY'

        sanction_data = {
                "mobile": str(customer_data.get("mobilePhone"))[-10:],
                "firstName": customer_data.get("firstName"),
                "lastName": customer_data.get("lastName"),
                "fatherName": father_full_name,
                "gender": customer_data.get('gender'),
                "idProofTypeFromPartner": "PANCARD",
                "idProofNumberFromPartner": customer_data.get("panNo"),
                "addressProofTypeFromPartner": "AADHARCARD",
                "addressProofNumberFromPartner": customer_data.get("aadhaarNo"),
                "dob": str(date_of_birth),
                "ownedVehicle": customer_data.get("vehiclesOwned"),
                "currDoorAndBuilding": customer_data.get("doorNo"),
                "currStreetAndLocality":customer_data.get("mailingLocality"),
                "currLandmark": customer_data.get("landmark"),
                "currCity": customer_data.get("mailingLocality"),
                "currDistrict": customer_data.get("district"),
                "currState": customer_data.get("state"),
                "currPincode": str(customer_data.get("pincode")),
                "permDoorAndBuilding": customer_data.get("doorNo"),
                "permLandmark": customer_data.get("landmark"),
                "permCity":customer_data.get("locality"),
                "permDistrict": customer_data.get("district"),
                "permState": customer_data.get("state"),
                "permPincode": str(customer_data.get("pincode")),
                "companyName": customer_data['udf']['userDefinedFieldValues']['udf7'],
                "clientId": str(loan_data.get("customerId")),
                "grossMonthlyIncome": income_info.get("incomeEarned"),
                "netMonthlyIncome": income_info.get("incomeEarned"),
                "pan": customer_data.get("panNo"),
                "purposeOfLoan":loan_data.get("requestedLoanPurpose") ,
                "loanAmount":loan_data.get("loanAmount") ,
                "interestRate":loan_data.get("interestRate") ,
                "scheduleStartDate": schedule_date,
                "firstInstallmentDate": installment_info.get("firstRepaymentDate"),
                "totalProcessingFees": loan_data.get("processingFeeInPaisa"),
                "preEmiAmount": loan_data.get("preEmi"),
                "emi": loan_data.get("emi"),
                "emiDate": emi_info.get("emiDate"),
                "repaymentFrequency": repayment_frequency,
                "repaymentMode": repayment_info.get("modeOfPayment"),
                "tenureValue": int(loan_data.get("tenure")),
                "tenureUnits": tenure_unit,
                "productName": loan_data.get("productCode"),
                "primaryBankAccount": bank_accounts_info.get("accountNumber"),
                "bankName":  bank_accounts_info.get("customerBankName"),
                "email": customer_data.get("email"),
                "middleName": customer_data.get("middleName"),
                "maritalStatus": customer_data.get("maritalStatus"),
                "loanId": str(sm_loan_id),
                }
        sanction_data['emiWeek'] = 1
        sanction_data['modeOfSalary'] = "ONLINE"
        sanction_data['incomeValidationStatus'] = True
        sanction_data['gst'] = 0
        sanction_data['occupation']="SALARIED_OTHER"

        print('1 - Sanction Data from Perdix and Sending the data to create sanction function', sanction_data)
        sanction_response = await create_sanction(sanction_data)
        sanction_response_status = hanlde_response_status(sanction_response)
        sanction_response_body = hanlde_response_body(sanction_response)

        print(f"------------{sanction_response_body}")
        if(sanction_response_status == 200):

            get_sanction_ref = await find_sanction(sm_loan_id)
            get_sanction_ref_status = hanlde_response_status(get_sanction_ref)
            response_body_json = hanlde_response_body(get_sanction_ref)
            if(get_sanction_ref_status == 200):
                reference_id = str(response_body_json.get('customerId'))
                message_remarks = 'Customer Created Successfully'

                # To Update Perdix with Sanction Reference ID
                update_loan_info = await update_loan('SANCTION', sm_loan_id, reference_id, 'Dedupe', message_remarks,
                                                     'PROCEED', message_remarks)
                update_loan_info_status = hanlde_response_status(update_loan_info)
                if(update_loan_info_status == 200):

                    payload['partnerHandoffIntegration']['status'] = 'SUCCESS'
                    payload['partnerHandoffIntegration']['partnerReferenceKey'] = reference_id
                    result = payload
                else:
                    loan_update_error = hanlde_response_body(get_sanction_ref)
                    logger.error(f"{datetime.now()} - post_sanction_automator_data - 426 - {loan_update_error}")
                    result = JSONResponse(status_code=500, content=loan_update_error)
                    payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                    payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
                    result = payload
            else:
                logger.error(f"{datetime.now()} - post_sanction_automator_data - 426 - {response_body_json}")
                result = JSONResponse(status_code=500, content=response_body_json)
                payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
                result = payload
        else:
           
            sanction_response_get_body = sanction_response_body.get('body')
            sanction_response_get_body_json = json.loads(sanction_response_get_body)
            sanction_response_get_body_value = sanction_response_get_body_json.get('content').get('value')
            update_loan_info = await update_loan('SANCTION', sm_loan_id, '', 'Rejected', str(sanction_response_get_body_value),
                                                 'PROCEED', str(sanction_response_get_body_value))
            logger.error(f"{datetime.now()} - post_sanction_automator_data - 452 - {sanction_response_body}")
            result = JSONResponse(status_code=500, content=sanction_response_body)
            payload['partnerHandoffIntegration']['status'] = 'FAILURE'
            payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
            result = payload
    except Exception as e:
        logger.exception(f"{datetime.now()} - Issue with post_sanction_automator_data function, {e.args[0]}")
        result = JSONResponse(status_code=500,content={"message": f"Issue with post_automator_data function, {e.args[0]}"})
    return result


@router.post("/nac-disbursement-automator-data", status_code=status.HTTP_200_OK, tags=["Automator"])
async def post_disbursement_automator_data(
    # request_info: Request,
    # response: Response
    # Below is to test manually by providing json data in request body
    request_info: dict = Body(...),
):
    try:
        database = get_database()
        
        # Below is for data published manually
        payload = request_info
        # Customer Data
        customer_data = payload["enrollmentDTO"]["customer"]
        loan_data = payload["loanDTO"]["loanAccount"]

        # Loan Data
        sm_loan_id = loan_data.get("id")
        bank_accounts_info = {}
        if len(customer_data["customerBankAccounts"]) > 0:
            bank_accounts_info = customer_data["customerBankAccounts"][0]
        print('1 - Fetch customer Id and Sanction Reference Id from DB', sm_loan_id)
        customer_sanction_response = await find_customer_sanction(sm_loan_id)
        customer_sanction_response_status = hanlde_response_status(customer_sanction_response)
        customer_sanction_response_body = hanlde_response_body(customer_sanction_response)
        if(customer_sanction_response_status == 200):
            sanction_ref_id = customer_sanction_response_body.get('sanctionRefId')
            customer_id = customer_sanction_response_body.get('customerId')
            
            print('2 - Response from DB with customer id and sanction ref id', customer_sanction_response)
            originator_id = get_env_or_fail(NAC_SERVER, 'originator-id', NAC_SERVER + 'originator ID not configured')
            print('3 - Originator ID from env', originator_id)

            disbursement_info = {
                "originatorId": originator_id,
                "sanctionReferenceId": int(sanction_ref_id),
                "customerId": int(customer_id),
                "requestedAmount": loan_data.get("loanAmount"),
                "ifscCode": bank_accounts_info.get("ifscCode"),
                "branchName":  bank_accounts_info.get("customerBankBranchName"),
                "processingFees": loan_data.get("processingFeeInPaisa"),
                "insuranceAmount": loan_data.get("insuranceFee"),
                "disbursementDate": loan_data.get("loanDisbursementDate")
            }
            print('4 - Data Prepared to post to NAC disbursement endpoint', disbursement_info)
            # Real Endpoint
            nac_disbursement_response = await create_disbursement(disbursement_info)
            print('5 - Response from NAC disbursement endpoint', nac_disbursement_response)
            nac_disbursement_response_status = hanlde_response_status(nac_disbursement_response)
            nac_disbursement_response_body = hanlde_response_body(nac_disbursement_response)

            if(nac_disbursement_response_status == 200):
                print('5a - Response from NAC disbursement endpoint', nac_disbursement_response_body)
                disbursement_message = nac_disbursement_response_body['content']['message']
                disbursement_reference_id = nac_disbursement_response_body['content']['value']['disbursementReferenceId']
                payload['partnerHandoffIntegration']['status'] = 'SUCCESS'
                payload['partnerHandoffIntegration']['partnerReferenceKey'] = disbursement_reference_id
                update_loan_info = await update_loan('DISBURSEMENT', sm_loan_id, disbursement_reference_id, '',
                                                     disbursement_message,
                                                     'PROCEED', disbursement_message)
                update_loan_info_status = hanlde_response_status(update_loan_info)
                if (update_loan_info_status == 200):

                    payload['partnerHandoffIntegration']['status'] = 'SUCCESS'
                    payload['partnerHandoffIntegration']['partnerReferenceKey'] = disbursement_reference_id
                    result = payload
                else:
                    loan_update_error = hanlde_response_body(update_loan_info)
                    logger.error(f"{datetime.now()} - post_sanction_automator_data - 426 - {loan_update_error}")
                    result = JSONResponse(status_code=500, content=loan_update_error)
                    payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                    payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
                    result = payload


                result = payload
            else:
                payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
                nac_disbursement_response_body_message = nac_disbursement_response_body.get('content').get('message')
                print('5b - Response from NAC disbursement endpoint', nac_disbursement_response_body.get('content').get('message'))
                logger.error(f"{datetime.now()} - Issue with post_disbursement_automator_data function")
                update_loan_info = await update_loan('DISBURSEMENT', sm_loan_id, '', 'Rejected',
                                                     nac_disbursement_response_body_message,
                                                     'PROCEED', nac_disbursement_response_body_message)
                update_loan_info_status = hanlde_response_status(update_loan_info)
                if (update_loan_info_status == 200):

                    payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                    payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
                    result = payload
                else:
                    loan_update_error = hanlde_response_body(update_loan_info)
                    logger.error(f"{datetime.now()} - post_sanction_automator_data - 426 - {loan_update_error}")
                    result = JSONResponse(status_code=500, content=loan_update_error)
                    payload['partnerHandoffIntegration']['status'] = 'FAILURE'
                    payload['partnerHandoffIntegration']['partnerReferenceKey'] = ''
                    result = payload
                result = JSONResponse(status_code=500, content={"message": f"Issue with post_disbursement_automator_data function"})
        else:
           
            logger.error(f"{datetime.now()} - Issue with post_disbursement_automator_data function")
            result = JSONResponse(status_code=500, content={"message": f"Issue with post_disbursement_automator_data function"})
    except Exception as e:
        logger.exception(f"{datetime.now()} - Issue with post_disbursement_automator_data function, {e.args[0]}")
        result = JSONResponse(status_code=500, content={"message": f"Issue with post_disbursement_automator_data function, {e.args[0]}"})
    return result


@router.post("/perdix/update-loan", tags=["Perdix"])
async def update_loan(
    url_type: str,
    loan_id: int,
    reference_id: str,
    stage: str,
    reject_reason: str,
    loan_process_action: str,
    remarks: str
):
    try:
        # For Real updating the loan information
        get_loan_info = await perdix_fetch_loan(loan_id)
        loan_response_decode_status = hanlde_response_status(get_loan_info)
        loan_response_decode_body = hanlde_response_body(get_loan_info)
        ('printing loan info ', loan_response_decode_body)
        if(loan_response_decode_status == 200):

            get_loan_info = loan_response_decode_body
            ('printing loan info ', get_loan_info)
           

            if "rejectReason" in get_loan_info:
                get_loan_info['rejectReason'] = reject_reason
            get_loan_info['stage'] = stage
            if "remarks1" in get_loan_info:
                get_loan_info['remarks1'] = "Testing remarks1"
            if "loanProcessAction" in get_loan_info:
                get_loan_info['loanProcessAction'] = "Testing loanProcessAction"
            if "accountUserDefinedFields" in get_loan_info:
                if (url_type == 'DEDUPE'):
                    get_loan_info['accountUserDefinedFields']['userDefinedFieldValues']['udf41'] = reference_id

                if (url_type == 'SANCTION'):
                    get_loan_info['accountUserDefinedFields']['userDefinedFieldValues']['udf42'] = reference_id

                if (url_type == 'SANCTION-REFERENCE'):
                    get_loan_info['accountUserDefinedFields']['userDefinedFieldValues']['udf43'] = reference_id

                if (url_type == 'DISBURSEMENT'):
                    get_loan_info['accountUserDefinedFields']['userDefinedFieldValues']['udf44'] = reference_id

                if (url_type == 'DISBURSEMENT-ITR'):
                    get_loan_info['accountUserDefinedFields']['userDefinedFieldValues']['udf45'] = reference_id
            if(stage == 'Rejected'):
                prepare_loan_info = {
                    "loanAccount": get_loan_info,
                    "loanProcessAction": loan_process_action,
                    "stage": stage,
                    "remarks": remarks,
                    "rejectReason": reject_reason
                }
            else:
                prepare_loan_info = {
                    "loanAccount": get_loan_info,
                    "loanProcessAction": loan_process_action,
                    "remarks": remarks,
                    "rejectReason": ''
                }

            # Below is for loan Id 317
            prepare_loan_info['loanAccount']['tenure'] = 24
           
            print('before updateing perdix loan', prepare_loan_info)
            update_perdix_loan = await perdix_update_loan(prepare_loan_info)
            perdix_update_loan_response_decode_status = hanlde_response_status(update_perdix_loan)
            loan_response_decode_body = hanlde_response_body(update_perdix_loan)
            if(perdix_update_loan_response_decode_status == 200):
                print('after updateing perdix loan', loan_response_decode_body)
                result = JSONResponse(status_code=200, content=loan_response_decode_body)
            else:
                logger.error(f"{datetime.now()} - update_loan - 573 - {loan_response_decode_body}")
                result = JSONResponse(status_code=404, content=loan_response_decode_body)

        else:
            logger.error(f"{datetime.now()} - update_loan - 573 - {loan_response_decode_body}")
            result = JSONResponse(status_code=404, content=loan_response_decode_body)
    except Exception as e:
        logger.exception(f"Issue with update_loan function, {e.args[0]}")
        result = JSONResponse(status_code=500, content={"message": f"Error Occurred at DB level - {e.args[0]}"})
    return result


@router.post("/sanction/upload-document", tags=["Perdix"])
def document_upload(settings, url, document_info, image_id):
    file_url = settings.file_stream_url + image_id
    tmp_file = "/tmp/" + image_id + ".jpg"
    urllib.request.urlretrieve(file_url, tmp_file)

    with open(tmp_file, "rb") as file_handle:
        files = {"file": file_handle}
        document_response = requests.post(
            url,
            auth=HTTPBasicAuth(settings.username, settings.password),
            data=document_info,
            files=files,
        )
        return document_response


@router.post("/sanction/update-sanction-in-db", tags=["Perdix"])
async def update_sanction_in_db():
    try:
        database = get_database()
        database_record_fetch = await fetch_data_from_db(sanction)
        print('fetching recrods from db', database_record_fetch)
        for i in database_record_fetch:
            customer_id = i[1]
            sm_loan_id = i[61]
            sanction_gt_response = await nac_get_sanction('sanction', customer_id)
            print('response from sanction_gt_response', sanction_gt_response)
            sanction_gt_response_status = hanlde_response_status(sanction_gt_response)
            sanction_gt_response_body = hanlde_response_body(sanction_gt_response)
            
            if(sanction_gt_response_status == 200):
                print('GETTING 200 RESPONSE FROM NAC ',sanction_gt_response_status, sanction_gt_response_body)
                sanction_status = sanction_gt_response_body.get('content').get('status')
               
                if (sanction_status == 'SUCCESS'):
                    print('inside SUCCESS')
                    sanction_status_value = sanction_gt_response_body['content']['value']
                    sanction_status_value_status = sanction_gt_response_body['content']['value']['status']
                    if (sanction_status_value_status == 'ELIGIBLE'):
                        print('inside ELIGIBLE')
                        sanction_status_value_reference_id = sanction_gt_response_body['content']['value'][
                            'sanctionReferenceId']
                        sanction_status_value_bureau_fetch = sanction_gt_response_body['content']['value'][
                            'bureauFetchStatus']
                        print('coming here', sanction_status_value_reference_id, sanction_status_value_bureau_fetch)
                        query = sanction.update().where(sanction.c.customer_id == customer_id).values(
                            status=sanction_status_value_status,
                           
                            sanctin_ref_id=sanction_status_value_reference_id,
                            bureau_fetch_status=sanction_status_value_bureau_fetch)
                        sanction_updated = await database.execute(query)
                        update_loan_info = await update_loan('SANCTION-REFERENCE', sm_loan_id,
                                                             sanction_status_value_reference_id, 'Dedupe',
                                                             sanction_status_value_bureau_fetch,
                                                             'PROCEED', sanction_status_value_bureau_fetch)
                    elif (sanction_status_value_status == 'REJECTED'):
                        print('inside REJECTED')
                        sanction_status_value_stage = sanction_gt_response_body['content']['value'][
                            'stage']
                        sanction_status_value_bureau_fetch = sanction_gt_response_body['content']['value'][
                            'bureauFetchStatus']
                        if (sanction_status_value_stage == 'BUREAU_FETCH'):
                            print('inside BUREAU_FETCH')

                            query = sanction.update().where(sanction.c.customer_id == customer_id).values(
                                status=sanction_status_value_status,
                                stage=sanction_status_value_stage,
                                bureau_fetch_status=sanction_status_value_bureau_fetch)
                            sanction_updated = await database.execute(query)
                            update_loan_info = await update_loan('SANCTION', sm_loan_id, '',
                                                                 'Rejected',
                                                                 sanction_status_value_bureau_fetch,
                                                                 'PROCEED', sanction_status_value_bureau_fetch)
                        else:
                            print('inside else BUREAU_FETCH')
                            sanction_status_value_reject_reason = str(response_sanction_status['content']['value'][
                                                                          'rejectReason'])
                            print(sanction_status_value_reject_reason)
                            query = sanction.update().where(sanction.c.customer_id == customer_id).values(
                                status=sanction_status_value_status,
                                stage=sanction_status_value_stage,
                                reject_reason=sanction_status_value_reject_reason,
                                bureau_fetch_status=sanction_status_value_bureau_fetch)
                            sanction_updated = await database.execute(query)
                            update_loan_info = await update_loan('SANCTION', sm_loan_id, '',
                                                                 'Rejected',
                                                                 sanction_status_value_reject_reason,
                                                                 'PROCEED', sanction_status_value_reject_reason)
                    else:
                        print('inside else not eligible')
                        sanction_status_value_stage = sanction_gt_response_body['content']['value'][
                            'stage']
                        sanction_status_value_bureau_fetch = sanction_gt_response_body['content']['value'][
                            'bureauFetchStatus']
                        query = sanction.update().where(sanction.c.customer_id == customer_id).values(
                            status=sanction_status_value_status,
                            stage=sanction_status_value_stage,
                            
                            bureau_fetch_status=sanction_status_value_bureau_fetch)
                        sanction_updated = await database.execute(query)
                        update_loan_info = await update_loan('SANCTION', sm_loan_id, '',
                                                             'Dedupe',
                                                             sanction_status_value_bureau_fetch,
                                                             'PROCEED', sanction_status_value_bureau_fetch)
                else:
                    logger.exception(f" Error from Northern Arc {sanction_gt_response_body}")
                    result = JSONResponse(status_code=500, content=sanction_gt_response_body)

            else:
                logger.exception(f" Error from Northern Arc {sanction_gt_response_body}")
                result = JSONResponse(status_code=500, content=sanction_gt_response_body)

        return database_record_fetch
    except Exception as e:
        logger.exception(f"Issue with update_sanction_in_db function, {e.args[0]}")
        result = JSONResponse(status_code=500, content={"message": f"Error Occurred at DB level - {e.args[0]}"})


@router.post("/disbursement/update-disbursement-in-db", tags=["Perdix"])
async def update_disbursement_in_db():
    try:
        database = get_database()
        database_record_fetch = await fetch_data_from_db(disbursement)
        print('coming inside update_disbursement_in_db ', database_record_fetch)
        for i in database_record_fetch:
            disbursement_ref_id = i[1]
            sanction_ref_id = i[8]
            customer_id = i[9]
            print('passing customer id to sanction ', customer_id)
            disbursement_sanction_id = await find_loan_id_from_sanction(customer_id)
            disbursement_sanction_id_status = hanlde_response_status(disbursement_sanction_id)
            disbursement_sanction_id_body = hanlde_response_body(disbursement_sanction_id)
            if(disbursement_sanction_id_status == 200):
                print('got the customer id from sanction', disbursement_sanction_id_body)
                sm_loan_id = disbursement_sanction_id_body.get('loanID')
                get_disbursement_response = await disbursement_get_status('disbursement', disbursement_ref_id)
                get_disbursement_response_status = hanlde_response_status(get_disbursement_response)
                get_disbursement_response_body = hanlde_response_body(get_disbursement_response)
                if(get_disbursement_response_status == 200):
                    print('SUCCESS 200 FROM ', get_disbursement_response_status, get_disbursement_response_body)
                    get_disbursement_response_content = get_disbursement_response_body['content']
                    get_disbursement_response_status = get_disbursement_response_body['content']['status']
                    if (get_disbursement_response_status == 'SUCCESS'):
                        print('SUCCSDFSKJSLF')
                        get_disbursement_response_stage = get_disbursement_response_body['content']['value']['stage']
                        print('disbursement response stage -', get_disbursement_response_stage)
                        if (get_disbursement_response_stage == 'AMOUNT_DISBURSEMENT'):
                            get_disbursement_response_utr = get_disbursement_response_body['content']['value']['utr']
                            get_disbursement_response_disbursement_status = \
                            get_disbursement_response_body['content']['value'][
                                'disbursementStatus']
                            query = disbursement.update().where(
                                disbursement.c.disbursement_reference_id == disbursement_ref_id).values(
                                status=get_disbursement_response_status,
                                stage=get_disbursement_response_stage,
                                disbursement_status=get_disbursement_response_disbursement_status,
                                message='',
                                utr=get_disbursement_response_utr)
                            disbursement_updated = await database.execute(query)
                            update_loan_info = await update_loan('DISBURSEMENT-ITR', sm_loan_id,
                                                                 get_disbursement_response_utr, 'Dedupe',
                                                                 get_disbursement_response_disbursement_status,
                                                                 'PROCEED',
                                                                 get_disbursement_response_disbursement_status)
                            print('disbursement response AMOUNT_DISBURSEMENT -', get_disbursement_response_utr,
                                  get_disbursement_response_disbursement_status)
                        else:
                            get_disbursement_response_disbursement_status = get_disbursement_response_body['content']['value']['disbursementStatus']
                            query = disbursement.update().where(
                                disbursement.c.disbursement_reference_id == disbursement_ref_id).values(
                                status=get_disbursement_response_status,
                                stage=get_disbursement_response_stage,
                                disbursement_status=get_disbursement_response_disbursement_status,
                                message='',
                                utr='')
                            disbursement_updated = await database.execute(query)
                            print('disbursement response AMOUNT_DISBURSEMENT -',
                                  get_disbursement_response_disbursement_status)
                    else:
                        if ("value" in get_disbursement_response_content):

                            get_disbursement_response_stage = get_disbursement_response_body['content']['value']['stage']
                            get_disbursement_response_value_status = get_disbursement_response_body['content']['value'][
                                'status']
                            query = disbursement.update().where(
                                disbursement.c.disbursement_reference_id == disbursement_ref_id).values(
                                status=get_disbursement_response_status,
                                stage=get_disbursement_response_stage,
                                disbursement_status=get_disbursement_response_value_status,
                                message='',
                                utr='')
                            disbursement_updated = await database.execute(query)
                            print('yes value is there', get_disbursement_response_stage,
                                  get_disbursement_response_value_status)
                            update_loan_info = await update_loan('DISBURSEMENT-ITR', sm_loan_id,
                                                                 '', 'Rejected',
                                                                 get_disbursement_response_stage,
                                                                 'PROCEED',
                                                                 get_disbursement_response_stage)
                        else:
                            get_disbursement_response_message = get_disbursement_response_body['content']['message']
                            query = disbursement.update().where(
                                disbursement.c.disbursement_reference_id == disbursement_ref_id).values(
                                status=get_disbursement_response_status,
                                stage='',
                                disbursement_status='',
                                message=get_disbursement_response_message,
                                utr='')
                            disbursement_updated = await database.execute(query)
                            print(' value is not there', get_disbursement_response_message)
                            update_loan_info = await update_loan('DISBURSEMENT-ITR', sm_loan_id,
                                                                 '', 'Rejected',
                                                                 get_disbursement_response_stage,
                                                                 'PROCEED',
                                                                 get_disbursement_response_stage)
                    result = database_record_fetch
                else:
                    logger.exception(f" Error from update_disbursement_in_db {get_disbursement_response_body}")
                    result = JSONResponse(status_code=500, content=get_disbursement_response_body)
            else:
                logger.exception(f"NOT GOT the customer id from update_disbursement_in_db sanction {disbursement_sanction_id_body}")
                result = JSONResponse(status_code=500, content=disbursement_sanction_id_body)
                continue

    except Exception as e:
        logger.exception(f"Issue with update_sanction_in_db function, {e.args[0]}")
        result = JSONResponse(status_code=500, content={"message": f"Error Occurred at DB level - {e.args[0]}"})
    return result