import os
import traceback
import requests


def get_graph_token():
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    response = requests.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
    )
    response.raise_for_status()
    return response.json()["access_token"]


def send_alert(subject, body):
    """Send an alert email via Microsoft Graph."""
    from_address = os.getenv("ALERT_FROM_EMAIL", "donotreply@abtaba.com")
    to_address = os.getenv("ALERT_TO_EMAIL", "nglustein@abtaba.com")

    try:
        token = get_graph_token()
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body},
                "from": {"emailAddress": {"name": "Above and Beyond ABA", "address": from_address}},
                "toRecipients": [{"emailAddress": {"address": to_address}}],
            },
            "saveToSentItems": False
        }
        resp = requests.post(
            f"https://graph.microsoft.com/v1.0/users/{from_address}/sendMail",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload
        )
        if resp.status_code != 202:
            print(f"Alert email failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"Alert email failed: {e}")


def send_error_alert(endpoint, lead_id, error):
    """Send a formatted error alert with full traceback."""
    tb = traceback.format_exc()
    subject = f"🚨 Lobbie-HubSpot Error: {endpoint}"
    body = f"""
    <h2>Error in {endpoint}</h2>
    <p><strong>Lead ID:</strong> {lead_id or 'N/A'}</p>
    <p><strong>Error:</strong> {str(error)}</p>
    <h3>Full Traceback:</h3>
    <pre>{tb}</pre>
    """
    send_alert(subject, body)


def _send_graph_email(from_address, to_address, subject, body_html, cc_address=None, save_to_sent=False):
    """Low-level Graph email send. Returns True on success, False on failure."""
    try:
        token = get_graph_token()
        message = {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "from": {"emailAddress": {"address": from_address}},
            "toRecipients": [{"emailAddress": {"address": to_address}}],
        }
        if cc_address:
            message["ccRecipients"] = [{"emailAddress": {"address": cc_address}}]

        payload = {"message": message, "saveToSentItems": save_to_sent}
        resp = requests.post(
            f"https://graph.microsoft.com/v1.0/users/{from_address}/sendMail",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code != 202:
            print(f"Graph sendMail failed from={from_address} status={resp.status_code} body={resp.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"Graph sendMail exception from={from_address}: {e}")
        return False


def send_intake_email(parent_email, parent_first_name, child_name, form_url, owner_email=None, is_spanish=False):
    """Send the intake packet link to the parent.

    Sends as the lead owner if owner_email is provided and the send succeeds.
    Falls back to donotreply@abtaba.com if the owner send fails or no owner is provided.
    """
    fallback_from = os.getenv("ALERT_FROM_EMAIL", "donotreply@abtaba.com")

    if is_spanish:
        subject = f"Su paquete de ingreso de ABA para {child_name or ''}".strip()
        body = f"""
        <p>Hola {parent_first_name or ''},</p>
        <p>¡Fue un placer hablar con usted!</p>
        <p>Agradecemos su interés en nuestros servicios y esperamos poder ayudarle durante el proceso de ingreso.</p>
        <p>Como hablamos, para completar el proceso de ingreso, por favor haga clic en el enlace a continuación para subir sus tarjetas de seguro y el reporte diagnóstico, y completar los formularios de ingreso lo antes posible.</p>
        <p><a href="{form_url}">{form_url}</a></p>
        <p>Si tiene algún problema subiendo sus tarjetas de seguro o el reporte diagnóstico, puede enviárnoslos respondiendo a este correo electrónico y adjuntándolos.</p>
        <p>Si tiene alguna pregunta, no dude en comunicarse con nosotros.</p>
        """
    else:
        subject = f"Your ABA Intake Packet for {child_name or ''}".strip()
        body = f"""
        <p>Hi {parent_first_name or ''},</p>
        <p>It was a pleasure speaking with you!</p>
        <p>We appreciate your interest in our services and are looking forward to assisting you through the intake process.</p>
        <p>As per our conversation, to complete the intake process, please click the link below to upload your insurance cards and diagnostic report, and fill out the intake packet at your earliest convenience.</p>
        <p><a href="{form_url}">{form_url}</a></p>
        <p>If you have any issues uploading your insurance cards or diagnostic report, you can send it to us by replying to this email and attaching it.</p>
        <p>If you have any questions, please do not hesitate to reach out.</p>
        """

    # Try sending as the lead owner first
    if owner_email:
        success = _send_graph_email(
            from_address=owner_email,
            to_address=parent_email,
            subject=subject,
            body_html=body,
            cc_address=None,
            save_to_sent=True,
        )
        if success:
            return True
        print(f"Falling back to {fallback_from} after failed send as {owner_email}")

    # Fallback
    return _send_graph_email(
        from_address=fallback_from,
        to_address=parent_email,
        subject=subject,
        body_html=body,
        cc_address=owner_email,
        save_to_sent=False,
    )
