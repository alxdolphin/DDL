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

library_ids = {
        9393: "Appoquinimink Public Library",
        9394: "Bear Public Library",
        9395: "Brandywine Hundred Library",
        9410: "Bridgeville Public Library",
        9396: "Claymont Public Library",
        9397: "Corbit-Calloway Memorial Library",
        9398: "Delaware City Public Library",
        9411: "Delmar Public Library",
        8206: "Dover Public Library",
        9399: "Elsmere Public Library",
        9412: "Frankford Public Library",
        9369: "Georgetown Public Library",
        9413: "Greenwood Public Library",
        9407: "Harrington Public Library",
        9400: "Hockessin Public Library",
        9408: "Kent County Public Library",
        9401: "Kirkwood Library",
        9414: "Laurel Public Library",
        9415: "Lewes Public Library",
        9409: "Milford Public Library",
        9416: "Millsboro Public Library",
        9417: "Milton Public Library",
        9402: "New Castle Public Library",
        9403: "Newark Free Library",
        9418: "Rehoboth Beach Public Library",
        9404: "Route 9 Library & Innovation Center",
        9419: "Seaford District Library",
        9420: "Selbyville Public Library",
        9181: "Smyrna Public Library",
        9421: "South Coastal Public Library",
        8205: "Wilmington Public Library",
        9405: "Wilmington Public Library - North Branch",
        9406: "Woodlawn Public Library"
    }

def get_library_ids():
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

def get_library_choice(library_ids):
    library_names = list(library_ids.values())
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
            
        for id, name in library_ids.items():
            if name.lower() == selected.lower():
                if id not in selected_ids:
                    selected_ids.append(id)
                    print(f"Added {name} to selection.")
                else:
                    print(f"{name} is already selected.")
                break
        else:
            print("Library not found. Please try again.")

def main():
    user_date = input("Enter a date (YYYY-MM-DD): ")
    try:
        datetime.strptime(user_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        return

    calendar_ids = get_library_choice(library_ids)

    try:
        token = get_access_token()
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
                library_id = event.get('calendar', {}).get('id', 'Unknown library')
                library_name = library_ids.get(library_id, 'Unknown library')
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
            print(f"\nNo spaces information found for {user_date}.")
            
    except requests.HTTPError as e:
        print(f"HTTP error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()