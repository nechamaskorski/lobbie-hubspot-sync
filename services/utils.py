import re

def strip_html(text):
    """Strip HTML tags from a string."""
    return re.sub(r'<[^>]+>', '', text).strip()