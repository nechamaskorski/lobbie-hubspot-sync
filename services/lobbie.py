import requests
import base64
import time
from config import (
    LOBBIE_CLIENT_ID,
    LOBBIE_CLIENT_SECRET,
    LOBBIE_AUTH_URL,
    LOBBIE_API_URL,
    LOBBIE_INTAKE_FORM_EN,
    LOBBIE_CONSENT_FORM_EN,
    LOBBIE_INTAKE_FORM_ES,
    LOBBIE_CONSENT_FORM_ES,
)


def get_access_token():
    """Get a Lobbie access token using client credentials."""
    credentials = f"{LOBBIE_CLIENT_ID}:{LOBBIE_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    response = requests.post(
        LOBBIE_AUTH_URL,
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def search_patient_by_email(token, email):
    """Search for an existing Lobbie patient by email."""
    response = requests.get(
        f"{LOBBIE_API_URL}/patients/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"email": email},
    )
    response.raise_for_status()
    results = response.json().get("data", [])
    return results[0] if results else None


def search_patient(token, first_name, last_name, dob=None):
    """Search for an existing Lobbie patient by name and optionally DOB."""
    params = {"firstName": first_name, "lastName": last_name}
    if dob:
        params["dateOfBirth"] = dob
    response = requests.get(
        f"{LOBBIE_API_URL}/patients/search",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def create_patient(token, patient_data):
    """Create a single patient in Lobbie."""
    response = requests.post(
        f"{LOBBIE_API_URL}/patients/batch",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"patients": [patient_data]},
    )
    if not response.ok:
        print(f"LOBBIE CREATE PATIENT ERROR: {response.text}")
    response.raise_for_status()
    results = response.json()
    if isinstance(results, list) and results:
        if results[0].get("status") == "error":
            raise ValueError(f"Failed to create patient: {results[0].get('error')}")
        return results[0]
    raise ValueError("Unexpected response from Lobbie patient creation")


def create_patient_relationship(token, parent_id, child_id):
    """Create a parent/child relationship between two Lobbie patients."""
    response = requests.post(
        f"{LOBBIE_API_URL}/patients/relationships",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "relationships": [{
                "parentId": parent_id,
                "childId": child_id,
                "parentRelationshipName": "Guardian",
                "childRelationshipName": "Child",
                "primary": True,
            }]
        },
    )
    response.raise_for_status()
    results = response.json()
    if isinstance(results, list) and results:
        if results[0].get("status") == "error":
            # Relationship may already exist, log but don't fail
            print(f"Relationship warning: {results[0].get('error')}")
    return results


def send_intake_form(lead_name, dob, gender, parent_first_name, parent_last_name, email, location_id, due_date_unix, spanish_speaking=False):
    """Create a Form Group/Packet in Lobbie and send intake form to patient."""
    token = get_access_token()

    if spanish_speaking:
        form_template_ids = [LOBBIE_INTAKE_FORM_ES, LOBBIE_CONSENT_FORM_ES]
    else:
        form_template_ids = [LOBBIE_INTAKE_FORM_EN, LOBBIE_CONSENT_FORM_EN]

    # Split lead name on last space to handle middle names
    prefill = {}
    child_first = ""
    child_last = ""
    if lead_name:
        parts = lead_name.rsplit(" ", 1)
        if len(parts) == 2:
            child_first = parts[0]
            child_last = parts[1]
            prefill["first_name"] = child_first
            prefill["last_name"] = child_last
        else:
            child_first = lead_name
            prefill["first_name"] = lead_name

    if dob:
        prefill["date_of_birth"] = dob
    if parent_first_name:
        prefill["parent_legal_guardian_first_name"] = parent_first_name
    if parent_last_name:
        prefill["parent_legal_guardian_last_name"] = parent_last_name

    # Step 1: Find or create parent patient
    parent = search_patient_by_email(token, email)
    if not parent:
        parent = create_patient(token, {
            "firstName": parent_first_name or "",
            "lastName": parent_last_name or "",
            "email": email,
        })
    parent_id = parent["id"]
    time.sleep(1)  # prevent Lobbie dedup collision


    

    # Step 2: Find or create child patient
    child = None
    if child_first and dob:
        results = search_patient(token, first_name=child_first, last_name=child_last, dob=dob)

        if results:
            non_parent = [r for r in results if r["id"] != parent_id]
            if non_parent:
                child = non_parent[0]

    if not child:
        child_payload = {
            "firstName": child_first or "",
            "lastName": child_last or "",
        }
        if dob:
            child_payload["dateOfBirth"] = dob
        if gender:
            child_payload["gender"] = gender

        child = create_patient(token, child_payload)


    child_id = child["id"]


    # Step 3: Create parent/child relationship
    create_patient_relationship(token, parent_id, child_id)

    # Step 4: Create form packet assigned to child
    payload = {
        "formTemplateIds": form_template_ids,
        "locationId": location_id,
        "dueDateUnix": due_date_unix,
        "patient": {"id": child_id},
        "prefill": prefill,
    }


    response = requests.post(
        f"{LOBBIE_API_URL}/forms/groups",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    response.raise_for_status()
    return response.json()


def create_pdf(form_group_id):
    """Request Lobbie to generate a PDF for a form group."""
    token = get_access_token()
    response = requests.post(
        f"{LOBBIE_API_URL}/forms/pdf/create",
        headers={"Authorization": f"Bearer {token}"},
        json={"formGroupId": form_group_id, "isPatient": True},
    )
    response.raise_for_status()
    return response.json()


def retrieve_pdf(s3_object_path):
    """Retrieve the signed URL for a generated PDF."""
    token = get_access_token()
    response = requests.post(
        f"{LOBBIE_API_URL}/forms/pdf/retrieve",
        headers={"Authorization": f"Bearer {token}"},
        json={"s3ObjectPath": s3_object_path},
    )
    response.raise_for_status()
    return response.json()


def get_pdf(form_group_id):
    """Get the PDF content for a completed form group."""
    token = get_access_token()

    create_response = requests.post(
        f"{LOBBIE_API_URL}/forms/pdf/create",
        headers={"Authorization": f"Bearer {token}"},
        json={"formGroupId": form_group_id, "isPatient": True},
    )
    create_response.raise_for_status()
    s3_path = create_response.json().get("data", {}).get("s3ObjectPath")
    if not s3_path:
        raise ValueError("No s3ObjectPath returned from Lobbie")

    # Retry up to 5 times with 5 second delays
    for attempt in range(5):
        time.sleep(5)
        retrieve_response = requests.post(
            f"{LOBBIE_API_URL}/forms/pdf/retrieve",
            headers={"Authorization": f"Bearer {token}"},
            json={"s3ObjectPath": s3_path},
        )
        retrieve_response.raise_for_status()
        signed_url = retrieve_response.json().get("data", {}).get("signedURL")
        if signed_url:
            pdf_response = requests.get(signed_url)
            pdf_response.raise_for_status()
            return pdf_response.content

    raise ValueError("PDF generation timed out after 5 attempts")