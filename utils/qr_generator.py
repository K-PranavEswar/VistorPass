import hashlib
import hmac
import json
import os
import secrets

import qrcode
from flask import current_app


def _sign(payload):
    secret = current_app.config["SECRET_KEY"].encode()
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


def make_qr_payload(visitor):
    token = secrets.token_urlsafe(24)
    qr_data = {
        "visitor_id": f"VIS{visitor.id}",
        "visitor_name": visitor.public_user.name,
        "visitor_type": visitor.visitor_type or "Visitor",
        "relationship": visitor.relationship or "",
        "student_id": visitor.student_id or "",
        "student_name": visitor.student_name or "",
        "phone": visitor.public_user.phone,
    }
    base = (
        f"data={json.dumps(qr_data, separators=(',', ':'))}|"
        f"visitor_id={visitor.id}|name={visitor.public_user.name}|"
        f"visit_date={visitor.visit_date.isoformat()}|visit_time={visitor.visit_time}|"
        f"authority={visitor.authority_id}|status={visitor.status}|token={token}"
    )
    return f"{base}|sig={_sign(base)}", hashlib.sha256(token.encode()).hexdigest()


def verify_payload(payload):
    parts = payload.split("|")
    data = {}
    for item in parts:
        if "=" in item:
            key, value = item.split("=", 1)
            data[key] = value
    sig = data.pop("sig", "")
    unsigned = "|".join(f"{key}={value}" for key, value in data.items())
    if not hmac.compare_digest(sig, _sign(unsigned)):
        return None
    if "data" in data:
        try:
            qr_data = json.loads(data["data"])
            for key, value in qr_data.items():
                if key in data:
                    data[f"qr_{key}"] = value
                else:
                    data[key] = value
        except json.JSONDecodeError:
            return None
    return data


def generate_qr(visitor):
    payload, token_hash = make_qr_payload(visitor)
    os.makedirs(current_app.config["QRCODE_FOLDER"], exist_ok=True)
    filename = f"visitor_{visitor.id}.png"
    path = os.path.join(current_app.config["QRCODE_FOLDER"], filename)
    img = qrcode.make(payload)
    img.save(path)
    visitor.qr_code = f"qrcodes/{filename}"
    visitor.qr_token_hash = token_hash
    return visitor.qr_code
