import requests
from config import HUBSPOT_API_TOKEN

HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_API_TOKEN}",
    "Content-Type": "application/json"
}

# Get all association types between deals and contacts
response = requests.get(
    "https://api.hubapi.com/crm/v4/associations/deals/contacts/labels",
    headers=HEADERS
)
print("DEAL -> CONTACT ASSOCIATIONS:")
for label in response.json().get("results", []):
    print(f"  {label['label']} (typeId: {label['typeId']}, category: {label['category']})")

# Get all association types between deals and leads
response = requests.get(
    "https://api.hubapi.com/crm/v4/associations/deals/leads/labels",
    headers=HEADERS
)
print("\nDEAL -> LEAD ASSOCIATIONS:")
for label in response.json().get("results", []):
    print(f"  {label['label']} (typeId: {label['typeId']}, category: {label['category']})")