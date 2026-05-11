import sys
from datetime import datetime

from app import app
from extensions import db
from models import Student


def make_address(idx: int) -> str:
    # Kerala addresses (deterministic / varied)
    locations = [
        "Kowdiar, Thiruvananthapuram",
        "Edappally, Kochi",
        "Marine Drive, Ernakulam",
        "MG Road, Ernakulam",
        "Kaloor, Kochi",
        "Vyttila, Kochi",
        "Kottayam Town, Kottayam",
        "Changanassery, Kottayam",
        "Thrissur Town, Thrissur",
        "Guruvayur, Thrissur",
        "Kozhikode Beach Road, Kozhikode",
        "Palayam, Kozhikode",
        "Kannur Cantonment, Kannur",
        "Shivapuram, Kasaragod",
        "Alappuzha Beach, Alappuzha",
        "Haripad, Alappuzha",
        "Punalur, Kollam",
        "Chathannoor, Kollam",
    ]
    district = [
        "Thiruvananthapuram",
        "Ernakulam",
        "Ernakulam",
        "Ernakulam",
        "Ernakulam",
        "Ernakulam",
        "Kottayam",
        "Kottayam",
        "Thrissur",
        "Thrissur",
        "Kozhikode",
        "Kozhikode",
        "Kannur",
        "Kasaragod",
        "Alappuzha",
        "Alappuzha",
        "Kollam",
        "Kollam",
    ]
    state = "Kerala"
    pincode = [
        "695003",
        "682024",
        "682031",
        "682016",
        "682017",
        "682019",
        "686001",
        "686101",
        "680001",
        "679105",
        "673032",
        "673002",
        "670001",
        "671121",
        "688001",
        "690514",
        "691305",
        "691571",
    ]

    loc = locations[idx % len(locations)]
    dist = district[idx % len(district)]
    pin = pincode[idx % len(pincode)]
    return f"House No. {10 + idx}, {loc}, {dist}, {state} - {pin}"


def make_unique_phone(idx: int) -> str:
    # Generate Kerala-like 10-digit mobile numbers, deterministic & unique
    base = 9000000000
    phone = base + idx
    return str(phone)


def main() -> None:
    courses = [
        "MCA",
        "MBA",
        "MSc",
        "MA",
        "MCom",
        "B.Tech",
        "BHM",
        "BCA",
        "BSc",
        "BCom",
        "BA",
        "BBA",
    ]


    first_names = [
        "Ananya",
        "Devika",
        "Gopika",
        "Haritha",
        "Ishita",
        "Jaya",
        "Karthika",
        "Lekshmi",
        "Meenakshi",
        "Nandini",
        "Oviya",
        "Priya",
        "Riya",
        "Sreya",
        "Swathi",
        "Tejaswini",
        "Usha",
        "Vidhya",
        "Yamini",
        "Zara",
    ]
    last_names = [
        "Nair",
        "Menon",
        "Warrier",
        "Pillai",
        "Thomas",
        "Raj",
        "Kumar",
        "Sankar",
        "Krishnan",
        "Raghavan",
    ]

    with app.app_context():
        # Ensure tables exist without changing existing app code.
        db.create_all()

        new_students = 0

        for i in range(1, 41):
            student_id = f"SCI{i:03d}"

            # Prevent duplicate insertion
            if Student.query.filter_by(student_id=student_id).first():
                continue

            department = "Science"
            course = courses[(i - 1) % len(courses)]
            # Student model has both full_name and student_name
            first = first_names[(i - 1) % len(first_names)]
            last = last_names[(i - 1) % len(last_names)]
            full_name = f"{first} {last}"
            student_name = full_name

            phone = make_unique_phone(i)  # unique phone numbers
            college_id = f"SCI-COL{2000 + i:04d}"  # must be unique + not-null per model

            student = Student(
                student_id=student_id,
                student_name=student_name,
                full_name=full_name,
                college_id=college_id,
                course_applied=course,
                course=course.split()[-1],  # e.g., Physics/Chemistry/etc (fits String(40))
                admission_year=2025,
                batch="2025-28",
                current_year="2nd Year",
                department=department,
                address=make_address(i),
                phone=phone,
                qr_code=f"science-{student_id}-{datetime.utcnow().strftime('%Y%m%d')}"[:255],
            )

            db.session.add(student)
            new_students += 1

        db.session.commit()

        # Requirement: print this exact output
        print("40 Science students added successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # If something goes wrong, fail loudly for CI/terminal visibility
        print(f"Error inserting students: {e}")
        sys.exit(1)

