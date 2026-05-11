import json
import os

import qrcode
from flask import current_app


def student_qr_payload(student):
    return json.dumps(
        {
            "student_id": student.student_id,
            "name": student.student_name,
            "department": student.department,
            "phone": student.phone,
        },
        separators=(",", ":"),
    )


def generate_student_qr(student):
    folder = os.path.join(current_app.config["QRCODE_FOLDER"], "students")
    os.makedirs(folder, exist_ok=True)
    filename = f"student_{student.student_id}.png"
    path = os.path.join(folder, filename)
    qrcode.make(student_qr_payload(student)).save(path)
    student.qr_code = f"qrcodes/students/{filename}"
    return student.qr_code
