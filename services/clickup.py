import requests
from config import CLICKUP_API_TOKEN, CLICKUP_CLIENTS_LIST_IDS

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

    payload = {
        "name": child_name,
        "status": "Intake Packet Received",
    }

    response = requests.post(
        f"{BASE_URL}/list/{list_id}/task",
        headers=HEADERS,
        json=payload,
    )
    response.raise_for_status()
    return response.json()