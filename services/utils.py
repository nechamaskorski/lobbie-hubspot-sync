import re
import urllib.parse

def decode_filename(url):
    """Extract and decode a filename from a URL."""
    filename = url.split("/")[-1].split("?")[0]
    return urllib.parse.unquote(filename)

def strip_html(text):
    """Strip HTML tags from a string."""
    return re.sub(r'<[^>]+>', '', text).strip()