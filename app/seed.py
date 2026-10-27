"""Seed the SQLite database with Northwind Labs kit and realistic multi-stage reviews."""
from datetime import date
from app.db import SessionLocal, init_db
from app.kit import load_kit
from app.models import ApprovalAudit, Comment, FindingRow, Organisation, Review, ReviewRevision
from app.review import run_review

def seed():
    init_db()
    session = SessionLocal()
    try:
        # Check if org exists or load kit
        org = session.query(Organisation).first()
        org_id = org.id if org else load_kit(session, "sample_kit/northwind.json")

        # If reviews already exist, we don't duplicate
        existing = session.query(Review).filter(Review.org_id == org_id).count()
        if existing >= 3:
            print(f"Database already has {existing} reviews for Org {org_id}.")
            return

        today = date(2026, 10, 25)

        # 1. Review in "In Review" status (waiting for Manager approval)
        r1 = run_review(
            session=session,
            org_id=org_id,
            text="We are excited to share that FlowDesk plans start at $12 per user per month. Try the tool now to empower your teams with revolutionary collaboration.",
            channel="LinkedIn post",
            use_ai=False,
            today=today,
            title="Q4 Product Pricing Announcement",
            creator_name="Maya (Content Creator)",
        )
        rev1 = session.get(Review, r1["review_id"])
        rev1.status = "in_review"
        rev1.audit_logs.append(
            ApprovalAudit(
                action="submit_for_review",
                actor_name="Maya (Content Creator)",
                actor_role="creator",
                notes="Submitted for brand manager review ahead of tomorrow's launch.",
            )
        )
        rev1.comments.append(
            Comment(
                user_name="Jordan (Brand Manager)",
                user_role="manager",
                message="Checking terminology now. Remember we cannot use hype words like 'revolutionary'.",
            )
        )

        # 2. Review in "Changes Requested" status (Needs revision by creator)
        r2 = run_review(
            session=session,
            org_id=org_id,
            text="FlowDesk is used by over 5 million customers worldwide with guaranteed 100% secure storage.",
            channel="Email Newsletter",
            use_ai=False,
            today=today,
            title="Global Customer Milestone Newsletter",
            creator_name="Maya (Content Creator)",
        )
        rev2 = session.get(Review, r2["review_id"])
        rev2.status = "changes_requested"
        rev2.audit_logs.append(
            ApprovalAudit(
                action="submit_for_review",
                actor_name="Maya (Content Creator)",
                actor_role="creator",
                notes="Initial draft sent for review.",
            )
        )
        rev2.audit_logs.append(
            ApprovalAudit(
                action="request_changes",
                actor_name="Rachel (Legal Reviewer)",
                actor_role="reviewer",
                notes="Legal hold: '100% secure' is an absolute guarantee. Customer number contradicts Fact Sheet v3 (should be 3 million teams).",
            )
        )
        rev2.comments.append(
            Comment(
                user_name="Rachel (Legal Reviewer)",
                user_role="reviewer",
                message="Please revise the customer claim to 3 million teams and remove absolute security guarantees before we sign off.",
            )
        )

        # 3. Review in "Approved" status (Ready for publishing)
        r3 = run_review(
            session=session,
            org_id=org_id,
            text="Northwind Labs is proud to support more than 3 million teams globally with FlowDesk. Built with strong security controls and SOC 2 Type II certification, FlowDesk plans start at $12 per user with 99.9% uptime.",
            channel="Blog",
            use_ai=False,
            today=today,
            title="Enterprise Security & Reliability Whitepaper",
            creator_name="Maya (Content Creator)",
        )
        rev3 = session.get(Review, r3["review_id"])
        rev3.status = "approved"
        # Mark findings as accepted/resolved
        for f in rev3.findings:
            f.status = "accepted"
        rev3.audit_logs.append(
            ApprovalAudit(
                action="submit_for_review",
                actor_name="Maya (Content Creator)",
                actor_role="creator",
                notes="Final whitepaper copy submitted.",
            )
        )
        rev3.audit_logs.append(
            ApprovalAudit(
                action="approve",
                actor_name="Jordan (Brand Manager)",
                actor_role="manager",
                notes="All claims and tone fully align with Northwind brand standards. Approved!",
            )
        )
        rev3.comments.append(
            Comment(
                user_name="Jordan (Brand Manager)",
                user_role="manager",
                message="Looks spotless! Great adherence to the fact sheet.",
            )
        )

        session.commit()
        print(f"Successfully seeded demo reviews for Org {org_id}!")
    finally:
        session.close()

if __name__ == "__main__":
    seed()
