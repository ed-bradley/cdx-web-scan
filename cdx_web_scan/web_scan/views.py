from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from flask import Blueprint, Response, current_app, render_template, request, send_from_directory, session

from cdx_web_scan import db
from cdx_web_scan.models import CaptureMethod, Scan, ScanSource
from cdx_web_scan.web_scan.forms import validate_upc_ean

# blueprint router configuration
web_scan = Blueprint("web_scan", __name__)

# Path to static files for manifest and service worker
_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

#  Global constants
_BATCH_PER_PAGE = 5
_DEFAULT_TITLE = " -- UNTITLED -- "


def _classify_barcode(value: str) -> str:
    v = (value or "").strip()
    if not v.isdigit():
        return "unknown"

    # Heuristic classification by length.
    # - UPC-A: 12 digits
    # - EAN-8: 8 digits
    # - EAN-13: 13 digits
    # - ITF-14 / GTIN-14: 14 digits (treat as EAN family for display)
    if len(v) == 12:
        return "UPC"
    if len(v) in {8, 13, 14}:
        return "EAN"
    return "unknown"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_batch_items() -> list[dict]:
    items = session.get("batch_items")
    if not isinstance(items, list):
        items = []
    return items


def _set_batch_items(items: list[dict]) -> None:
    session["batch_items"] = items


def _batch_paging_context(items: list[dict], page: int | None = None) -> dict:
    total = len(items)
    total_pages = max(1, (total + _BATCH_PER_PAGE - 1) // _BATCH_PER_PAGE)

    if page is None:
        page = int(session.get("batch_page", 1) or 1)
    page = max(1, min(int(page), total_pages))
    session["batch_page"] = page

    start = (page - 1) * _BATCH_PER_PAGE
    end = start + _BATCH_PER_PAGE
    page_items = items[start:end]

    return {
        "items": items,
        "page_items": page_items,
        "page": page,
        "total_pages": total_pages,
        "ol_start": start + 1,
    }


def _batch_contains_code(code: str) -> bool:
    code_norm = (code or "").strip()
    if not code_norm:
        return False
    for item in _get_batch_items():
        if isinstance(item, dict) and (item.get("code") or "").strip() == code_norm:
            return True
    return False


def _append_to_batch(code: str, source: str) -> list[dict]:
    items = _get_batch_items()
    items.append({"code": code, "source": source, "captured_at": _utc_iso(), "title": None})
    _set_batch_items(items)
    return items


def _append_to_batch_with_title(code: str, source: str, title: str | None, barcode_type: str) -> list[dict]:
    items = _get_batch_items()
    code_norm = (code or "").strip()
    if any((item.get("code") or "").strip() == code_norm for item in items if isinstance(item, dict)):
        return items
    normalized_title = (title or "").strip()
    if not normalized_title:
        normalized_title = _DEFAULT_TITLE

    barcode_type_norm = (barcode_type or "").strip() or "unknown"
    items.append(
        {
            "code": code_norm,
            "source": source,
            "captured_at": _utc_iso(),
            "title": normalized_title,
            "format": barcode_type_norm,
        }
    )
    _set_batch_items(items)
    return items


@web_scan.route("/", methods=["GET"])
def index():
    """Route to display the home page of the application"""

    items = _get_batch_items()
    return render_template("index.html", **_batch_paging_context(items))


@web_scan.route("/batch", methods=["GET"])
def batch_view():
    items = _get_batch_items()
    # Backfill missing format keys for older sessions.
    for item in items:
        if isinstance(item, dict) and not item.get("format"):
            item["format"] = _classify_barcode(str(item.get("code") or ""))
    _set_batch_items(items)
    page_arg = request.args.get("page")
    page = int(page_arg) if page_arg and page_arg.isdigit() else None
    return render_template("batch_fragment.html", **_batch_paging_context(items, page=page)), 200


@web_scan.route("/submit", methods=["POST"])
def submit_barcode():
    validation = validate_upc_ean(request.form.get("barcode"))
    if not validation.ok:
        # HTMX-friendly: return a small fragment.
        return (
            render_template(
                "oob_update_fragment.html",
                ok=False,
                message=validation.error,
                barcode=None,
                scan_id=None,
                **_batch_paging_context(_get_batch_items()),
            ),
            200,
        )

    source_raw = (request.form.get("source") or "manual").strip().lower()
    source: ScanSource
    capture_method: CaptureMethod
    batch_source: str

    if source_raw == "camera":
        source = ScanSource.camera
        capture_method = CaptureMethod.camera
        batch_source = "camera"
    elif source_raw in {"wedge", "scanner"}:
        # Wedge scanners emulate keyboard input; we store as 'scanner' in the DB enum.
        source = ScanSource.scanner
        capture_method = CaptureMethod.scanner
        batch_source = "wedge"
    else:
        source = ScanSource.manual
        capture_method = CaptureMethod.manual
        batch_source = "manual"

    barcode_value = validation.value or ""
    barcode_type = _classify_barcode(barcode_value)

    title = (request.form.get("title") or "").strip()
    if not title:
        title = _DEFAULT_TITLE

    # Prevent duplicates in the current session batch.
    if _batch_contains_code(barcode_value):
        return (
            render_template(
                "oob_update_fragment.html",
                ok=False,
                message=f"Already in batch: {barcode_value}",
                barcode=barcode_value,
                scan_id=None,
                **_batch_paging_context(_get_batch_items()),
            ),
            200,
        )

    # Always update the batch (session-backed) so the UI works even if DB isn't ready.
    items = _append_to_batch_with_title(barcode_value, batch_source, title, barcode_type)
    # After adding, jump to the last page so the newest item is visible.
    last_page = max(1, (len(items) + _BATCH_PER_PAGE - 1) // _BATCH_PER_PAGE)
    session["batch_page"] = last_page

    scan_id: str | None = None
    try:
        scan = Scan(source=source, notes=title)
        db.session.add(scan)
        db.session.flush()  # allocate scan.id

        # Store one primary barcode row when schema exists.
        from cdx_web_scan.models import BarcodeCapture

        barcode = BarcodeCapture(
            scan_id=scan.id,
            symbology=barcode_type,
            value_raw=barcode_value,
            value_normalized=barcode_value,
            is_primary=True,
            capture_method=capture_method,
        )
        db.session.add(barcode)

        scan.primary_barcode_id = barcode.id
        db.session.commit()
        scan_id = scan.id
    except Exception:
        # If the DB isn't initialized/migrated yet, still provide UI feedback.
        db.session.rollback()
        current_app.logger.exception("Failed to persist scan")

    return (
        render_template(
            "oob_update_fragment.html",
            ok=True,
            message="Added to batch",
            barcode=barcode_value,
            scan_id=scan_id,
            **_batch_paging_context(items, page=session.get("batch_page")),
        ),
        200,
    )


@web_scan.route("/batch/clear", methods=["POST"])
def batch_clear():
    _set_batch_items([])
    session["batch_page"] = 1
    return render_template("batch_fragment.html", **_batch_paging_context(_get_batch_items(), page=1)), 200


@web_scan.route("/batch/delete/<code>", methods=["POST"])
def batch_delete(code: str):
    code_norm = (code or "").strip()
    items = _get_batch_items()

    new_items: list[dict] = []
    removed = False
    for item in items:
        if (
            not removed
            and isinstance(item, dict)
            and (item.get("code") or "").strip() == code_norm
        ):
            removed = True
            continue
        new_items.append(item)

    _set_batch_items(new_items)
    # Keep the current page if possible; clamp in paging helper.
    return render_template("batch_fragment.html", **_batch_paging_context(new_items)), 200


def _post_json(url: str, payload: dict, headers: dict[str, str] | None = None) -> tuple[int, str]:
    import urllib.request

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = getattr(resp, "status", 200)
            return status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
        return int(getattr(e, "code", 500)), (e.read().decode("utf-8") if hasattr(e, "read") else str(e))
    except Exception as e:
        return 0, str(e)


@web_scan.route("/batch/submit", methods=["POST"])
def batch_submit():
    items = _get_batch_items()
    if not items:
        return render_template(
            "submit_result_fragment.html",
            ok=False,
            message="Batch is empty.",
            response_body=None,
        ), 200

    intake_url = current_app.config.get("INTAKE_API_URL") or ""
    if not intake_url:
        return render_template(
            "submit_result_fragment.html",
            ok=False,
            message="INTAKE_API_URL is not configured.",
            response_body=None,
        ), 200

    # Minimal, generic payload. Adjust keys to match your API contract.
    payload = {
        "source": "cdx-web-scan",
        "submitted_at": _utc_iso(),
        "barcodes": [item["code"] for item in items],
        "items": items,
    }

    headers: dict[str, str] = {}
    token = current_app.config.get("INTAKE_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    status, body = _post_json(intake_url, payload, headers=headers)
    ok = 200 <= status < 300

    if ok:
        _set_batch_items([])

    return (
        render_template(
            "submit_result_fragment.html",
            ok=ok,
            message=(f"Submitted {len(items)} item(s)" if ok else f"Submit failed (HTTP {status})"),
            response_body=body,
        ),
        200,
    )


@web_scan.route("/manifest.webmanifest", methods=["GET"])
def manifest():
    return send_from_directory(_STATIC_DIR, "manifest.webmanifest", mimetype="application/manifest+json")


@web_scan.route("/service-worker.js", methods=["GET"])
def service_worker():
    # Must be served from the app root for scope '/'
    return send_from_directory(_STATIC_DIR, "service-worker.js", mimetype="text/javascript")