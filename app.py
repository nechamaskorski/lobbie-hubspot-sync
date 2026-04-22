import requests
import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from services.lobbie import send_intake_form, get_pdf
from services.hubspot import (
    get_lead_with_contact, update_lead_status, update_lead_lobbie_form_group_id,
    find_lead_by_lobbie_form_group_id, create_deal, update_deal_clickup_id, associate_deal,
    get_client_from_lead, get_client_properties, get_lead_notes, get_note,
    get_attachment_signed_url
)
from services.clickup import create_intake_task, upload_file_to_task, post_task_comment
from services.email import send_error_alert
from config import (
    LOBBIE_LOCATION_IDS, LOBBIE_INTAKE_FORM_EN, LOBBIE_CONSENT_FORM_EN,
    LOBBIE_INTAKE_FORM_ES, LOBBIE_CONSENT_FORM_ES, HS_LEAD_STAGE_INTAKE_PACKET_RECEIVED,
    HS_DEAL_PIPELINE_ID, HS_DEAL_STAGE_INTAKE_PACKET_RECEIVED
)
from services.utils import strip_html

app = Flask(__name__)


def get_due_date_unix(days=7):
    """Return unix timestamp for X days from now."""
    return int((datetime.utcnow() + timedelta(days=days)).timestamp() * 1000)


def handle_intake_received(lead_id, include_pdf=False, form_group_id=None):
    """Shared logic for when intake packet is received."""
    lead, contact = get_lead_with_contact(lead_id)
    lead_props = lead.get("properties", {})
    contact_props = contact.get("properties", {}) if contact else {}
    lead_name = lead_props.get("hs_lead_name")
    service_state = lead_props.get("service_state")

    update_lead_status(lead_id, HS_LEAD_STAGE_INTAKE_PACKET_RECEIVED)

    deal = create_deal(
        child_name=lead_name,
        pipeline_id=HS_DEAL_PIPELINE_ID,
        stage_id=HS_DEAL_STAGE_INTAKE_PACKET_RECEIVED,
    )
    deal_id = deal.get("id")

    # Associate Client custom object to Deal
    client_id = get_client_from_lead(lead_id)
    if client_id:
        try:
            associate_deal(deal_id, "2-47660783", client_id, 45, association_category="USER_DEFINED")
        except Exception:
            pass  # Association may already exist, continue

    client_props = get_client_properties(client_id) if client_id else {}

    # Associate Deal to Contact
    if contact:
        contact_id = contact.get("id")
        associate_deal(deal_id, "contacts", contact_id, 3)


    clickup_task = create_intake_task(
    child_name=lead_name,
    service_state=service_state,
    lead_props=lead_props,
    contact_props=contact_props,
    client_props=client_props,
)
    clickup_task_id = clickup_task.get("id")

    update_deal_clickup_id(deal_id, clickup_task_id)

    if include_pdf and form_group_id:
        pdf_content = get_pdf(form_group_id)
        upload_file_to_task(clickup_task_id, pdf_content, "intake_packet.pdf")


    # Post HubSpot notes as ClickUp comments
    note_ids = get_lead_notes(lead_id)
    for note_id in note_ids:
        note = get_note(note_id)
        body = note.get("hs_note_body", "").strip()
        date = note.get("hs_createdate", "")[:10]  # just the date portion
        if body:
            clean_body = strip_html(body)
            if clean_body:
                post_task_comment(clickup_task_id, f"{date}\n{clean_body}")

        # Upload HubSpot Lead attachments to ClickUp task
    attachments_raw = lead_props.get("attachments", "")
    if attachments_raw:
        attachment_ids = [a.strip() for a in attachments_raw.split(";") if a.strip()]
        for file_id in attachment_ids:
            try:
                signed_url = get_attachment_signed_url(file_id)
                if signed_url:
                    file_response = requests.get(signed_url)
                    file_response.raise_for_status()
                    # Extract filename from URL or use file_id as fallback
                    filename = signed_url.split("/")[-1].split("?")[0] or f"attachment_{file_id}"
                    upload_file_to_task(clickup_task_id, file_response.content, filename)
            except Exception as e:
                print(f"Failed to upload attachment {file_id}: {e}")

    return deal_id, clickup_task_id


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

    try:
        if not lead_id:
            return jsonify({"error": "lead_id is required"}), 400

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
        gender = lead_props.get("gender")

        if lead_props.get("lobbie_form_group_id"):
            return jsonify({"error": "Intake form already sent for this lead"}), 400

        if not all([email, service_state]):
            return jsonify({"error": "Missing required properties"}), 400

        location_id = LOBBIE_LOCATION_IDS.get(service_state)
        if not location_id:
            return jsonify({"error": f"No Lobbie location found for state: {service_state}"}), 400

        spanish_speaking = lead_props.get("spanish_intake_packet") == "true"

        result = send_intake_form(
            lead_name=lead_name,
            dob=dob,
            gender=gender,
            parent_first_name=parent_first_name,
            parent_last_name=parent_last_name,
            email=email,
            location_id=location_id,
            due_date_unix=get_due_date_unix(days=7),
            spanish_speaking=spanish_speaking,
        )

        form_group_id = result.get("data", {}).get("id")
        if form_group_id:
            update_lead_lobbie_form_group_id(lead_id, form_group_id)

        return jsonify({"success": True, "lobbie_response": result}), 200

    except Exception as e:
        send_error_alert("/send-intake", lead_id, e)
        return jsonify({"error": str(e)}), 500


@app.route("/lobbie-webhook", methods=["POST"])
def lobbie_webhook():
    """
    Receives webhook from Lobbie when patient completes their forms.
    """
    data = request.get_json()
    lead_id = None

    try:
        secret = request.headers.get("X-Lobbie-Secret")
        if secret != os.getenv("LOBBIE_WEBHOOK_SECRET"):
            return jsonify({"error": "unauthorized"}), 401

        if not data.get("isComplete"):
            return jsonify({"status": "ignored, not complete"}), 200

        form_group_id = data.get("id")
        if not form_group_id:
            return jsonify({"error": "no form group id"}), 400

        lead = find_lead_by_lobbie_form_group_id(form_group_id)
        if not lead:
            return jsonify({"error": f"no lead found for form group id {form_group_id}"}), 404

        lead_id = lead.get("id")

        deal_id, clickup_task_id = handle_intake_received(
            lead_id=lead_id,
            include_pdf=True,
            form_group_id=form_group_id,
        )

        return jsonify({"success": True, "lead_id": lead_id, "deal_id": deal_id, "clickup_task_id": clickup_task_id}), 200

    except Exception as e:
        send_error_alert("/lobbie-webhook", lead_id, e)
        return jsonify({"error": str(e)}), 500


@app.route("/intake-received-manual", methods=["POST"])
def intake_received_manual():
    """
    Triggered by HubSpot workflow when intake_packet_received_manually = true.
    Expects JSON: { "lead_id": "123" }
    """
    data = request.get_json()
    lead_id = data.get("lead_id")

    try:
        if not lead_id:
            return jsonify({"error": "lead_id is required"}), 400

        deal_id, clickup_task_id = handle_intake_received(
            lead_id=lead_id,
            include_pdf=False,
        )

        return jsonify({"success": True, "lead_id": lead_id, "deal_id": deal_id, "clickup_task_id": clickup_task_id}), 200

    except Exception as e:
        send_error_alert("/intake-received-manual", lead_id, e)
        return jsonify({"error": str(e)}), 500
    

@app.route("/test-lobbie-form/<int:form_group_id>", methods=["GET"])
def test_lobbie_form(form_group_id):
    from services.lobbie import get_access_token
    token = get_access_token()
    response = requests.get(
        f"https://api.lobbie.com/lobbie/api/v1/forms/groups/{form_group_id}?isIncludeMappedFormAnswers=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    return jsonify(response.json()), response.status_code



if __name__ == "__main__":
    app.run(debug=True)