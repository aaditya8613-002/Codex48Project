from datetime import date

from app.claims import FactRef, check_claims, format_value, to_findings

TEAMS = FactRef(1, "customer_teams", "More than 3 million teams use FlowDesk.", 3e6, "", ["teams"], "Fact sheet v3",
                date(2026, 1, 1))
UPTIME = FactRef(2, "uptime", "99.9% uptime.", 99.9, "%", ["uptime"], "Status report", date(2026, 7, 1))
PRICE = FactRef(3, "price", "From $12 per user.", 12, "usd", ["per user"], "Pricing", date(2026, 10, 1))
COUNTRIES = FactRef(4, "countries", "40 countries.", 40, "", ["countries"], "Fact sheet v3")
SOC2 = FactRef(5, "soc2", "SOC 2 Type II certified.", None, "", ["soc 2"], "Audit letter")
FACTS = [TEAMS, UPTIME, PRICE, COUNTRIES, SOC2]
TODAY = date(2026, 10, 25)


def verdict(text, facts=FACTS):
    return [(r.verdict, r.text) for r in check_claims(text, facts, TODAY)]


def test_outdated_number_is_contradicted_with_fix():
    [r] = check_claims("Used by over 5 million teams", FACTS, TODAY)
    assert r.verdict == "contradicted" and r.suggestion == "3 million" and r.fact.id == 1
    assert r.text == "over 5 million"


def test_lower_bound_qualifier_supported_when_below_fact():
    assert verdict("Over 2 million teams use it") == [("supported", "Over 2 million")]
    assert verdict("More than 3 million teams use it")[0][0] == "supported"


def test_short_forms_and_commas():
    assert verdict("3M teams trust it")[0][0] == "supported"
    assert verdict("3,000,000 teams trust it")[0][0] == "supported"
    assert verdict("5M teams trust it")[0][0] == "contradicted"


def test_percentages_use_percentage_points():
    assert verdict("99.9% uptime")[0][0] == "supported"
    assert verdict("99.99% uptime")[0][0] == "contradicted"
    assert verdict("100% uptime")[0][0] == "contradicted"


def test_currency_unit_must_match():
    assert verdict("Starts at $12 per user")[0][0] == "supported"
    assert verdict("Starts at $9 per user")[0][0] == "contradicted"


def test_each_number_uses_the_fact_next_to_it():
    assert [v for v, _ in verdict("3 million teams in 40 countries")] == ["supported", "supported"]
    assert [v for v, _ in verdict("3 million teams in 60 countries")] == ["supported", "contradicted"]


def test_unverifiable_number_and_superlative_say_cannot_verify():
    assert verdict("Revenue grew 45% last year")[0][0] == "cannot_verify"
    assert verdict("We are the fastest in the market")[0][0] == "cannot_verify"


def test_numbers_without_claim_cues_are_ignored():
    assert verdict("Join us on 12 November at 10 am") == []
    assert verdict("Our 2026 roadmap is calm") == []
    assert verdict("See Q3 results") == []


def test_superlative_backed_by_non_numeric_fact_is_supported():
    assert verdict("The most trusted option, SOC 2 certified")[0][0] == "supported"


def test_expired_fact_cannot_verify():
    old = FactRef(9, "customer_teams", "2 million teams.", 2e6, "", ["teams"], "Fact sheet v2", date(2024, 1, 1), date(2025, 12, 31))
    [r] = check_claims("2 million teams use it", [old], TODAY)
    assert r.verdict == "cannot_verify" and "expired" in r.explanation


def test_supported_claims_are_not_findings():
    results = check_claims("3 million teams. 5 million teams.", FACTS, TODAY)
    assert [f.verdict for f in to_findings(results)] == ["contradicted"]


def test_format_value():
    assert format_value(3e6, "") == "3 million"
    assert format_value(99.9, "%") == "99.9%"
    assert format_value(12, "usd") == "$12"


def test_years_must_match_exactly():
    founded = FactRef(6, "founded", "Founded in 2019.", 2019, "", ["founded"], "Company profile")
    assert verdict("Northwind was founded in 2019", [founded])[0][0] == "supported"
    assert verdict("Northwind was founded in 2018", [founded])[0][0] == "contradicted"
    assert verdict("Northwind was founded in 2015", [founded])[0][0] == "contradicted"
