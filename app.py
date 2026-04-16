import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from services.lobbie import send_intake_form
from services.hubspot import get_lead_with_contact, update_lead_status, update_lead_lobbie_form_group_id, find_lead_by_lobbie_form_group_id
from services.clickup import create_intake_task
from config import LOBBIE_LOCATION_IDS, LOBBIE_INTAKE_FORM_EN, LOBBIE_CONSENT_FORM_EN, LOBBIE_INTAKE_FORM_ES, LOBBIE_CONSENT_FORM_ES, HS_LEAD_STAGE_INTAKE_PACKET_RECEIVED
app = Flask(__name__)


def get_due_date_unix(days=7):
    """Return unix timestamp for X days from now."""
    return int((datetime.utcnow() + timedelta(days=days)).timestamp() * 1000)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/send-intake", methods=["POST"])
def send_intake():
    """
    Triggered by HubSpot workflow when Lead reaches 'Intake Packet Sent'.
    Expects JSON: { "lead_id": "123" }
    """
    data = request.get_json()
    lead_id = data.get("lead_id")

    if not lead_id:
        return jsonify({"error": "lead_id is required"}), 400

    # Get lead and associated contact from HubSpot
    lead, contact = get_lead_with_contact(lead_id)

    if not contact:
        return jsonify({"error": "No associated contact found for lead"}), 400

    lead_props = lead.get("properties", {})
    contact_props = contact.get("properties", {}) if contact else {}

    lead_name = lead_props.get("hs_lead_name")
    dob = lead_props.get("dob")
    service_state = lead_props.get("service_state")
    parent_first_name = contact_props.get("firstname")
    parent_last_name = contact_props.get("lastname")
    email = contact_props.get("email")
  
    # Validate required fields
    if not all([email, service_state]):
        return jsonify({"error": "Missing required properties"}), 400

    # Look up Lobbie location ID
    location_id = LOBBIE_LOCATION_IDS.get(service_state)
    if not location_id:
        return jsonify({"error": f"No Lobbie location found for state: {service_state}"}), 400
    
    if lead_props.get("lobbie_form_group_id"):
        return jsonify({"error": "Intake form already sent for this lead"}), 400
    

    spanish_speaking = lead_props.get("spanish_intake_packet") == "true"

    print("SPANISH SPEAKING:", spanish_speaking)
    print("FORM TEMPLATE IDS WILL BE:", [LOBBIE_INTAKE_FORM_ES, LOBBIE_CONSENT_FORM_ES] if spanish_speaking else [LOBBIE_INTAKE_FORM_EN, LOBBIE_CONSENT_FORM_EN])

    result = send_intake_form(
        lead_name=lead_name,
        dob=dob,
        parent_first_name=parent_first_name,
        parent_last_name=parent_last_name,
        email=email,
        location_id=location_id,
        due_date_unix=get_due_date_unix(days=7),
        spanish_speaking=spanish_speaking,
    )


    # Write Lobbie form group ID back to HubSpot Lead
    form_group_id = result.get("data", {}).get("id")
    if form_group_id:
        update_lead_lobbie_form_group_id(lead_id, form_group_id)

    return jsonify({"success": True, "lobbie_response": result}), 200


@app.route("/lobbie-webhook", methods=["POST"])
def lobbie_webhook():
    data = request.get_json()
    print("LOBBIE WEBHOOK RECEIVED:", data)

    if not data.get("isComplete"):
        return jsonify({"status": "ignored, not complete"}), 200

    form_group_id = data.get("id")
    if not form_group_id:
        return jsonify({"error": "no form group id"}), 400

    # Find the Lead in HubSpot by lobbie_form_group_id
    lead = find_lead_by_lobbie_form_group_id(form_group_id)
    if not lead:
        return jsonify({"error": f"no lead found for form group id {form_group_id}"}), 404

    lead_id = lead.get("id")

    # Advance Lead to Intake Packet Received
    update_lead_status(lead_id, HS_LEAD_STAGE_INTAKE_PACKET_RECEIVED)

        # Get lead details for ClickUp
    lead, contact = get_lead_with_contact(lead_id)
    lead_props = lead.get("properties", {})
    lead_name = lead_props.get("hs_lead_name")
    service_state = lead_props.get("service_state")

    # Create ClickUp task
    clickup_task = create_intake_task(
        child_name=lead_name,
        service_state=service_state,
    )
    print("CLICKUP TASK CREATED:", clickup_task.get("id"))

    return jsonify({"success": True, "lead_id": lead_id}), 200

@app.route("/lobbie-token", methods=["GET"])
def get_token():
    from services.lobbie import get_access_token
    token = get_access_token()
    return jsonify({"token": token})

@app.route("/lobbie-attributes", methods=["GET"])
def get_attributes():
    from services.lobbie import get_access_token
    token = get_access_token()
    response = requests.get(
        "https://api.lobbie.com/lobbie/api/developer/v1/forms/templates/attributes?formTemplateId=50376",
        headers={"Authorization": f"Bearer {token}"}
    )
    return jsonify(response.json())


if __name__ == "__main__":
    app.run(debug=True)