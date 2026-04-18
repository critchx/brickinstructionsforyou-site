# brickset_not_owned_2026_FULLY_UPDATED.py
# ------------------------------------------------------------
# Brickset "Not Owned" export for a given year (snapshot CSV)
# + Automatically duplicates output to:
#   - Main Brickset.csv
#   - 2019.csv
# ------------------------------------------------------------

from __future__ import annotations

import csv
import json
import os
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

API_BASE = "https://brickset.com/api/v3.asmx"


# -----------------------------
# Utilities
# -----------------------------
def script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_line(log_path: str, msg: str) -> None:
    ensure_parent_dir(log_path)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{now_stamp()}] {msg}\n")


def safe_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    if isinstance(v, (int, float)):
        return bool(v)
    return default


def safe_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def load_config() -> Dict[str, Any]:
    cfg_path = os.path.join(script_dir(), "brickset_config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_creds(cfg: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    api_key = (cfg.get("api_key") or "").strip() or os.getenv("BRICKSET_API_KEY")
    username = (cfg.get("username") or "").strip() or os.getenv("BRICKSET_USERNAME")
    password = (cfg.get("password") or "").strip() or os.getenv("BRICKSET_PASSWORD")
    return api_key, username, password


def atomic_write_csv(rows: List[Dict[str, Any]], out_path: str, fieldnames: List[str]) -> None:
    ensure_parent_dir(out_path)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    os.close(tmp_fd)
    try:
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        os.replace(tmp_path, out_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# -----------------------------
# Brickset API helpers
# -----------------------------
def _request_with_retries(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 45,
    tries: int = 6,
    backoff_base: float = 1.5,
    debug: bool = False,
) -> requests.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(1, tries + 1):
        try:
            if method.upper() == "GET":
                r = requests.get(url, params=params, timeout=timeout)
            else:
                r = requests.post(url, data=data, timeout=timeout)

            if r.status_code in (500, 502, 503, 504):
                if debug:
                    print(f"Brickset {r.status_code} on {url} (attempt {attempt}/{tries})")
                time.sleep(backoff_base ** (attempt - 1))
                continue

            r.raise_for_status()
            return r

        except requests.RequestException as e:
            last_exc = e
            time.sleep(backoff_base ** (attempt - 1))

    if last_exc:
        raise last_exc
    raise RuntimeError("Request failed unexpectedly")


def brickset_call(
    api_key: str,
    method: str,
    *,
    use_get: bool,
    user_hash: Optional[str] = None,
    params_obj: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    url = f"{API_BASE}/{method}"

    if method == "login":
        payload = {"apiKey": api_key, "username": extra["username"], "password": extra["password"]}
        r = _request_with_retries("POST", url, data=payload, debug=debug)
        data = r.json()
        if data.get("status") != "success":
            raise RuntimeError(f"login failed: {data}")
        return data

    payload = {"apiKey": api_key, "userHash": user_hash or ""}
    payload["params"] = json.dumps(params_obj or {})

    r = _request_with_retries(
        "GET" if use_get else "POST",
        url,
        params=payload if use_get else None,
        data=None if use_get else payload,
        debug=debug,
    )

    data = r.json()
    if data.get("status") != "success":
        raise RuntimeError(f"{method} failed: {data}")
    return data


def brickset_login(api_key: str, username: str, password: str) -> str:
    data = brickset_call(
        api_key,
        "login",
        use_get=False,
        extra={"username": username, "password": password},
    )
    return data["hash"]


def get_sets(api_key: str, params: Dict[str, Any], *, user_hash: str, use_get: bool) -> List[Dict[str, Any]]:
    p = dict(params)
    p.setdefault("pageSize", 500)
    p.setdefault("pageNumber", 1)

    first = brickset_call(api_key, "getSets", use_get=use_get, user_hash=user_hash, params_obj=p)
    matches = int(first.get("matches", 0))
    sets = list(first.get("sets", []) or [])

    while len(sets) < matches:
        p["pageNumber"] += 1
        nxt = brickset_call(api_key, "getSets", use_get=use_get, user_hash=user_hash, params_obj=p)
        sets.extend(nxt.get("sets", []) or [])
        time.sleep(0.15)

    return sets


# -----------------------------
# CSV handling
# -----------------------------
FIELDNAMES = [
    "setID",
    "number",
    "name",
    "year",
    "theme",
    "subtheme",
    "pieces",
    "minifigs",
    "availability",
    "packagingType",
    "imageURL",
    "bricksetURL",
]

EXCLUDED_THEMES = {
    "gear",
    "games",
    "collectable minifigures",
}


def extract_row(s: Dict[str, Any]) -> Dict[str, Any]:
    image_url = ""
    if isinstance(s.get("image"), dict):
        image_url = s["image"].get("imageURL") or ""
    return {
        "setID": s.get("setID", ""),
        "number": s.get("number", ""),
        "name": s.get("name", ""),
        "year": s.get("year", ""),
        "theme": s.get("theme", ""),
        "subtheme": s.get("subtheme", ""),
        "pieces": s.get("pieces", ""),
        "minifigs": s.get("minifigs", ""),
        "availability": s.get("availability", ""),
        "packagingType": s.get("packagingType", ""),
        "imageURL": image_url,
        "bricksetURL": s.get("bricksetURL", ""),
    }


# -----------------------------
# Main
# -----------------------------
def main() -> int:
    cfg = load_config()
    year = safe_int(cfg.get("year", 2026), 2026)
    order_by = cfg.get("order_by", "Theme")
    use_get = safe_bool(cfg.get("use_get", True), True)

    out_path = cfg.get(
        "out_path",
        "C:/Users/critc/OneDrive/Desktop/PDFs To Extract/output/brickset_2026_not_owned.csv",
    )

    log_path = os.path.join(script_dir(), "brickset_not_owned.log")

    api_key, username, password = get_creds(cfg)
    if not api_key or not username or not password:
        log_line(log_path, "Missing Brickset credentials")
        return 2

    try:
        user_hash = brickset_login(api_key, username, password)

        all_sets = get_sets(
            api_key,
            {"year": str(year), "orderBy": order_by},
            user_hash=user_hash,
            use_get=use_get,
        )

        owned_sets = get_sets(
            api_key,
            {"year": str(year), "owned": 1},
            user_hash=user_hash,
            use_get=use_get,
        )

        owned_ids = {s["setID"] for s in owned_sets if s.get("setID")}
        not_owned = [s for s in all_sets if s.get("setID") not in owned_ids]
        not_owned = [
            s for s in not_owned
            if str(s.get("theme", "")).strip().lower() not in EXCLUDED_THEMES
        ]

        rows = [extract_row(s) for s in not_owned]
        atomic_write_csv(rows, out_path, FIELDNAMES)

        # 🔥 NEW: duplicate output
        out_dir = os.path.dirname(out_path)
        shutil.copy2(out_path, os.path.join(out_dir, "Main Brickset.csv"))
        shutil.copy2(out_path, os.path.join(out_dir, "2019.csv"))

        log_line(log_path, f"Wrote {len(rows)} rows + created Main Brickset.csv and 2019.csv")
        return 0

    except Exception as e:
        log_line(log_path, f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
