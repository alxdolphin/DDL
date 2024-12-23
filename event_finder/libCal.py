#!/usr/bin/env python
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
API_URL = "https://delawarelibraries.libcal.com/api/1.1"

library_info = {
    "Appoquinimink Public Library": {"cal_id": 9393, "lid": 4419},
    "Bear Public Library": {"cal_id": 9394, "lid": 4420},
    "Brandywine Hundred Library": {"cal_id": 9395, "lid": 4421},
    "Bridgeville Public Library": {"cal_id": 9410, "lid": 4422},
    "Claymont Public Library": {"cal_id": 9396, "lid": 4423},
    "Corbit-Calloway Memorial Library": {"cal_id": 9397, "lid": 4424},
    "Delaware City Public Library": {"cal_id": 9398, "lid": 4425},
    "Delmar Public Library": {"cal_id": 9411, "lid": 4426},
    "Dover Public Library": {"cal_id": 8206, "lid": 4389},
    "Elsmere Public Library": {"cal_id": 9399, "lid": None},
    "Frankford Public Library": {"cal_id": 9412, "lid": 4428},
    "Georgetown Public Library": {"cal_id": 9369, "lid": 4429},
    "Greenwood Public Library": {"cal_id": 9413, "lid": 4430},
    "Harrington Public Library": {"cal_id": 9407, "lid": 4432},
    "Hockessin Public Library": {"cal_id": 9400, "lid": None},
    "Kent County Public Library": {"cal_id": 9408, "lid": 4433},
    "Kirkwood Library": {"cal_id": 9401, "lid": None},
    "Laurel Public Library": {"cal_id": 9414, "lid": 4435},
    "Lewes Public Library": {"cal_id": 9415, "lid": 4436},
    "Milford Public Library": {"cal_id": 9409, "lid": 4437},
    "Millsboro Public Library": {"cal_id": 9416, "lid": 4438},
    "Milton Public Library": {"cal_id": 9417, "lid": 4439},
    "New Castle Public Library": {"cal_id": 9402, "lid": 4468},
    "Newark Free Library": {"cal_id": 9403, "lid": 4470},
    "Rehoboth Beach Public Library": {"cal_id": 9418, "lid": 4441},
    "Route 9 Library & Innovation Center": {"cal_id": 9404, "lid": 4447},
    "Seaford District Library": {"cal_id": 9419, "lid": 4443},
    "Selbyville Public Library": {"cal_id": 9420, "lid": 4444},
    "Smyrna Public Library": {"cal_id": 9181, "lid": 4711},
    "South Coastal Public Library": {"cal_id": 9421, "lid": 4445},
    "Wilmington Public Library": {"cal_id": 8205, "lid": 4391},
    "Wilmington Public Library - North Branch": {"cal_id": 9405, "lid": 4440},
    "Woodlawn Public Library": {"cal_id": 9406, "lid": None}
}

library_ids = {library_info[library]["cal_id"]: library for library in library_info}

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
    rooms = {}
    seen_pending = set()  
    
    for booking in bookings:
        room_name = f"{booking['item_name']} (ID: {booking['eid']})" 
        if room_name not in rooms:
            rooms[room_name] = []
        
        is_confirmed = booking['status'] == 'Confirmed'
        status_indicator = "[CONFIRMED] " if is_confirmed else "[PENDING] "
        
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
    
    return rooms

def main():
    user_date = input("Enter a date (YYYY-MM-DD): ")
    try:
        datetime.strptime(user_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        return

    calendar_ids = get_library_choice(library_info)

    try:
        token = get_access_token()      
        events = get_events(token, user_date, calendar_ids)
        library_id_map = get_library_ids()  # map of cal_id to library name

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
            lid = library_info[library_name]['lid']
            
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