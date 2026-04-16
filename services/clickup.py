import requests
from config import CLICKUP_API_TOKEN, CLICKUP_CLIENTS_LIST_IDS, CLICKUP_INTAKE_STATUS_FIELDS

HEADERS = {
    "Authorization": CLICKUP_API_TOKEN,
    "Content-Type": "application/json"
}
BASE_URL = "https://api.clickup.com/api/v2"


def create_intake_task(child_name, service_state):
    """Create a new intake task in the correct ClickUp list."""
    list_id = CLICKUP_CLIENTS_LIST_IDS.get(service_state)
    if not list_id:
        raise ValueError(f"No ClickUp list found for state: {service_state}")

    # Create the task
    response = requests.post(
        f"{BASE_URL}/list/{list_id}/task",
        headers=HEADERS,
        json={"name": child_name},
    )
    print("CLICKUP STATUS:", response.status_code)
    print("CLICKUP RESPONSE:", response.text)
    response.raise_for_status()
    task = response.json()
    task_id = task.get("id")

    # Set Intake Status custom field
    field_info = CLICKUP_INTAKE_STATUS_FIELDS.get(service_state)
    if field_info:
        field_response = requests.post(
            f"{BASE_URL}/task/{task_id}/field/{field_info['field_id']}",
            headers=HEADERS,
            json={"value": field_info["option_id"]},
        )
        print("CLICKUP FIELD STATUS:", field_response.status_code)
        print("CLICKUP FIELD RESPONSE:", field_response.text)

    return task