import requests
import phonenumbers
from config import CLICKUP_CLIENTS_LIST_IDS, CLICKUP_INTAKE_STATUS_FIELDS
import os
import time

BASE_URL = "https://api.clickup.com/api/v2"
HEADERS = {"Authorization": os.getenv("CLICKUP_API_TOKEN")}


def format_phone_e164(phone):
    """Format a phone number to E.164 format. Returns empty string if invalid."""
    if not phone:
        return ""
    try:
        parsed = phonenumbers.parse(phone, "US")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return ""


def geocode_address(street, city, state, postal_code):
    """Geocode an address using Google Maps API. Returns (lat, lng, formatted_address) or None."""
    if not all([street, city, state]):
        return None
    try:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        address = f"{street}, {city}, {state} {postal_code or ''}"
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": address, "key": api_key},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return None
        location = results[0]["geometry"]["location"]
        formatted = results[0]["formatted_address"]
        return location["lat"], location["lng"], formatted
    except Exception:
        return None


def find_dropdown_option_id(custom_fields, field_id, option_name):
    """Find a ClickUp dropdown option ID by matching the option name exactly."""
    if not option_name:
        return None
    for field in custom_fields:
        if field.get("id") == field_id:
            for option in field.get("type_config", {}).get("options", []):
                if option.get("name", "").strip().lower() == option_name.strip().lower():
                    return option.get("id")
    return None


def get_list_custom_fields(list_id):
    """Fetch all custom fields for a ClickUp list."""
    response = requests.get(
        f"{BASE_URL}/list/{list_id}/field",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json().get("fields", [])


def create_intake_task(child_name, service_state, lead_props=None, contact_props=None, client_props=None):
    """Create a new intake task in the correct ClickUp list and populate all custom fields."""
    lead_props = lead_props or {}
    contact_props = contact_props or {}
    client_props = client_props or {}

    list_id = CLICKUP_CLIENTS_LIST_IDS.get(service_state)
    if not list_id:
        raise ValueError(f"No ClickUp list found for state: {service_state}")

    # Fetch custom fields for this list (needed for insurance dropdown matching)
    custom_fields = get_list_custom_fields(list_id)

    # Format phone number to E.164
    raw_phone = lead_props.get("home_phone") or contact_props.get("phone")
    phone_e164 = format_phone_e164(raw_phone)

    # Format DOB as unix timestamp (milliseconds)
    dob_unix = ""
    dob = lead_props.get("dob")
    if dob:
        try:
            from datetime import datetime
            dob_unix = int(datetime.strptime(dob, "%Y-%m-%d").timestamp() * 1000)
        except Exception:
            dob_unix = ""

    # Geocode address
    geo = geocode_address(
        lead_props.get("street_address"),
        lead_props.get("city"),
        lead_props.get("state_region_code"),
        lead_props.get("postal_code"),
    )

    # Match insurance dropdown option IDs by name
    primary_insurance_id = find_dropdown_option_id(
        custom_fields, "7af7afaa-398c-46e2-91ea-8776bd38580f",
        client_props.get("primary_insurance")
    )
    secondary_insurance_id = find_dropdown_option_id(
        custom_fields, "68467317-ba50-4b29-ba24-527fc77faa48",
        client_props.get("secondary_insurance")
    )

    # Map gender to ClickUp option ID
    gender_map = {
        "male": "1d7bfea1-9e5f-4790-9469-6dcdec59fa2b",
        "female": "4fad9fe5-f41c-426d-9825-e6148a968429",
    }
    gender_id = gender_map.get((lead_props.get("gender") or "").lower())

    # Map state to ClickUp option ID
    state_option_map = {
        "Georgia": "afd738ac-977f-4067-ac32-67ad64af38ac",
        "Indiana": "7d42d082-2836-49c7-a555-b7d4adb5dcb2",
        "Nebraska": "62eff579-0b58-41dd-9b92-01d29aa690c6",
        "North Carolina": "0df348db-2dbc-4e31-81ea-c557438ff0b4",
        "Oklahoma": "618c0752-c00d-48fa-94b7-a1bffb854174",
        "Utah": "d553f653-3ffa-4f34-9829-42e5352d8ded",
        "Virginia": "6d716ed5-255a-413c-8b64-f785efbac1e2",
        "Colorado": "c625f029-00c5-4e2e-8505-ed10f8d71ff1",
        "Maryland": "9dbac72a-6247-4c6a-828e-97c4b457bfa9",
    }
    # Map 2-letter state code to full name for the dropdown
    state_code_to_name = {
        "GA": "Georgia", "IN": "Indiana", "NE": "Nebraska", "NC": "North Carolina",
        "OK": "Oklahoma", "UT": "Utah", "VA": "Virginia", "CO": "Colorado", "MD": "Maryland",
    }
    state_full = state_code_to_name.get(service_state, "")
    state_option_id = state_option_map.get(state_full)

    # Parse desired times of services (semicolon separated in HubSpot)
    desired_times_labels = []
    desired_times_raw = lead_props.get("desired_times_of_services", "")
    time_label_map = {
        "Morning": "71370cdd-a086-48ad-a90e-4b671a29daa9",
        "Afternoon": "c738c5b7-065a-469d-b07c-b46fd3bd46e5",
        "Evening": "e560f169-4249-4ef9-9cc3-a79a7181a50b",
        "Clinic": "a341c249-e043-4278-84ac-8f5e131dbf7e",
        "School": "ab7b4b5b-be62-4c46-be97-16c665e53e45",
    }
    if desired_times_raw:
        for t in desired_times_raw.split(";"):
            label_id = time_label_map.get(t.strip())
            if label_id:
                desired_times_labels.append(label_id)

    # Build custom fields list
    custom_field_values = [
        {"id": "b40a93c9-2d97-438e-8a89-62ca8ac49419", "value": contact_props.get("email", "")},
        {"id": "9bf1f0c8-d0b1-4fa2-9e0f-a90746b69ada", "value": f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip()},
        {"id": "7310f284-928d-4b84-908e-4528853f4584", "value": phone_e164},
        {"id": "ee25221e-e205-4c35-88a0-6dfc6308eb57", "value": child_name or ""},
        {"id": "9292b969-1d79-4d31-b11e-ff5733f2b10a", "value": lead_props.get("diagnosing_dr", "")},
        {"id": "794cc859-b961-4767-b8b4-0976466053f1", "value": lead_props.get("scho", "")},
        {"id": "baee30e1-630d-431b-8ad1-a6d2a6b4b98f", "value": lead_props.get("gclid", "")},
        {"id": "7254b06d-8e9b-47d1-92f5-d65027f69b21", "value": lead_props.get("spanish_intake_packet") == "true"},
    ]

    # Only add fields with actual values to avoid overwriting with nulls
    if dob_unix:
        custom_field_values.append({"id": "72112b20-989a-48ab-a3c8-66caa84b1413", "value": dob_unix})
    if gender_id:
        custom_field_values.append({"id": "983c443c-a81d-49ab-af9d-c350afc90722", "value": gender_id})
    if state_option_id:
        custom_field_values.append({"id": "0a9f6b4e-b0ef-4875-a171-5c82b2d5d114", "value": state_option_id})
    if primary_insurance_id:
        custom_field_values.append({"id": "7af7afaa-398c-46e2-91ea-8776bd38580f", "value": primary_insurance_id})
    if secondary_insurance_id:
        custom_field_values.append({"id": "68467317-ba50-4b29-ba24-527fc77faa48", "value": secondary_insurance_id})
    if desired_times_labels:
        custom_field_values.append({"id": "f5a7d88f-dce0-4f6d-b0b9-9f1464b06812", "value": desired_times_labels})

    # Create the task with all custom fields
    response = requests.post(
        f"{BASE_URL}/list/{list_id}/task",
        headers=HEADERS,
        json={
            "name": child_name,
            "custom_fields": custom_field_values,
        },
    )
    response.raise_for_status()
    task = response.json()
    task_id = task.get("id")

    # Set Intake Status custom field separately (as before)
    field_info = CLICKUP_INTAKE_STATUS_FIELDS.get(service_state)
    if field_info:
        requests.post(
            f"{BASE_URL}/task/{task_id}/field/{field_info['field_id']}",
            headers=HEADERS,
            json={"value": field_info["option_id"]},
        )

    # Set address location field if geocoding succeeded
    if geo:
        lat, lng, formatted_address = geo
        requests.post(
            f"{BASE_URL}/task/{task_id}/field/5c246050-bc96-42c0-b319-15a17981d6f0",
            headers=HEADERS,
            json={"value": {"location": {"lat": lat, "lng": lng}, "formatted_address": formatted_address}},
        )

    return task

def upload_file_to_task(task_id, file_content, filename="attachment"):
    """Upload a file as an attachment to a ClickUp task."""
    for attempt in range(3):
        try:
            response = requests.post(
                f"{BASE_URL}/task/{task_id}/attachment",
                headers={"Authorization": os.getenv("CLICKUP_API_TOKEN")},
                files={"attachment": (filename, file_content)},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2)

def post_task_comment(task_id, comment):
    """Post a comment on a ClickUp task."""
    response = requests.post(
        f"{BASE_URL}/task/{task_id}/comment",
        headers=HEADERS,
        json={"comment_text": comment, "notify_all": False},
    )
    response.raise_for_status()
    return response.json()

def update_clickup_insurance_fields(task_id, insurance_fields):
    """Update insurance text fields on a ClickUp task from Lobbie form answers."""
    field_map = {
        "insurance_company": "7b129add-1987-4230-803e-644f7b42f8b5",       # Insurance - Intake Packet
        "insurance_id": "c4acc13d-8618-49b4-8b35-d3420c8a2025",             # Insurance ID
        "policyholder": "30e7adcf-ed06-4418-89fd-eb42e37c72f7",             # Policyholder
        "secondary_insurance_company": "2aeed84d-3076-4182-b3a0-60c480208f96",  # Secondary Insurance - Intake Packet
        "secondary_insurance_id": "397ddcdc-ee5d-448b-b6b6-fb7df2c4478a",   # Secondary Insurance ID
        "secondary_policyholder": "0f6fb32d-0239-472d-91d3-0b7861033558",   # Secondary Policyholder
    }
    for key, field_id in field_map.items():
        value = insurance_fields.get(key, "")
        if value:
            try:
                requests.post(
                    f"{BASE_URL}/task/{task_id}/field/{field_id}",
                    headers=HEADERS,
                    json={"value": value},
                )
            except Exception as e:
                print(f"Failed to update ClickUp field {field_id}: {e}")