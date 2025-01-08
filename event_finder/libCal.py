#!/usr/bin/env python
import os
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter
from pathlib import Path

try:
    load_dotenv(override=True)
except Exception:
    pass

config_path = Path(__file__).parent.parent / 'config.json'
with open(config_path) as f:
    config = json.load(f)

CLIENT_ID = config['client_id']
CLIENT_SECRET = config['client_secret']
API_URL = config['api_url']
LIBRARY_INFO = config['library_info']

# add validation for required environment variables
if not all([CLIENT_ID, CLIENT_SECRET, API_URL]):
    raise RuntimeError("Missing required environment variables. Ensure CLIENT_ID, CLIENT_SECRET, and API_URL are set.")

library_ids = {LIBRARY_INFO[library]["cal_id"]: library for library in LIBRARY_INFO}

def get_library_ids():
    """Get mapping of calendar IDs to library names."""
    return library_ids

def get_access_token():
    """Authenticate and get an access token."""
    response = requests.post(API_URL + "/oauth/token", data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    })
    response.raise_for_status()
    return response.json().get('access_token')

def get_events(access_token, date, calendars):
    """Get events for the given date and list of calendars."""
    headers = {'Authorization': f'Bearer {access_token}'}
    events = []

    for calendar_id in calendars:
        params = {
            'cal_id': calendar_id,
            'date': date
        }
        response = requests.get(API_URL + "/events", headers=headers, params=params)
        response.raise_for_status()
        events.extend(response.json().get('events', []))

    # only want events that start and end on the specified date
    filtered_events = [
        event for event in events
        if event['start'].split('T')[0] == date and event['end'].split('T')[0] == date
    ]

    return filtered_events

def strip_html_tags(html_text):
    """Remove HTML tags from a string."""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text()

def get_library_choice(library_info):
    library_names = list(library_info.keys())
    library_completer = FuzzyWordCompleter(library_names)
    selected_ids = []
    
    while True:
        selected = prompt(
            'Enter library name (press Tab for suggestions, press Enter when finished): ',
            completer=library_completer
        ).strip()
        
        if not selected:  # if empty input just send it
            if selected_ids:
                return selected_ids
            print("Please select at least one library.")
            continue
            
        if selected in library_info:
            cal_id = library_info[selected]["cal_id"]
            if cal_id not in selected_ids:
                selected_ids.append(cal_id)
                print(f"Added {selected} to selection.")
            else:
                print(f"{selected} is already selected.")
        else:
            print("Library not found. Please try again.")

def get_space_bookings(access_token, lid, date):
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'lid': lid,
        'date': date,
        'limit': 100,
        'check_in_status': 1,
        'form_answers': 1,
    }
    
    response = requests.get(f"{API_URL}/space/bookings", headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def process_space_availability(bookings):
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    
    rooms = {}
    seen_pending = set()  
    
    for booking in bookings:
        room_name = f"{booking['item_name']} (ID: {booking['eid']})" 
        if room_name not in rooms:
            rooms[room_name] = []
        
        is_confirmed = booking['status'] == 'Confirmed'
        status_indicator = f"{GREEN}[CONFIRMED]{RESET} " if is_confirmed else f"{YELLOW}[PENDING]{RESET} "
        
        booking_key = (
            booking['item_name'], 
            booking['fromDate'],
            booking['toDate'],
            booking.get('nickname', 'Booked')
        )
        
        # skip if it's a duplicate pending booking
        if not is_confirmed and booking_key in seen_pending:
            continue
            
        if not is_confirmed:
            seen_pending.add(booking_key)
            
        rooms[room_name].append({
            'from': datetime.fromisoformat(booking['fromDate']).strftime('%I:%M %p'),
            'to': datetime.fromisoformat(booking['toDate']).strftime('%I:%M %p'),
            'nickname': status_indicator + (booking.get('nickname', 'Booked'))
        })
    
    return dict(sorted(rooms.items()))

def get_space_availability(access_token, lid, date, start_time=None, end_time=None):
    """Search for available spaces within a time range."""
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'lid': lid,
        'date': date,
        'availability': date,  # api expects same date in both fields
        'limit': 100
    }
    
    response = requests.get(f"{API_URL}/space/availability", headers=headers, params=params)
    response.raise_for_status()
    availability_data = response.json()
    
    # filter results if time range specified
    if start_time and end_time:
        filtered_spaces = []
        for space in availability_data:
            # check if space has any availability slots that contain our desired time range
            for slot in space.get('availability', []):
                slot_start = datetime.fromisoformat(slot['from'])
                slot_end = datetime.fromisoformat(slot['to'])
                desired_start = datetime.fromisoformat(f"{date}T{start_time}")
                desired_end = datetime.fromisoformat(f"{date}T{end_time}")
                
                if slot_start <= desired_start and slot_end >= desired_end:
                    filtered_spaces.append(space)
                    break  # no need to check other slots for this space
        return filtered_spaces
    
    return availability_data

def main():
    user_date = input("Enter a date (YYYY-MM-DD): ")
    try:
        datetime.strptime(user_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        return

    # add time range input
    search_available = input("Would you like to search for available spaces? (y/n): ").lower() == 'y'
    start_time = end_time = None
    if search_available:
        start_time = input("Enter start time (HH:MM, 24hr format) or press enter to skip: ")
        if start_time:
            end_time = input("Enter end time (HH:MM, 24hr format): ")
            # validate time format
            try:
                datetime.strptime(start_time, "%H:%M")
                datetime.strptime(end_time, "%H:%M")
            except ValueError:
                print("Invalid time format. Please use HH:MM (24hr format).")
                return

    calendar_ids = get_library_choice(LIBRARY_INFO)
    library_id_map = get_library_ids()  # Moved this line up

    try:
        token = get_access_token()
        
        # First show available spaces if requested
        if search_available:
            print("\nSearching for available spaces...")
            for cal_id in calendar_ids:
                library_name = library_id_map[cal_id]
                lid = LIBRARY_INFO[library_name]['lid']
                
                if lid:
                    try:
                        available_spaces = get_space_availability(token, lid, user_date, start_time, end_time)
                        if available_spaces:
                            print(f"\n{library_name} - Available Spaces:")
                            for space in available_spaces:
                                print(f"\n  {space['name']}:")
                                for slot in space['availability']:
                                    slot_start = datetime.fromisoformat(slot['from']).strftime('%I:%M %p')
                                    slot_end = datetime.fromisoformat(slot['to']).strftime('%I:%M %p')
                                    print(f"    • {slot_start} - {slot_end}")
                        else:
                            print(f"\n{library_name} - No spaces available for requested time.")
                    except Exception as e:
                        print(f"Could not get space availability for {library_name}: {e}")

        events = get_events(token, user_date, calendar_ids)

        if events:
            print(f"\nEvents on {user_date}:")
            for event in events:
                title = event['title']
                start = event['start']
                end = event['end']
                description = strip_html_tags(event.get('description', 'No description available'))
                location = event.get('location', {}).get('name', 'Unknown location')
                print("--------------------------------------------------")
                library_id = event.get('calendar', {}).get('id')
                library_name = library_id_map.get(library_id, 'Unknown library')
                print(f"Library: {library_name}")
                print(f"Location: {location}")
                print(f"Event: {title}")
                print(f"Time: {start} to {end}")
                description_no_line_breaks = description.replace('\n', ' ').replace('\r', '')
                description_no_extra_spaces = ' '.join(description_no_line_breaks.split())
                if len(description_no_extra_spaces) > 77:
                    truncated_description = description_no_extra_spaces[:77]
                    last_space = truncated_description.rfind(' ')
                    if last_space != -1:
                        truncated_description = truncated_description[:last_space]
                    truncated_description += '<...>'
                else:
                    truncated_description = description_no_extra_spaces
                print(f"Description: {truncated_description}")
                print("--------------------------------------------------")
        else:
            print(f"\nNo events found for {user_date}.")
            
        print("\nRoom Availability:")
        for cal_id in calendar_ids:
            library_name = library_id_map[cal_id]
            lid = LIBRARY_INFO[library_name]['lid']
            
            if lid:  # some libraries don't have space booking
                try:
                    bookings = get_space_bookings(token, lid, user_date)
                    rooms = process_space_availability(bookings)
                    
                    if rooms:
                        print(f"\n{library_name}:")
                        for room, bookings in rooms.items():
                            print(f"\n  {room}:")
                            if bookings:
                                for booking in bookings:
                                    print(f"    • {booking['from']} - {booking['to']}: {booking['nickname']}")
                            else:
                                print("    • Available all day")
                except Exception as e:
                    print(f"Could not get space bookings for {library_name}: {e}")
    except requests.HTTPError as e:
        print(f"HTTP error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()