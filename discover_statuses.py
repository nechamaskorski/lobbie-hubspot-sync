import requests
from config import CLICKUP_API_TOKEN, CLICKUP_CLIENTS_LIST_IDS

HEADERS = {"Authorization": CLICKUP_API_TOKEN}
BASE_URL = "https://api.clickup.com/api/v2"

for state, list_id in CLICKUP_CLIENTS_LIST_IDS.items():
    response = requests.get(f"{BASE_URL}/list/{list_id}/field", headers=HEADERS).json()
    print(f"\n{state}:")
    for field in response.get("fields", []):
        if "intake status" in field["name"].lower():
            print(f"  Field: '{field['name']}' (id: {field['id']})")
            for option in field.get("type_config", {}).get("options", []):
                if "intake packet received" in option["name"].lower():
                    print(f"  Option: '{option['name']}' (id: {option['id']})")