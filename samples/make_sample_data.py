"""Generate a messy, fictional customer CSV for demos and tests."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

FIRST = ["Emily", "Michael", "Sarah", "James", "Olivia", "Daniel", "Sophia",
         "William", "Ava", "Ethan", "Mia", "Lucas", "Charlotte", "Henry",
         "Amelia", "Jack", "Grace", "Owen", "Chloe", "Noah"]
LAST = ["Johnson", "Brown", "Davis", "Wilson", "Miller", "Moore", "Taylor",
        "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Clark",
        "Lewis", "Walker", "Hall", "Young", "King", "Wright"]
AREA_CODES = {"Austin": "512", "Chicago": "312", "Denver": "303",
              "Seattle": "206", "Miami": "305"}
COLUMNS = ["name", "email", "phone", "signup_date", "city"]


def make_customers(n):
    combos = random.sample([(f, l) for f in FIRST for l in LAST], n)
    start = date(2023, 1, 1)
    rows = []
    for first, last in combos:
        city = random.choice(list(AREA_CODES))
        rows.append({
            "name": f"{first} {last}",
            "email": f"{first}.{last}@example.com".lower(),
            "phone": f"({AREA_CODES[city]}) 555-01{random.randint(0, 99):02d}",
            "signup_date": (start + timedelta(days=random.randint(0, 730))).isoformat(),
            "city": city,
        })
    return rows


def main():
    rows = make_customers(170)

    # Pick distinct rows to damage, and clean rows to duplicate
    damaged = random.sample(range(len(rows)), 42)
    spaces, bad_email = damaged[:10], damaged[10:18]
    no_email, no_phone = damaged[18:24], damaged[24:32]
    bad_date, no_city = damaged[32:38], damaged[38:42]
    clean_pool = [i for i in range(len(rows)) if i not in damaged]
    dup_sources = random.sample(clean_pool, 20)

    email_breakers = [
        lambda e: e.replace("@", "@@"),
        lambda e: e.split("@")[0] + "@example",
        lambda e: e.replace("@", ""),
        lambda e: e.replace("@example.com", "@.com"),
    ]
    bad_dates = ["2024-02-31", "not a date", "13/45/2024",
                 "2024-13-01", "2023-00-10", "yesterday"]

    for i in spaces:
        rows[i]["name"] = f"  {rows[i]['name']}  "
        rows[i]["city"] = f"  {rows[i]['city']}  "
    for i in bad_email:
        rows[i]["email"] = random.choice(email_breakers)(rows[i]["email"])
    for i in no_email:
        rows[i]["email"] = ""
    for i in no_phone:
        rows[i]["phone"] = ""
    for i, value in zip(bad_date, bad_dates):
        rows[i]["signup_date"] = value
    for i in no_city:
        rows[i]["city"] = ""

    extras = []
    for i in dup_sources[:12]:  # exact duplicates
        extras.append(dict(rows[i]))
    for i in dup_sources[12:]:  # duplicates with a trailing space
        dup = dict(rows[i])
        dup["name"] += " "
        extras.append(dup)
    for _ in range(6):  # fully empty rows
        extras.append({col: "" for col in COLUMNS})

    for extra in extras:
        rows.insert(random.randint(0, len(rows)), extra)

    out_path = Path(__file__).parent / "messy_customers.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()