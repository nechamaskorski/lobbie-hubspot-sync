import os
from dotenv import load_dotenv

load_dotenv()

# HubSpot
HUBSPOT_API_TOKEN = os.getenv("HUBSPOT_API_TOKEN")

# Lobbie
LOBBIE_CLIENT_ID = os.getenv("LOBBIE_CLIENT_ID")
LOBBIE_CLIENT_SECRET = os.getenv("LOBBIE_CLIENT_SECRET")
LOBBIE_AUTH_URL = "https://auth.lobbie.com/oauth2/token"
LOBBIE_API_URL = "https://api.lobbie.com/lobbie/api/developer/v1"

# Location mapping: HubSpot Service State -> Lobbie Location ID
LOBBIE_LOCATION_IDS = {
    "CO": 1984,
    "GA": 1985,
    "IN": 1986,
    "MD": 1987,
    "NE": 1988,
    "NC": 1989,
    "OK": 1990,
    "UT": 1991,
    "VA": 1992,
}

# Form Templates
# Form Templates - English
LOBBIE_INTAKE_FORM_EN = 50376
LOBBIE_CONSENT_FORM_EN = 50953

# Form Templates - Spanish
LOBBIE_INTAKE_FORM_ES = 51311
LOBBIE_CONSENT_FORM_ES = 51388

# HubSpot Lead Pipeline Stages
HS_LEAD_STAGE_INTAKE_PACKET_SENT = "qualified-stage-id"
HS_LEAD_STAGE_INTAKE_PACKET_RECEIVED = "1266942855"

HS_DEAL_PIPELINE_ID = "765893784"
HS_DEAL_STAGE_INTAKE_PACKET_RECEIVED = "1117260801"


CLICKUP_API_TOKEN = os.getenv("CLICKUP_API_TOKEN")
CLICKUP_WORKSPACE_ID = "36079957"

CLICKUP_CLIENTS_LIST_IDS = {
    "CO": "901704855142",
    "GA": "901702254321",
    "IN": "901702886702",
    "MD": "901709170565",
    "NE": "900303547779",
    "NC": "901701488982",
    "OK": "901701944690",
    "UT": "901702616323",
    "VA": "901703823521",
}

CLICKUP_INTAKE_STATUS_FIELDS = {
    "CO": {"field_id": "4f2243e6-5fc9-4d6c-b1c1-9ac589d34a60", "option_id": "e6459b29-d7eb-47bc-b25e-f425450d4c22"},
    "GA": {"field_id": "716f00c9-cefa-4cc3-8c44-743bdac58af6", "option_id": "e9873d31-7cc0-4be6-b12d-eec9e1d4a208"},
    "IN": {"field_id": "b62c4f0a-8982-41d4-bf6e-a687e286fe33", "option_id": "31c3bed2-f078-4203-b6fa-7cdb2c046778"},
    "MD": {"field_id": "a5e0644d-94b7-405f-b659-42e5560d8cad", "option_id": "bb5842ee-f961-42cc-9f9e-7aac9db0f274"},
    "NE": {"field_id": "3fa5c694-1195-408c-88f1-3c5a47d7bcb2", "option_id": "b33f38ef-8eba-4e84-a3f8-dd685aa91c08"},
    "NC": {"field_id": "3e55cf63-b797-4cdd-9a41-17813f413aa3", "option_id": "b82555a5-6376-4bc9-908d-fb443572dffd"},
    "OK": {"field_id": "762401d2-0e5f-4a18-b59c-88a975228507", "option_id": "ea22423f-6e04-4a5d-bef0-9097b255e3ef"},
    "UT": {"field_id": "8af523af-f153-46d3-8727-5db10f21293c", "option_id": "244ff2c8-2af7-474a-86a5-1fa74e07bab9"},
    "VA": {"field_id": "81b055cc-5e87-478b-9377-d5fde5d550a2", "option_id": "68f7dead-da66-4e59-af6e-bea6bb257ed4"},
}