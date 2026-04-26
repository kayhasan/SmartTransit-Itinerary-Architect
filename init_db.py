# init_db.py
import sqlite3

connection = sqlite3.connect('voya.db')
cursor = connection.cursor()

# 1. Create the 'places' table (if it doesn't already exist)
create_places_table_query = """
CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, city TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('Restaurant', 'Shopping', 'Attraction', 'Hotel')),
    budget_level TEXT NOT NULL CHECK(budget_level IN ('Low-Budget', 'Affordable', 'Expensive')),
    description TEXT, rating REAL, is_halal BOOLEAN, latitude REAL, longitude REAL
);
"""
cursor.execute(create_places_table_query)
print("Table 'places' checked/created.")

# 2. --- NEW: Create the 'airport_transfers' table ---
create_transfers_table_query = """
CREATE TABLE IF NOT EXISTS airport_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL UNIQUE,
    low_budget_details TEXT NOT NULL,
    affordable_details TEXT NOT NULL,
    expensive_details TEXT NOT NULL
);
"""
cursor.execute(create_transfers_table_query)
print("Table 'airport_transfers' checked/created.")


# --- ADDING DATA (with checks to prevent duplicates) ---

# Add initial places for Kuala Lumpur
kl_places = [
    ('Petronas Twin Towers', 'Kuala Lumpur', 'Attraction', 'Affordable', 'Iconic 88-story twin skyscrapers with a sky bridge and observation deck.', 4.7, None, 3.1579, 101.7123),
    ('Suria KLCC', 'Kuala Lumpur', 'Shopping', 'Expensive', 'A premier shopping mall at the base of the Petronas Towers, featuring luxury brands and an aquarium.', 4.6, None, 3.1576, 101.7121),
    ('Madam Kwan''s', 'Kuala Lumpur', 'Restaurant', 'Affordable', 'Famous for serving a variety of delicious, authentic Malaysian dishes in a comfortable setting.', 4.2, True, 3.1571, 101.7128)
]
# Only insert if the place doesn't exist
for place in kl_places:
    cursor.execute("SELECT id FROM places WHERE name = ? AND city = ?", (place[0], place[1]))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO places (name, city, category, budget_level, description, rating, is_halal, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", place)
        print(f"Added place: {place[0]}")

# --- NEW: Add initial airport transfer info for Kuala Lumpur ---
kl_transfer_info = (
    'Kuala Lumpur',
    'From KLIA/KLIA2, take the Airport Bus Service to KL Sentral. It is the cheapest option, offering a comfortable ride directly to the city''s main transport hub.',
    'The KLIA Ekspres train is a fast and reliable option, taking you from the airport to KL Sentral in just 28 minutes. Taxis or ride-sharing services (like Grab) are also readily available.',
    'Arrange for a private airport transfer or use a premium taxi service. This offers a door-to-door, hassle-free journey directly to your hotel accommodation.'
)
# Only insert if the city doesn't exist to avoid duplicates
cursor.execute("SELECT id FROM airport_transfers WHERE city = ?", (kl_transfer_info[0],))
if cursor.fetchone() is None:
    cursor.execute("INSERT INTO airport_transfers (city, low_budget_details, affordable_details, expensive_details) VALUES (?, ?, ?, ?)", kl_transfer_info)
    print(f"Added airport transfer info for {kl_transfer_info[0]}")


connection.commit()
connection.close()

print("Database initialized and connection closed.")