"""Meta Graph API — Image Post nach Insta Business Account.

Flow:
1. POST /{ig-user-id}/media   { image_url, caption }   → creation_id
2. POST /{ig-user-id}/media_publish   { creation_id }   → media_id

image_url MUSS öffentlich per HTTPS erreichbar sein. Wir nutzen
https://schwaltenweiher.de/webcam/schwaltenweiher_latest.jpg.
"""
import os
import time
import requests


GRAPH = "https://graph.facebook.com/v21.0"


class PosterError(Exception):
    pass


def create_media(ig_user_id: str, image_url: str, caption: str, token: str,
                 media_type: str | None = None) -> str:
    data = {"image_url": image_url, "access_token": token}
    if caption:
        data["caption"] = caption
    if media_type:
        data["media_type"] = media_type
    r = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data=data,
        timeout=30,
    )
    if r.status_code >= 400:
        raise PosterError(f"create_media: {r.status_code} {r.text}")
    return r.json()["id"]


def wait_ready(creation_id: str, token: str, max_wait: int = 120,
               poll_interval: int = 3) -> None:
    """Container muss FINISHED sein vor publish.

    Pollt bis max_wait Sekunden. Instagram braucht bei Last gelegentlich
    deutlich >30s zum Verarbeiten — der alte 30s-Deckel war die Ursache des
    4-Tage-Ausfalls 23.-26.05.2026. Bei Ablauf sauberer PosterError; der
    Caller loggt das als error-Event und der naechste Cron-Tick versucht es
    erneut (kein mark_posted bei Fehler). Override via env CONTAINER_MAX_WAIT.
    """
    max_wait = int(os.getenv("CONTAINER_MAX_WAIT", str(max_wait)))
    deadline = time.monotonic() + max_wait
    last = None
    time.sleep(2)  # Container ist nie sofort fertig
    while time.monotonic() < deadline:
        r = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=10,
        )
        last = r.json()
        st = last.get("status_code")
        if st == "FINISHED":
            return
        if st == "ERROR":
            raise PosterError(f"container error: {last}")
        time.sleep(poll_interval)
    raise PosterError(f"container not ready after {max_wait}s (last={last})")


def publish(ig_user_id: str, creation_id: str, token: str) -> str:
    r = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    if r.status_code >= 400:
        raise PosterError(f"publish: {r.status_code} {r.text}")
    return r.json()["id"]


def post(image_url: str, caption: str, dry_run: bool = True) -> dict:
    if dry_run:
        return {"dry_run": True, "would_post": {"image_url": image_url, "caption": caption}}
    ig = os.environ["META_IG_USER_ID"]
    tok = os.environ["META_PAGE_TOKEN"]
    cid = create_media(ig, image_url, caption, tok)
    wait_ready(cid, tok)
    mid = publish(ig, cid, tok)
    return {"dry_run": False, "media_id": mid}


def post_story(image_url: str, dry_run: bool = True) -> dict:
    if dry_run:
        return {"dry_run": True, "would_post_story": {"image_url": image_url}}
    ig = os.environ["META_IG_USER_ID"]
    tok = os.environ["META_PAGE_TOKEN"]
    cid = create_media(ig, image_url, "", tok, media_type="STORIES")
    wait_ready(cid, tok)
    mid = publish(ig, cid, tok)
    return {"dry_run": False, "media_id": mid}


def post_to_facebook(image_url: str, caption: str, dry_run: bool = True) -> dict:
    """Crosspost als Foto auf die FB-Page."""
    if dry_run:
        return {"dry_run": True, "would_fb_post": {"image_url": image_url}}
    page_id = os.environ["META_PAGE_ID"]
    tok = os.environ["META_PAGE_TOKEN"]
    r = requests.post(
        f"{GRAPH}/{page_id}/photos",
        data={"url": image_url, "caption": caption, "access_token": tok,
              "published": "true"},
        timeout=30,
    )
    if r.status_code >= 400:
        raise PosterError(f"fb_photo: {r.status_code} {r.text}")
    return {"dry_run": False, "fb_post_id": r.json().get("post_id"),
            "fb_photo_id": r.json().get("id")}


def post_fb_story(image_url: str, dry_run: bool = True) -> dict:
    """FB-Page-Story (Photo). Erfordert pages_manage_posts."""
    if dry_run:
        return {"dry_run": True, "would_fb_story": {"image_url": image_url}}
    page_id = os.environ["META_PAGE_ID"]
    tok = os.environ["META_PAGE_TOKEN"]
    # Schritt 1: Foto unpublished hochladen → photo_id
    r1 = requests.post(
        f"{GRAPH}/{page_id}/photos",
        data={"url": image_url, "published": "false", "access_token": tok},
        timeout=30,
    )
    if r1.status_code >= 400:
        raise PosterError(f"fb_story_upload: {r1.status_code} {r1.text}")
    photo_id = r1.json()["id"]
    # Schritt 2: Foto als Story publishen
    r2 = requests.post(
        f"{GRAPH}/{page_id}/photo_stories",
        data={"photo_id": photo_id, "access_token": tok},
        timeout=30,
    )
    if r2.status_code >= 400:
        raise PosterError(f"fb_story_publish: {r2.status_code} {r2.text}")
    return {"dry_run": False, "fb_story_id": r2.json().get("post_id"),
            "fb_photo_id": photo_id}


def discover_ig_user_id(page_id: str, token: str) -> str:
    """Hilfsfunktion — einmalig nach Token-Erhalt aufrufen."""
    r = requests.get(
        f"{GRAPH}/{page_id}",
        params={"fields": "instagram_business_account", "access_token": token},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["instagram_business_account"]["id"]
