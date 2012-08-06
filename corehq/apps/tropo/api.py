import logging
from urllib import urlencode
from urllib2 import urlopen

API_ID = "TROPO"

BILLABLE_ITEM = 'TropoSMSBillableItem'

def send(msg, delay=True, *args, **kwargs):
    """
    Expected kwargs:
        messaging_token
    """
    phone_number = msg.phone_number
    if phone_number[0] != "+":
        phone_number = "+" + phone_number
    params = urlencode({
        "action" : "create"
       ,"token" : kwargs["messaging_token"]
       ,"numberToDial" : phone_number
       ,"msg" : msg.text
       ,"_send_sms" : "true"
    })
    url = "https://api.tropo.com/1.0/sessions?%s" % params
    response = urlopen(url).read()

    try:
        # attempt to bill client
        from hqpayments.tasks import bill_client_for_sms
        if delay:
            bill_client_for_sms.delay(BILLABLE_ITEM, msg, **dict(response=response))
        else:
            bill_client_for_sms(BILLABLE_ITEM, msg, **dict(response=response))
    except Exception as e:
        logging.debug("TROPO API contacted, errors in billing. Error: %s" % e)

    return response

