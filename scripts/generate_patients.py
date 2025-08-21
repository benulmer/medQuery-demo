#!/usr/bin/env python3
"""
Generate synthetic patient records for MedQuery AI.

Usage:
  python3 scripts/generate_patients.py [count]

Outputs to: data/mock_patient_data.json
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta


def rand_date(start_year: int = 2023, end_year: int = 2025) -> str:
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    d = start + timedelta(days=random.randint(0, delta.days))
    return d.strftime("%Y-%m-%d")


def main() -> None:
    random.seed(42)
    target_count = int(sys.argv[1]) if len(sys.argv) > 1 else 250

    first_names = [
        "Jane", "John", "Maria", "David", "Sarah", "Michael", "Alice", "Robert",
        "Emily", "Daniel", "Laura", "James", "Olivia", "William", "Sophia",
        "Liam", "Isabella", "Noah", "Mia", "Ethan", "Ava", "Lucas", "Amelia"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
        "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
    ]
    streets = ["Maple St", "Oak Dr", "Pine Ave", "Cedar Ln", "Elm St", "Birch Rd"]
    cities = ["Springfield", "Riverton", "Lakeside", "Fairview", "Hillcrest"]

    conditions_pool = [
        "Type 2 Diabetes", "Hypertension", "Asthma", "High Cholesterol",
        "Hypothyroidism", "Depression", "Anxiety", "Arthritis",
        "COPD", "GERD", "Allergic Rhinitis"
    ]
    meds_pool = [
        "Metformin", "Lisinopril", "Albuterol", "Atorvastatin", "Levothyroxine",
        "Sertraline", "Escitalopram", "Ibuprofen", "Omeprazole", "Amlodipine"
    ]

    genders = ["F", "M"]

    patients = []
    used_names = set()
    for i in range(1, target_count + 1):
        # Build unique-ish names
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        name = f"{fn} {ln}"
        # Avoid too many duplicates in a row
        if name in used_names:
            name = f"{fn} {ln}-{random.randint(2, 999)}"
        used_names.add(name)

        age = random.randint(18, 90)
        gender = random.choice(genders)

        num_conds = 0 if random.random() < 0.1 else random.randint(1, 3)
        conds = random.sample(conditions_pool, k=num_conds)
        num_meds = 0 if random.random() < 0.15 else random.randint(1, 3)
        meds = random.sample(meds_pool, k=num_meds)

        visits = sorted({rand_date() for _ in range(random.randint(1, 4))})

        street_num = random.randint(100, 999)
        addr = f"{street_num} {random.choice(streets)}, {random.choice(cities)}"

        note_templates = [
            "Patient has responded well to {drug}. {extra}",
            "Condition stable on current regimen. {extra}",
            "Follow-up recommended in 3 months. {extra}",
            "Lifestyle modifications discussed. {extra}"
        ]
        extra_notes = [
            "Blood pressure stable.",
            "A1C trending down.",
            "Symptoms improved.",
            "No adverse effects reported.",
            "Needs vaccination update."
        ]
        drug_for_note = random.choice(meds or ["current therapy"])
        notes = random.choice(note_templates).format(
            drug=drug_for_note, extra=random.choice(extra_notes)
        )

        patients.append({
            "id": f"P{i:04d}",
            "name": name,
            "age": age,
            "gender": gender,
            "conditions": conds,
            "medications": meds,
            "notes": notes,
            "address": addr,
            "visit_dates": visits,
        })

    out_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "mock_patient_data.json")
    with open(out_path, "w") as f:
        json.dump(patients, f, indent=2)

    print(f"Wrote {len(patients)} patients to {out_path}")


if __name__ == "__main__":
    main()

