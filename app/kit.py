"""Load a brand kit (organisation settings, terms, facts, guideline documents) from JSON."""
import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from .kb.ingest import add_document
from .models import Fact, Organisation, Term


def _d(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def load_kit(session: Session, kit_path: str | Path, embed: bool = True) -> int:
    """Create an organisation from a kit file and return its id."""
    kit_path = Path(kit_path)
    kit = json.loads(kit_path.read_text(encoding="utf-8"))
    o = kit["organisation"]
    org = Organisation(name=o["name"], product_names=o.get("product_names", []), palette=o.get("palette", []))
    session.add(org)
    session.flush()

    for t in kit.get("terms", []):
        session.add(Term(org_id=org.id, kind=t["kind"], phrase=t["phrase"], preferred=t.get("preferred"),
                         reason=t.get("reason", ""), severity=t.get("severity", "medium")))
    for f in kit.get("facts", []):
        session.add(Fact(org_id=org.id, key=f["key"], statement=f["statement"], value=f.get("value"),
                         unit=f.get("unit", ""), keywords=f.get("keywords", []), source=f.get("source", ""),
                         valid_from=_d(f.get("valid_from")), valid_to=_d(f.get("valid_to"))))
    session.commit()

    for d in kit.get("documents", []):
        text = (kit_path.parent / d["file"]).read_text(encoding="utf-8")
        add_document(session, org.id, d["title"], text, filename=d["file"], kind=d.get("kind", "guideline"), embed=embed)
    return org.id
