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
        params={"properties": "hs_lead_status,service_state,hs_lead_name,dob,spanish_intake_packet,gender,home_phone,street_address,city,state_region_code,postal_code,diagnosing_dr,referral_source,scho,desired_times_of_services,attachments,gclid"},
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
        params={"properties": "firstname,lastname,email,phone"},
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

def update_lead_lobbie_form_group_id(lead_id, form_group_id, patient_form_url=None):
    """Write Lobbie form group ID (and optionally patient form URL) back to the Lead."""
    properties = {"lobbie_form_group_id": str(form_group_id)}
    if patient_form_url:
        properties["lobbie_patient_form_url"] = patient_form_url
    response = requests.patch(
        f"{BASE_URL}/crm/v3/objects/leads/{lead_id}",
        headers=HEADERS,
        json={"properties": properties},
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

def associate_deal(deal_id, object_type, object_id, association_type_id, association_category="HUBSPOT_DEFINED"):
    """Associate a Deal with another object in HubSpot.
    Use association_category='USER_DEFINED' for custom object associations."""
    response = requests.put(
        f"{BASE_URL}/crm/v4/objects/deals/{deal_id}/associations/{object_type}/{object_id}",
        headers=HEADERS,
        json=[{"associationCategory": association_category, "associationTypeId": association_type_id}],
    )
    response.raise_for_status()
    return response.json()

def get_client_from_lead(lead_id):
    """Get the Client custom object ID associated to a Lead."""
    response = requests.get(
        f"{BASE_URL}/crm/v4/objects/leads/{lead_id}/associations/2-47660783",
        headers= HEADERS
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return None
    return results[0].get("toObjectId")


def get_client_properties(client_id):
    """Get properties from a HubSpot Client custom object."""
    response = requests.get(
        f"{BASE_URL}/crm/v3/objects/2-47660783/{client_id}",
        headers=HEADERS,
        params={"properties": "primary_insurance,secondary_insurance,service_state"},
    )
    response.raise_for_status()
    return response.json().get("properties", {})

def get_lead_notes(lead_id):
    """Fetch all notes associated to a Lead."""
    response = requests.get(
        f"{BASE_URL}/crm/v4/objects/leads/{lead_id}/associations/notes",
        headers=HEADERS,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return [r.get("toObjectId") for r in results if r.get("toObjectId")]


def get_note(note_id):
    """Fetch a single note with body and author details."""
    response = requests.get(
        f"{BASE_URL}/crm/v3/objects/notes/{note_id}",
        headers=HEADERS,
        params={"properties": "hs_note_body,hs_created_by_user_id,hs_createdate"},
    )
    response.raise_for_status()
    return response.json().get("properties", {})


def get_attachment_signed_url(file_id):
    """Get a signed download URL for a HubSpot file attachment."""
    response = requests.get(
        f"{BASE_URL}/files/v3/files/{file_id}/signed-url",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json().get("url")

def get_lead_owner_email(lead_id):
    """Get the email of the HubSpot user who owns the Lead."""
    response = requests.get(
        f"{BASE_URL}/crm/v3/objects/leads/{lead_id}",
        headers=HEADERS,
        params={"properties": "hubspot_owner_id"},
    )
    response.raise_for_status()
    owner_id = response.json().get("properties", {}).get("hubspot_owner_id")
    if not owner_id:
        return None

    owner_response = requests.get(
        f"{BASE_URL}/crm/v3/owners/{owner_id}",
        headers=HEADERS,
    )
    owner_response.raise_for_status()
    return owner_response.json().get("email")

def get_contact_from_client(client_id):
    """Get the Parent/Guardian Contact ID associated to a Client custom object."""
    response = requests.get(
        f"{BASE_URL}/crm/v4/objects/2-47660783/{client_id}/associations/contacts",
        headers=HEADERS,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return None
    # Only consider Parent/Guardian associations (typeId=48), not Referring Provider etc.
    for result in results:
        association_types = result.get("associationTypes", [])
        for assoc_type in association_types:
            if assoc_type.get("typeId") == 48:
                return result.get("toObjectId")
    return None


def associate_client_to_contact(client_id, contact_id):
    """Associate a Client custom object to a Contact (Parent/Guardian, typeId=48)."""
    response = requests.put(
        f"{BASE_URL}/crm/v4/objects/2-47660783/{client_id}/associations/contacts/{contact_id}",
        headers=HEADERS,
        json=[{"associationCategory": "USER_DEFINED", "associationTypeId": 48}],
    )
    response.raise_for_status()
    return response.json()


def post_note_on_client(client_id, note_body):
    """Post a note on a Client custom object."""
    response = requests.post(
        f"{BASE_URL}/crm/v3/objects/notes",
        headers=HEADERS,
        json={
            "properties": {
                "hs_note_body": note_body,
                "hs_timestamp": str(int(__import__("time").time() * 1000)),
            },
            "associations": [
                {
                    "to": {"id": client_id},
                    "types": [{"associationCategory": "USER_DEFINED", "associationTypeId": 33}],
                }
            ],
        },
    )
    response.raise_for_status()
    return response.json()