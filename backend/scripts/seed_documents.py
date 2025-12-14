"""Seed the `documents` table with sample rows for testing.
Runs in the application context and is safe to re-run (it skips if documents already exist).
"""
from app import create_app
from app.extensions import db
from app.models import Document


SAMPLES = [
    ("Contract A", "IN-001", "OUT-001", 5, "Contract for services A"),
    ("Report B", "IN-002", "OUT-002", 10, "Monthly report B"),
    ("Invoice C", "IN-003", "OUT-003", 2, "Invoice C details"),
    ("Spec D", "IN-004", "OUT-004", 25, "Technical spec D"),
    ("Letter E", "IN-005", "OUT-005", 1, "Correspondence E"),
    ("Archive F", "IN-006", "OUT-006", 100, "Large archive F"),
    ("Archive G", "IN-007", "OUT-007", 120, "Very large G"),
    ("Memo H", "IN-008", "OUT-008", 3, "Internal memo H"),
    ("Form I", "IN-009", "OUT-009", 4, "Form I details"),
    ("Booklet J", "IN-010", "OUT-010", 15, "Booklet J info"),
]


def seed_documents():
    app = create_app()
    with app.app_context():
        existing = Document.query.count()
        if existing > 0:
            print(f"Documents table already has {existing} rows — skipping seeding.")
            return

        objs = []
        for idx, (title, inc, out, pages, extra) in enumerate(SAMPLES, start=1):
            objs.append(Document(title=title, incoming_number=inc, outgoing_number=out, pages_count=pages, extra_info=extra))

        # add additional generated small documents
        for i in range(11, 51):
            objs.append(Document(title=f"Doc {i}", incoming_number=f"IN-{i:03}", outgoing_number=f"OUT-{i:03}", pages_count=(i % 20) + 1, extra_info=f"Generated doc {i}"))

        db.session.bulk_save_objects(objs)
        db.session.commit()
        print(f"Inserted {len(objs)} sample documents.")


if __name__ == '__main__':
    seed_documents()
