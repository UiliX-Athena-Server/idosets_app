import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_TIMEOUT_SECONDS = 4
_MAX_BYTES = 512 * 1024
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; idosets.app favicon lookup)"
}


def clean_url(url: str | None) -> str | None:
    """Return the url if it is a plausible http(s) link, otherwise None."""
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if "://" not in url:
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    if "." not in parsed.hostname:
        return None
    return url


def _is_public_host(hostname: str) -> bool:
    """Prevent the server from being used to probe internal addresses."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError:
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            return False
    return True


def find_favicon(url: str | None) -> str | None:
    """
    Best-effort lookup of a page's favicon. Never raises, and never blocks for
    longer than a few seconds.
    """
    url = clean_url(url)
    if not url:
        return None

    parsed = urlparse(url)
    fallback = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"

    if not _is_public_host(parsed.hostname):
        return None

    try:
        with requests.get(
            url,
            timeout=_TIMEOUT_SECONDS,
            headers=_HEADERS,
            stream=True,
            allow_redirects=True,
        ) as response:
            if response.status_code != 200:
                return fallback
            content = response.raw.read(_MAX_BYTES, decode_content=True)
            base_url = response.url
    except (requests.RequestException, ValueError, OSError):
        return fallback

    soup = BeautifulSoup(content, "html.parser")
    for rel in ("icon", "shortcut icon", "apple-touch-icon"):
        tag = soup.find("link", rel=_rel_filter(rel))
        if tag and tag.get("href"):
            return urljoin(base_url, tag["href"])

    return fallback


def _rel_filter(wanted: str):
    return lambda value: _rel_matches(value, wanted)


def _rel_matches(value, wanted: str) -> bool:
    if not value:
        return False
    if isinstance(value, (list, tuple)):
        value = " ".join(value)
    return value.lower() == wanted
