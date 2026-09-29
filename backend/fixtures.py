"""Synthetic demo profiles. These names and traits are fictional and are not sourced from real people."""
PEOPLE = [
    ("Maya Chen", "Product designer", ["design", "travel", "coffee"], ["museum visits", "sketching"], ["city walks", "slow weekends"]),
    ("Arjun Mehta", "Climate researcher", ["climate", "hiking", "books"], ["trail walks", "reading"], ["outdoors", "early mornings"]),
    ("Sofia Rivera", "Architect", ["architecture", "food", "travel"], ["gallery visits", "cooking"], ["city walks", "long dinners"]),
    ("Noah Williams", "Software engineer", ["music", "coffee", "cycling"], ["cycling", "live music"], ["active weekends", "city life"]),
    ("Anika Rao", "Public health researcher", ["books", "food", "gardening"], ["reading", "cooking"], ["slow weekends", "home cooking"]),
    ("Leo Martin", "Photographer", ["travel", "photography", "hiking"], ["trail walks", "street photography"], ["outdoors", "city walks"]),
    ("Priya Shah", "Teacher", ["books", "music", "community"], ["reading", "choir"], ["slow weekends", "community events"]),
    ("Ethan Brooks", "Urban planner", ["architecture", "cycling", "community"], ["cycling", "volunteering"], ["city life", "active weekends"]),
    ("Nina Patel", "Chef", ["food", "travel", "gardening"], ["cooking", "market visits"], ["long dinners", "home cooking"]),
    ("Gabriel Costa", "Musician", ["music", "books", "travel"], ["live music", "reading"], ["city life", "late evenings"]),
    ("Keiko Tanaka", "Data journalist", ["books", "climate", "coffee"], ["reading", "long walks"], ["early mornings", "city walks"]),
    ("Amara Okafor", "Landscape designer", ["gardening", "architecture", "hiking"], ["gardening", "trail walks"], ["outdoors", "slow weekends"]),
    ("Oliver James", "Independent filmmaker", ["film", "food", "music"], ["film screenings", "cooking"], ["long dinners", "city life"]),
    ("Zara Khan", "Policy analyst", ["climate", "community", "travel"], ["volunteering", "museum visits"], ["community events", "city walks"]),
    ("Mateo Silva", "Marine biologist", ["climate", "hiking", "photography"], ["trail walks", "photography"], ["outdoors", "early mornings"]),
    ("Chloe Bennett", "Editor", ["books", "film", "coffee"], ["reading", "film screenings"], ["slow weekends", "city life"]),
    ("Dev Malhotra", "Founder", ["cycling", "food", "community"], ["cycling", "cooking"], ["active weekends", "long dinners"]),
    ("Isabella Rossi", "Art curator", ["architecture", "art", "travel"], ["gallery visits", "museum visits"], ["city walks", "long dinners"]),
    ("Sam Okoye", "Occupational therapist", ["music", "gardening", "community"], ["gardening", "live music"], ["community events", "slow weekends"]),
    ("Freya Nielsen", "Sustainability consultant", ["climate", "cycling", "food"], ["cycling", "market visits"], ["active weekends", "home cooking"]),
    ("Rohan Iyer", "Game developer", ["gaming", "music", "coffee"], ["board games", "live music"], ["city life", "late evenings"]),
    ("Lina Haddad", "Museum educator", ["art", "books", "community"], ["museum visits", "reading"], ["community events", "slow weekends"]),
    ("Theo Fischer", "Outdoor guide", ["hiking", "photography", "travel"], ["trail walks", "camping"], ["outdoors", "early mornings"]),
    ("Aisha Bello", "Food writer", ["food", "books", "travel"], ["cooking", "market visits"], ["home cooking", "long dinners"]),
    ("Lucas Kim", "Sound engineer", ["music", "film", "cycling"], ["live music", "cycling"], ["active weekends", "city life"]),
]

def fixture_profile(index: int):
    name, profession, interests, hobbies, lifestyle = PEOPLE[index]
    topic = interests[0]
    return {"profession": profession, "education": None, "interests": interests, "hobbies": hobbies,
            "lifestyle": lifestyle, "conversation_topics": interests[:2], "preferences": [],
            "summary": f"Synthetic demo profile for {name}, a fictional {profession.lower()} who enjoys {', '.join(interests[:2])}."}
