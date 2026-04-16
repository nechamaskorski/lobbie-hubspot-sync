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