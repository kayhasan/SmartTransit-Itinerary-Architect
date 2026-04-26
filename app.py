# app.py
import os, json, sqlite3, requests, re
import google.generativeai as genai
from flask import Flask, render_template, request

app = Flask(__name__)
ALL_COUNTRIES = [ "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria",
    "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia",
    "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo, Democratic Republic of the",
    "Congo, Republic of the", "Costa Rica", "Cote d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti",
    "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini",
    "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala",
    "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland",
    "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Kosovo", "Kuwait", "Kyrgyzstan", "Laos",
    "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar", "Malawi", "Malaysia",
    "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco",
    "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand",
    "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama",
    "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda",
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe",
    "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands",
    "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland",
    "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia",
    "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay",
    "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe" ] # List truncated for brevity

try:
    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)
    generation_config = genai.GenerationConfig(response_mime_type="application/json")
    model = genai.GenerativeModel('gemini-1.5-flash-latest', generation_config=generation_config)
except KeyError: model = None

try:
    weather_api_key = os.environ["OPENWEATHER_API_KEY"]
except KeyError: weather_api_key = None

try:
    pexels_api_key = os.environ["PEXELS_API_KEY"]
except KeyError: pexels_api_key = None

def get_pexels_image_url(query):
    if not pexels_api_key: return "https://images.pexels.com/photos/1072179/pexels-photo-1072179.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
    headers = {"Authorization": pexels_api_key}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data["photos"]: return data["photos"][0]["src"]["large"]
        else: return "https://images.pexels.com/photos/1072179/pexels-photo-1072179.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Pexels image for '{query}': {e}")
        return "https://images.pexels.com/photos/1072179/pexels-photo-1072179.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"

def get_weather(city_name):
    if not weather_api_key: return None
    params = {'q': city_name, 'appid': weather_api_key, 'units': 'metric'}
    try:
        response = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException: return None

def get_clothing_suggestion(weather_data):
    if not weather_data: return {"suggestion": "Weather data unavailable.", "icon": "unknown"}
    temp = weather_data['main']['temp']
    condition = weather_data['weather'][0]['main'].lower()
    if "rain" in condition: return {"suggestion": "Pack a waterproof jacket and umbrella.", "icon": "umbrella"}
    if temp > 25: return {"suggestion": "Warm weather. T-shirts and shorts are perfect.", "icon": "tshirt"}
    if temp > 15: return {"suggestion": "Mild weather. A light jacket is a good idea.", "icon": "sweater"}
    return {"suggestion": "It's cool. Pack a warm jacket and sweaters.", "icon": "jacket"}

def get_places_from_db(city, budget):
    conn = sqlite3.connect('voya.db')
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM places WHERE city LIKE ? AND budget_level = ?", (f'%{city}%', budget))
    places = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return places

# --- NEW: Function to get airport transfer info from our database ---
def get_airport_transfer_from_db(city):
    conn = sqlite3.connect('voya.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM airport_transfers WHERE city LIKE ?", (f'%{city}%',))
    transfer_info = cursor.fetchone()
    conn.close()
    return dict(transfer_info) if transfer_info else None

def get_ai_plan_with_db_data(destination, duration, budget, departure_country, places_from_db):
    places_str = "\n".join([f"- {p['name']} ({p['category']}): {p['description']}" for p in places_from_db])
    
    # --- MODIFIED PROMPT ---
    # The 'airport_transfer' object has been removed from the requested JSON structure.
    prompt = f"""
    Act as an expert travel planner. Based on the user's request and my curated list of places, generate a complete travel plan.
    **User's Request:**
    - Destination: {destination}
    - Duration: {duration} days
    - Budget: {budget}
    - Departure Country: {departure_country}

    **Curated Places from My Database (Prioritize using these):**
    {places_str}

    Return a single, valid JSON object. For hotels, food, and shopping, use the provided places first. If you need more suggestions, you MUST generate new ones and include their estimated 'latitude' and 'longitude'.
    
    **JSON Structure (airport_transfer section is now omitted):**
    {{
      "visa_info": {{ "required": boolean, "details": "...", "official_url": "..." }},
      "itinerary": [ {{ "day": int, "title": "...", "activities": ["..."] }} ],
      "suggested_hotels": [ {{ "name": "...", "latitude": float, "longitude": float, ... }} ],
      "suggested_food": [ {{ "name": "...", "latitude": float, "longitude": float, ... }} ],
      "suggested_shopping": [ {{ "name": "...", "latitude": float, "longitude": float, ... }} ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "")
        def markdown_to_html(text): return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        data = json.loads(cleaned_response_text)
        for day_plan in data.get('itinerary', []):
            day_plan['activities'] = [markdown_to_html(act) for act in day_plan.get('activities', [])]
        return data
    except Exception as e:
        print(f"Error generating or parsing travel plan: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if model is None or weather_api_key is None or pexels_api_key is None:
        error_message = "Configuration Error: An API key is not set. Please contact the site administrator."
        return render_template('index.html', error=error_message, countries=ALL_COUNTRIES)

    if request.method == 'POST':
        destination = request.form.get('destination', '').strip()
        city = destination.split(',')[0].strip()
        duration_str = request.form.get('duration')
        budget = request.form.get('budget')
        departure_country = request.form.get('departure_country')

        if not all([destination, duration_str, budget, departure_country]):
            return render_template('index.html', error="Please fill in all fields.", countries=ALL_COUNTRIES)

        try:
            duration = int(duration_str)
            if duration < 1: raise ValueError
        except (ValueError, TypeError):
            return render_template('index.html', error="Please enter a valid number for the duration.", countries=ALL_COUNTRIES)
        
        # --- Fetch all data ---
        places_from_db = get_places_from_db(city, budget)
        airport_transfer_info = get_airport_transfer_from_db(city) # NEW
        travel_plan = get_ai_plan_with_db_data(destination, duration, budget, departure_country, places_from_db)
        destination_weather = get_weather(city)
        origin_weather = get_weather(departure_country)
        clothing_suggestion = get_clothing_suggestion(destination_weather)

        if not travel_plan:
            return render_template('index.html', error="Sorry, we couldn't generate a travel plan.", countries=ALL_COUNTRIES)
        
        map_places = []
        for category_key in ['suggested_hotels', 'suggested_food', 'suggested_shopping']:
            for place in travel_plan.get(category_key, []):
                if place.get('latitude') and place.get('longitude'):
                    map_places.append({"name": place.get("name"), "latitude": place.get("latitude"), "longitude": place.get("longitude"), "category": category_key.replace("suggested_", "").capitalize()})

        for category in ['suggested_hotels', 'suggested_food', 'suggested_shopping']:
            for item in travel_plan.get(category, []):
                item['image_url'] = get_pexels_image_url(item.get('image_keywords', f"{item.get('name')} {city}"))

        return render_template('index.html', 
                               travel_plan=travel_plan, countries=ALL_COUNTRIES, destination=destination,
                               budget=budget.lower().replace('-', '_'), 
                               airport_transfer=airport_transfer_info, # NEW
                               places_for_map=map_places, destination_weather=destination_weather,
                               origin_weather=origin_weather, clothing_suggestion=clothing_suggestion)

    return render_template('index.html', countries=ALL_COUNTRIES)

if __name__ == '__main__':
    app.run(debug=True)