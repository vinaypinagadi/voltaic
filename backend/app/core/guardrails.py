import re

EMERGENCY_SCHEMES = [
    {
        "category": "medical",
        "keywords": [
            r"\bmedical\b", r"\bheart\s+attack\b", r"\bchest\s+pain\b", r"\bbreathing\s+difficulty\b", 
            r"\bunconscious\b", r"\bstroke\b", r"\bbleeding\b", r"\binjury\b", r"\bambulance\b", 
            r"\bseizure\b", r"\bchoking\b", r"\bpassed\s+out\b"
        ],
        "response": (
            "EMERGENCY PROTOCOL TRIGGERED: Stadium medical services have been notified of your location. "
            "First responders are being dispatched. Please remain where you are if it is safe. "
            "First aid kits and AEDs are located near every major gate entrance. "
            "If you can, signal to the nearest staff member wearing a high-visibility vest."
        ),
        "title": "Medical Incident Reported via Fan Chat",
        "severity": "critical"
    },
    {
        "category": "crowd",
        "keywords": [
            r"\bstampede\b", r"\bcrowd\s+crush\b", r"\bsuffocating\b", r"\bcannot\s+breathe\b", 
            r"\btrampled\b", r"\bstuck\s+in\s+crowd\b", r"\bpanic\b", r"\bgate\s+crush\b", r"\bovercrowding\b"
        ],
        "response": (
            "CROWD EMERGENCY PROTOCOL TRIGGERED: Stadium crowd management center has been alerted. "
            "Staff are being redirected to relieve congestion in your sector. Please move calmly toward the "
            "nearest open exit marked with green exit signs. Avoid pushing and stay clear of bottlenecked corridors."
        ),
        "title": "Crowd Bottleneck/Crush Incident Reported",
        "severity": "critical"
    },
    {
        "category": "fire",
        "keywords": [
            r"\bfire\b", r"\bsmoke\b", r"\bexplosion\b", r"\bbomb\b", r"\bgas\s+leak\b", r"\bweapon\b", r"\bgun\b"
        ],
        "response": (
            "HAZARD PROTOCOL TRIGGERED: Stadium security and emergency services have been alerted. "
            "Evacuate the area immediately in a calm and orderly manner. Follow instructions from stadium "
            "wardens and public address announcements. Do not use elevators; use designated exits."
        ),
        "title": "Hazardous/Safety Threat Incident Reported",
        "severity": "critical"
    }
]

def check_emergency(message: str) -> dict | None:
    """
    Checks if a message contains emergency keywords.
    Returns details if matched, else None.
    """
    cleaned = message.lower()
    for scheme in EMERGENCY_SCHEMES:
        for pattern in scheme["keywords"]:
            if re.search(pattern, cleaned):
                return {
                    "is_emergency": True,
                    "category": scheme["category"],
                    "response": scheme["response"],
                    "title": scheme["title"],
                    "severity": scheme["severity"]
                }
    return None
