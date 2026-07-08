import csv
import random
from faker import Faker

fake = Faker()
random.seed(42)

rows = []
for i in range(10000):
    rows.append({
        'ID': i + 1,
        'Full Name': fake.name(),
        'Email': fake.email() if random.random() > 0.1 else f"invalid-email-{i}",
        'Phone': fake.phone_number(),
        'Company': fake.company(),
        'Address': fake.address().replace('\n', ', '),
        'Notes': fake.sentence(nb_words=12),
        'Salary': random.randint(40000, 150000),
        'Department': random.choice(['Engineering', 'Marketing', 'Sales', 'HR', 'Finance']),
        'Join Date': fake.date_between(start_date='-5y', end_date='today').strftime('%d/%m/%Y'),
    })

with open('test_large_dataset.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows")