from app.core.guardrails import check_emergency

def test_no_emergency():
    res = check_emergency("Where is section 102?")
    assert res is None

def test_medical_emergency():
    res = check_emergency("Someone is having a heart attack near Gate A!")
    assert res is not None
    assert res["is_emergency"] is True
    assert res["category"] == "medical"
    assert "medical services" in res["response"]
    assert res["severity"] == "critical"

def test_crowd_emergency():
    res = check_emergency("Help, there's a stampede at Gate B!")
    assert res is not None
    assert res["is_emergency"] is True
    assert res["category"] == "crowd"
    assert "crowd management" in res["response"]

def test_fire_emergency():
    res = check_emergency("There is smoke and fire inside the corridor")
    assert res is not None
    assert res["category"] == "fire"
    assert "HAZARD PROTOCOL" in res["response"]
