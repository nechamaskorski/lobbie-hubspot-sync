import requests
import time
import base64
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


def send_intake_form(lead_name, dob, parent_first_name, parent_last_name, email, location_id, due_date_unix, spanish_speaking=False):

    token = get_access_token()

    if spanish_speaking:
        form_template_ids = [LOBBIE_INTAKE_FORM_ES, LOBBIE_CONSENT_FORM_ES]
    else:
        form_template_ids = [LOBBIE_INTAKE_FORM_EN, LOBBIE_CONSENT_FORM_EN]

    # Split lead name on last space to handle middle names
    prefill = {}
    if lead_name:
        parts = lead_name.rsplit(" ", 1)
        if len(parts) == 2:
            prefill["first_name"] = parts[0]
            prefill["last_name"] = parts[1]
        else:
            prefill["first_name"] = lead_name

    if dob:
        prefill["date_of_birth"] = dob
    if parent_first_name:
        prefill["parent_legal_guardian_first_name"] = parent_first_name
    if parent_last_name:
        prefill["parent_legal_guardian_last_name"] = parent_last_name

    payload = {
        "formTemplateIds": form_template_ids,
        "locationId": location_id,
        "dueDateUnix": due_date_unix,
        "patient": {
            "firstName": prefill.get("first_name", ""),
            "lastName": prefill.get("last_name", ""),
            "email": email,
        },
        "prefill": prefill,
    }

    print("LOBBIE PAYLOAD:", payload)

    response = requests.post(
        f"{LOBBIE_API_URL}/forms/groups",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    print("LOBBIE STATUS:", response.status_code)
    print("LOBBIE RESPONSE:", response.text)
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
        print(f"PDF RETRIEVE ATTEMPT {attempt + 1}:", retrieve_response.json())
        signed_url = retrieve_response.json().get("data", {}).get("signedURL")
        if signed_url:
            pdf_response = requests.get(signed_url)
            pdf_response.raise_for_status()
            return pdf_response.content

    raise ValueError("PDF generation timed out after 5 attempts")