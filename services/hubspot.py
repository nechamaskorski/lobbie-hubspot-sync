import requests
from config import HUBSPOT_API_TOKEN

HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_API_TOKEN}",
    "Content-Type": "application/json",
}
BASE_URL = "https://api.hubapi.com"


def get_lead_with_contact(lead_id):
    """Get a Lead and its associated Contact properties."""
    # Get lead properties
    response = requests.get(
        f"{BASE_URL}/crm/v3/objects/leads/{lead_id}",
        headers=HEADERS,
        params={"properties": "hs_lead_status,service_state,hs_lead_name,dob,spanish_intake_packet"},
    )
    response.raise_for_status()
    lead = response.json()

    # Get associated contact ID
    assoc_response = requests.get(
        f"{BASE_URL}/crm/v3/objects/leads/{lead_id}/associations/contacts",
        headers=HEADERS,
    )
    assoc_response.raise_for_status()
    associations = assoc_response.json().get("results", [])

    if not associations:
        return lead, None

    contact_id = associations[0]["id"]

    # Get contact properties
    contact_response = requests.get(
        f"{BASE_URL}/crm/v3/objects/contacts/{contact_id}",
        headers=HEADERS,
        params={"properties": "firstname,lastname,email"},
    )
    contact_response.raise_for_status()
    contact = contact_response.json()

    return lead, contact


def update_lead_status(lead_id, status):
    """Update the status of a Lead in HubSpot."""
    response = requests.patch(
        f"{BASE_URL}/crm/v3/objects/leads/{lead_id}",
        headers=HEADERS,
        json={"properties": {"hs_pipeline_stage": status}},
    )
    response.raise_for_status()
    return response.json()

def update_lead_lobbie_form_group_id(lead_id, form_group_id):
    """Write Lobbie form group ID back to the Lead."""
    response = requests.patch(
        f"{BASE_URL}/crm/v3/objects/leads/{lead_id}",
        headers=HEADERS,
        json={"properties": {"lobbie_form_group_id": str(form_group_id)}},
    )
    response.raise_for_status()
    return response.json()


def find_lead_by_lobbie_form_group_id(form_group_id):
    """Search for a Lead by Lobbie form group ID."""
    response = requests.post(
        f"{BASE_URL}/crm/v3/objects/leads/search",
        headers=HEADERS,
        json={
            "filterGroups": [{
                "filters": [{
                    "propertyName": "lobbie_form_group_id",
                    "operator": "EQ",
                    "value": str(form_group_id)
                }]
            }],
            "properties": ["hs_lead_status", "lobbie_form_group_id"]
        }
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0] if results else None


def create_deal(child_name, pipeline_id, stage_id):
    """Create a new Deal in HubSpot."""
    response = requests.post(
        f"{BASE_URL}/crm/v3/objects/deals",
        headers=HEADERS,
        json={
            "properties": {
                "dealname": child_name,
                "pipeline": pipeline_id,
                "dealstage": stage_id,
            }
        },
    )
    response.raise_for_status()
    return response.json()

def update_deal_clickup_id(deal_id, clickup_task_id):
    """Store ClickUp task ID on the HubSpot Deal."""
    response = requests.patch(
        f"{BASE_URL}/crm/v3/objects/deals/{deal_id}",
        headers=HEADERS,
        json={"properties": {"clickup_id": str(clickup_task_id)}},
    )
    response.raise_for_status()
    return response.json()