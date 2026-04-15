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