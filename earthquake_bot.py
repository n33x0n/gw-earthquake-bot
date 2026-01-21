"""
GW Earthquake Bot
Version: 1.0.1

Author: Tomasz Lebioda
Email: tlebioda@gmail.com
License: MIT
"""

import requests
import smtplib
from email.message import EmailMessage
import json
import time
import datetime
import os
import sys

DW_API_KEY = ""  # paste your Datawrapper API key here

EMAIL_SENDER = ""  # paste your Gmail address here
EMAIL_PASSWORD = ""  # paste your Gmail App Password here
EMAIL_RECIPIENT = ""  # paste primary recipient email here
EMAIL_CC = ""  # paste CC recipient email here

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"

CHECK_INTERVAL_SECONDS = 300
TEST_MODE = "--test" in sys.argv

HISTORY_FILE = "processed_ids.json"

DW_FOLDER_ID = None  # paste your Datawrapper folder ID here
DW_ZOOM_LEVEL = 6


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return list(set(json.load(f)))
        except json.JSONDecodeError:
            print(f"Warning: {HISTORY_FILE} is corrupted. Starting with empty history.")
            return []
    return []


def save_history(history_list):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history_list, f)
    except Exception as e:
        print(f"Error saving history: {e}")


def create_datawrapper_map(lat, lon, place, mag, geojson_payload=None):
    headers = {
        "Authorization": f"Bearer {DW_API_KEY}",
        "Content-Type": "application/json"
    }
    
    create_url = "https://api.datawrapper.de/v3/charts"
    payload = {
        "title": f"Trzęsienie ziemi: {place}",
        "type": "locator-map"
    }
    
    if DW_FOLDER_ID:
        payload["folderId"] = DW_FOLDER_ID

    payload["metadata"] = {
        "visualize": {
            "view": {
                "center": [lon, lat],
                "zoom": DW_ZOOM_LEVEL
            }
        }
    }
    
    try:
        print(f"Creating Datawrapper chart for {place}...")
        resp = requests.post(create_url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        chart_data = resp.json()
        chart_id = chart_data['id']
        print(f"Chart created with ID: {chart_id}")

        markers_data = {
            "markers": [
                {
                    "type": "point",
                    "title": f"{place} ({mag}M)",
                    "icon": {
                        "path": "M469 850c-259 0-469-210-469-469 0-259 210-469 469-469 259 0 469 210 469 469 0 259-210 469-469 469z m0-8c254 0 461-206 461-461 0-254-207-461-461-461-255 0-461 207-461 461 0 255 206 461 461 461z m0-84c-208 0-377-168-377-377 0-208 169-377 377-377 208 0 377 169 377 377 0 209-169 377-377 377z m0-13c201 0 364-163 364-364 0-201-163-364-364-364-201 0-364 163-364 364 0 201 163 364 364 364z m0-78c-158 0-286-128-286-286 0-158 128-286 286-286 158 0 286 128 286 286 0 158-128 286-286 286z m0-24c145 0 262-117 262-262 0-145-117-262-262-262-145 0-262 117-262 262 0 145 117 262 262 262z m0-72c-105 0-190-85-190-190 0-104 85-190 190-190 104 0 190 86 190 190 0 105-86 190-190 190z m0-42c82 0 148-66 148-148 0-82-66-148-148-148-82 0-148 66-148 148 0 82 66 148 148 148z m88-148a85 85 0 0 0-85-84 85 85 0 0 0-84 84 85 85 0 0 0 84 85 85 85 0 0 0 85-85z",
                        "height": 700,
                        "width": 1000
                    },
                    "scale": 1,
                    "markerColor": "#cc0000",
                    "anchor": "top-center",
                    "offsetY": 0,
                    "offsetX": 0,
                    "text": {
                        "color": "#333333",
                        "fontSize": 14,
                        "halo": "#f2f3f0"
                    },
                    "rotate": 0,
                    "visible": True,
                    "visibility": {
                        "mobile": True,
                        "desktop": True
                    },
                    "coordinates": [lon, lat],
                    "tooltip": {
                        "text": f"Magnituda: {mag}\nLokalizacja: {place}"
                    }
                }
            ]
        }
        
        upload_url = f"https://api.datawrapper.de/v3/charts/{chart_id}/data"
        headers_upload = {
            "Authorization": f"Bearer {DW_API_KEY}",
            "Content-Type": "text/csv"
        }
        
        print("Uploading marker data...")
        resp_upload = requests.put(
            upload_url, 
            headers=headers_upload, 
            data=json.dumps(markers_data),
            timeout=15
        )
        resp_upload.raise_for_status()
        print("Marker data uploaded.")

        publish_url = f"https://api.datawrapper.de/v3/charts/{chart_id}/publish"
        resp_publish = requests.post(publish_url, headers=headers, timeout=15)
        
        if resp_publish.status_code == 403:
            print("Error: 403 Forbidden on Publish. API Key missing scopes.")
            return None, None
             
        resp_publish.raise_for_status()
        publish_data = resp_publish.json()
        print("Chart published.")

        public_url = publish_data['data']['publicUrl']
        embed_codes = publish_data['data']['metadata']['publish']['embed-codes']
        embed_code = embed_codes.get('embed-method-responsive')

        if not embed_code:
            embed_code = list(embed_codes.values())[0] if embed_codes else "Brak kodu do osadzenia"

        return public_url, embed_code

    except requests.exceptions.RequestException as e:
        print(f"Datawrapper API Error: {e}")
        try:
            if 'resp' in locals():
                print(f"Create response: {resp.text}")
            if 'resp_upload' in locals():
                print(f"Upload response: {resp_upload.text}")
            if 'resp_publish' in locals():
                print(f"Publish response: {resp_publish.text}")
        except:
            pass
        return None, None


def send_alert(earthquake_data, map_url, embed_code, geojson_content):
    props = earthquake_data['properties']
    geo = earthquake_data['geometry']
    
    mag = props.get('mag')
    place = props.get('place')
    time_ms = props.get('time')
    tsunami = props.get('tsunami')
    usgs_url = props.get('url', 'https://earthquake.usgs.gov/')
    
    event_time = datetime.datetime.fromtimestamp(time_ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    
    lat = geo['coordinates'][1]
    lon = geo['coordinates'][0]

    tsunami_txt = "TAK - MOŻLIWOŚĆ" if tsunami == 1 else "BRAK"
    google_maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    msg = EmailMessage()
    msg['Subject'] = f"ALARM: Trzęsienie ziemi {mag}M - {place}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECIPIENT
    msg['Cc'] = EMAIL_CC

    body = f"""
ALARM: TRZĘSIENIE ZIEMI
=======================

MAGNITUDA: {mag}
LOKALIZACJA: {place}
CZAS: {event_time}
OSTRZEŻENIE PRZED TSUNAMI: {tsunami_txt}

MAPA INTERAKTYWNA (DATAWRAPPER)
-------------------------------
Link publiczny: {map_url}

KOD DO OSADZENIA (RESPONSYWNY):
-------------------------------
{embed_code}

LINK DO GOOGLE MAPS:
--------------------
{google_maps_link}

WIĘCEJ INFORMACJI (USGS):
-------------------------
{usgs_url}

(Załączono surowe dane JSON)
    """
    msg.set_content(body)

    try:
        geojson_str = json.dumps(geojson_content, indent=2)
        filename_id = props.get('code', 'unknown_id')
        msg.add_attachment(geojson_str.encode('utf-8'),
                           maintype='application',
                           subtype='json',
                           filename=f"earthquake_{filename_id}.json")
    except Exception as e:
        print(f"Error attaching GeoJSON: {e}")

    try:
        print(f"Sending email to {EMAIL_RECIPIENT}...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("Email sent successfully.")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def translate_place(place_text):
    replacements = {
        "E of": "na wschód od",
        "W of": "na zachód od",
        "N of": "na północ od",
        "S of": "na południe od",
        "NE of": "na północny wschód od",
        "NW of": "na północny zachód od",
        "SE of": "na południowy wschód od",
        "SW of": "na południowy zachód od"
    }
    
    translated = place_text
    for en, pl in replacements.items():
        if f" {en} " in translated:
            translated = translated.replace(f" {en} ", f" {pl} ")
        elif translated.startswith(f"{en} "):
            translated = translated.replace(f"{en} ", f"{pl} ", 1)
             
    return translated


def earthquake_monitor():
    print(f"Starting Earthquake Bot (Test Mode: {TEST_MODE})...")
    
    processed_ids = load_history()
    print(f"Loaded {len(processed_ids)} processed events.")

    while True:
        try:
            print(f"Checking USGS feed at {datetime.datetime.now().strftime('%H:%M:%S')}...")
            response = requests.get(USGS_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            
            if not features:
                print("No earthquakes found in feed.")
                if TEST_MODE:
                    print("TEST_MODE: No earthquakes found to test.")
                    return
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue

            features.sort(key=lambda x: x['properties']['time'])
            
            processed_count = 0
            
            if TEST_MODE and features:
                features = [features[-1]]
                print(f"TEST_MODE: Processing event {features[0]['id']} regardless of history.")

            for feature in features:
                event_id = feature['id']
                props = feature['properties']
                mag = props.get('mag')
                place = props.get('place')

                if (mag is None or mag <= 5.0) and not TEST_MODE:
                    continue

                if not TEST_MODE and event_id in processed_ids:
                    continue
                
                print(f"Processing new event: {place} ({mag}M)...")
                
                geo = feature['geometry']
                lon = geo['coordinates'][0]
                lat = geo['coordinates'][1]
                
                place_pl = translate_place(place)

                detail_url = feature['properties'].get('detail')
                geojson_content = None
                if detail_url:
                    try:
                        print(f"Fetching event detail from: {detail_url}")
                        r_detail = requests.get(detail_url, timeout=10)
                        r_detail.raise_for_status()
                        geojson_content = r_detail.json()
                    except Exception as e:
                        print(f"Error fetching detail GeoJSON: {e}")
                        geojson_content = feature
                else:
                    geojson_content = feature

                dw_url, dw_embed_code = create_datawrapper_map(lat, lon, place_pl, mag, geojson_content)
                
                if dw_url:
                    feature_copy = json.loads(json.dumps(feature))
                    feature_copy['properties']['place'] = place_pl
                    
                    if send_alert(feature_copy, dw_url, dw_embed_code, geojson_content):
                        processed_ids.append(event_id)
                        processed_count += 1
                    else:
                        print(f"Map generation failed for {event_id}. Will retry next cycle.")
            
            if processed_count == 0 and not TEST_MODE:
                print("No new earthquakes to process.")

        except requests.exceptions.RequestException as e:
            print(f"Network error fetching USGS feed: {e}")
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")

        if TEST_MODE:
            break

        print(f"Sleeping for {CHECK_INTERVAL_SECONDS} seconds...")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    earthquake_monitor()
