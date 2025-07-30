import sys
from datetime import datetime, timedelta
import requests
import json
import csv
import pytz
from icalendar import Calendar, Event
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def fetch_events(url):
    """
    Fetch event data from the provided URL and return the events list from the 'data' element.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        json_response = response.json()
        events = json_response.get('data', [])
# Print the first event for debugging
#        if events:
#            print("Debug: First event structure:")
#            print(json.dumps(events[0], indent=2))
#            print(f"Debug: Raw category field: {events[0].get('category')}")
#            print(f"Debug: Type of category field: {type(events[0].get('category'))}")
#        else:
#            print("Debug: No events in response.")
        return events
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing JSON: {e}")
        return None



def search_events(events, search_term_title, search_term_location, search_term_category, search_term_tags=None):
    """
    Search events by title, location, category, and optionally tags, case-insensitive.
    - If only one term is non-empty, search by that field.
    - If multiple terms are non-empty, events must match all specified fields.
    - If all terms are empty, return all events.
    - Category search checks the 'name' field in the category dictionary.
    - Tags search (optional) checks if any tag in search_term_tags matches any tag name.
    Args:
        events: List of event dictionaries
        search_term_title: String to search for in title
        search_term_location: String to search for in location
        search_term_category: String to search for in category name
        search_term_tags: List of strings to search for in tags name (optional)
    Returns:
        List of matching events
    """
    if not search_term_title and not search_term_location and not search_term_category and not (search_term_tags and any(search_term_tags)):
        return events

    search_term_title = search_term_title.lower() if search_term_title else ""
    search_term_location = search_term_location.lower() if search_term_location else ""
    search_term_category = search_term_category.lower() if search_term_category else ""
    search_term_tags = [tag.lower() for tag in search_term_tags] if search_term_tags else []
    results = []

    for event in events:
        event_title = event.get('title', '').lower()
        event_location = event.get('location', '').lower()
        category_dict = event.get('category', {})
        event_category = category_dict.get('name', '').lower() if isinstance(category_dict, dict) else ''
        event_tags = [tag.get('name', '').lower() for tag in event.get('tags', [])]
#        print(f"Debug: Event '{event_title}' category: {event_category}, tags: {event_tags}")

        title_match = (search_term_title in event_title) if search_term_title else True
        location_match = (search_term_location in event_location) if search_term_location else True
        category_match = (search_term_category in event_category) if search_term_category else True
        tags_match = any(any(search_tag in tag for search_tag in search_term_tags) for tag in event_tags) if search_term_tags else True

        
        if title_match and location_match and category_match and tags_match:
            results.append(event)

    return results



def print_event(event):
    print(f"Event: {event.get('title', 'N/A')}")
    print(f"Location: {event.get('location', 'N/A')}")
    print(f"Date: {event.get('eventDate', 'N/A')}")
    print(f"ID: {event.get('eventId', 'N/A')}")
    category_dict = event.get('category', {})
    print(f"Category: {category_dict.get('name', 'N/A') if isinstance(category_dict, dict) else 'N/A'}")
    tags = [tag.get('name', 'N/A') for tag in event.get('tags', [])]
    print(f"Tags: {', '.join(tags) if tags else 'N/A'}")
    print("-" * 50)


def get_calendar_service():
    """
    Authenticate and return a Google Calendar API service object.
    Requires credentials.json and creates token.json after first authentication.
    """
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f"Error initializing Google Calendar service: {error}")
        return None


def create_calendar_if_not_exists(service, calendar_name):
    """
    Create a Google Calendar with the given name if it doesn't exist.
    Returns the calendar ID or None if failed.
    """
    try:
        # Check if calendar exists
        calendar_list = service.calendarList().list().execute()
        for calendar in calendar_list.get('items', []):
            if calendar.get('summary') == calendar_name:
                calendar_id = calendar.get('id')
                calendar_details = service.calendars().get(calendarId=calendar_id).execute()
                calendar_tz = calendar_details.get('timeZone', 'Unknown')
#                print(f"Debug: Found existing calendar '{calendar_name}' (ID: {calendar_id}) with timezone: {calendar_tz}")
                if calendar_tz != 'America/New_York':
                    print(f"Warning: Calendar '{calendar_name}' timezone is {calendar_tz}, expected 'America/New_York'")
                return calendar_id

        # Create new calendar
        calendar_body = {
            'summary': calendar_name,
            'timeZone': 'America/New_York'
        }
        created_calendar = service.calendars().insert(body=calendar_body).execute()
        calendar_id = created_calendar.get('id')
#        print(f"Debug: Created new calendar '{calendar_name}' (ID: {calendar_id}) with timezone: America/New_York")

        return calendar_id
    except HttpError as e:
        print(f"Error creating calendar '{calendar_name}': {e}")
        return None


def get_google_calendar_events(service, calendar_id, start_date, end_date):
    """
    Retrieve event IDs from a Google Calendar within the specified date range.
    Args:
        service: Google Calendar API service object
        calendar_id: Google Calendar ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    Returns:
        Set of event IDs
    """
    try:
#        print(f"Debug: Received start_date: '{start_date}', end_date: '{end_date}'")
        if not start_date or not end_date:
            print(f"Error: Invalid date range - start_date: '{start_date}', end_date: '{end_date}'")
            return set()
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError as e:
            print(f"Error: Invalid date format - start_date: '{start_date}', end_date: '{end_date}', expected 'YYYY-MM-DD': {e}")
            return set()

        # Convert dates to EDT datetime
        edt_tz = pytz.timezone('America/New_York')
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=edt_tz)
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=edt_tz, hour=23, minute=59, second=59)

        # Convert to RFC3339 for API
        time_min = start_dt.isoformat()
        time_max = end_dt.isoformat()

        event_ids = set()
        page_token = None
        while True:
            events_result = service.events().list(
                calendarId=calendar_id,
                singleEvents=True,
                timeMin=time_min,
                timeMax=time_max,
                pageToken=page_token
            ).execute()
            events = events_result.get('items', [])
            for event in events:
                event_id = event.get('id')
                if event_id:
                    event_ids.add(event_id)
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
#        print(f"Fetched {len(event_ids)} event IDs from Google Calendar {calendar_id} for {start_date} to {end_date}")
        return event_ids
    except HttpError as error:
        print(f"Error fetching events from Google Calendar {calendar_id}: {error}")
        return set()


def synchronize_events(service, events, calendar_id, calendar_name, start_date, end_date):
    """
    Synchronize events to the specified Google Calendar by adding new events only.
    No events are deleted, even if not in the current API results.
    Args:
        service: Google Calendar API service object
        events: List of event dictionaries to synchronize
        calendar_id: Google Calendar ID
        calendar_name: Calendar name for logging
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    if not events:
        print(f"No events to synchronize for calendar '{calendar_name}' ({calendar_id})")
        return

    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        print(f"Error: Invalid date format for calendar '{calendar_name}' - start_date: '{start_date}', end_date: '{end_date}': {e}")
        return

    # Get existing event IDs
    existing_event_ids = get_google_calendar_events(service, calendar_id, start_date, end_date)

    for event in events:
        event_id = str(event.get('eventId', ''))
        if not event_id or event_id in existing_event_ids:
#            print(f"Skipping event '{event.get('title', '')}' (ID: {event_id}) - already exists or no ID")
            continue

        try:
            # Get raw API fields
            event_date = event.get('eventDate', '')
            raw_start = event.get('startTime', '')
            raw_end = event.get('endTime', '') or raw_start
#            print(f"Raw API eventDate: {event_date}, startTime: {raw_start}, endTime: {raw_end}")

            # Validate inputs
            if not event_date or not raw_start:
                print(f"Error: Missing eventDate or startTime for event {event_id}")
                continue

            # Parse eventDate for the date
            edt_tz = pytz.timezone('America/New_York')
            try:
                event_dt = datetime.strptime(event_date.strip(), '%Y-%m-%dT%H:%M:%S')
                event_date_only = event_dt.date()
            except ValueError as e:
                print(f"Error parsing eventDate '{event_date}' for event {event_id}: {e}")
                continue

            # Parse startTime and endTime as %I:%M %p
            try:
                start_time = datetime.strptime(raw_start.strip(), '%I:%M %p')
                start_time_edt = edt_tz.localize(datetime.combine(event_date_only, start_time.time()))
                end_time = datetime.strptime(raw_end.strip(), '%I:%M %p')
                end_time_edt = edt_tz.localize(datetime.combine(event_date_only, end_time.time()))
#                print(f"Parsed startTime (EDT): {start_time_edt}, endTime (EDT): {end_time_edt}")
            except ValueError as e:
                print(f"Error parsing startTime/endTime for event {event_id}: {e}")
                continue

            # Create Google Calendar event
            google_event = {
                'id': event_id,
                'summary': event.get('title', 'Untitled Event'),
                'location': event.get('location', ''),
                'description': f"Tags: {', '.join(tag.get('name', '') for tag in event.get('tags', []))}\nCategory: {event.get('category', {}).get('name', '')}",
                'start': {
                    'dateTime': start_time_edt.isoformat(),
                    'timeZone': 'America/New_York'
                },
                'end': {
                    'dateTime': end_time_edt.isoformat(),
                    'timeZone': 'America/New_York'
                }
            }

            try:
                service.events().insert(calendarId=calendar_id, body=google_event).execute()
                print(f"Added event '{event.get('title', '')}' to calendar '{calendar_name}'")
            except HttpError as e:
                print(f"Error adding event '{event.get('title', '')}' to calendar '{calendar_name}': {e}")
        except Exception as e:
            print(f"Unexpected error for event {event_id}: {e}")
            continue

    print(f"No events deleted from calendar '{calendar_name}' ({calendar_id})")
    

def main():
    try:
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.strptime(start_date, "%Y-%m-%d").date() + timedelta(days=14)).strftime("%Y-%m-%d")
        print("start date: ", start_date, ", end date: ", end_date)
    except ValueError as e:
        print(f"Error generating date range: {e}")
        return

    url = f"https://api.thevillages.com/cc3/Api/EventList?type_id=0&date_filter=99&tag_ids=&searchtext=&end_date={end_date}&start_date={start_date}&start_row=0&end_row=20000&query_id=00000000000000000000000000"
# https://api.thevillages.com/cc3/Api/EventList?start_row=0&end_row=1&query_id=00000000000000000000000000

    # CSV file with search terms
    csv_file = "search_terms.csv"

    # Initialize Google Calendar service
    service = get_calendar_service()
    if not service:
        print("Failed to initialize Google Calendar service. Exiting.")
        return

    # Read search terms from CSV file
    search_terms = []
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            expected_fields = {'calendar', 'title', 'location', 'category', 'tags'}
            if not expected_fields.issubset(reader.fieldnames):
                print("CSV file must contain 'calendar', 'title', 'location', 'category', and 'tags' columns.")
                return
            for row in reader:
                # Handle None or missing values with empty strings
                calendar = (row.get('calendar') or '').strip()
                title = (row.get('title') or '').strip()
                location = (row.get('location') or '').strip()
                category = (row.get('category') or '').strip()
                tags = (row.get('tags') or '').strip()
                
                # Parse tags as a quoted, comma-separated string
                tags_list = []
                if tags:
                    if tags.startswith("'") and tags.endswith("'"):
                        tags = tags[1:-1]
                    tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                
                # Add to search_terms
                search_terms.append({
                    'title': title,
                    'location': location,
                    'category': category,
                    'calendar': calendar,
                    'tags': tags_list
                })
    except FileNotFoundError:
        print(f"CSV file '{csv_file}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    if not search_terms:
        print("No search terms found in CSV file.")
        return

    # Fetch events
    events = fetch_events(url)
    if not events:
        print("No events fetched or empty data. Exiting.")
        return

    print(f"Fetched {len(events)} events.")
#    print(f"System timezone: {datetime.now().astimezone().tzinfo}")

    # Assemble events into a dictionary
    calendar_events = {}
    for terms in search_terms:
        search_term_title = terms['title']
        search_term_location = terms['location']
        search_term_category = terms['category']
        search_term_tags = terms.get('tags', [])

        # Describe the search based on non-empty terms
        search_parts = []
        if search_term_title:
            search_parts.append(f"title containing '{search_term_title}'")
        if search_term_location:
            search_parts.append(f"location containing '{search_term_location}'")
        if search_term_category:
            search_parts.append(f"category containing '{search_term_category}'")
        if search_term_tags:
            search_parts.append(f"tags containing {search_term_tags}")

        search_description = ' and '.join(search_parts) if search_parts else "Showing all events"
#        print(f"\n{search_description}:")
        results = search_events(events, search_term_title, search_term_location, search_term_category, search_term_tags)
        
        if results:
#            print(f"Found {len(results)} matching events:")
#            for event in results:
#                print_event(event)
            
            # Add results to calendar_events
            calendar_name = terms['calendar']
            if calendar_name:
                if calendar_name not in calendar_events:
                    calendar_events[calendar_name] = []
                calendar_events[calendar_name].extend(results)
        else:
            print("No events found for the specified search criteria.")

    # Synchronize all events
    for calendar_name, event_list in calendar_events.items():
        calendar_id = create_calendar_if_not_exists(service, calendar_name)
        if not calendar_id:
            print(f"Failed to create or find calendar '{calendar_name}'. Skipping.")
            continue
        # Remove duplicates by eventId
        unique_events = []
        seen_event_ids = set()
        for event in event_list:
            event_id = str(event.get('eventId', ''))
            if event_id and event_id not in seen_event_ids:
                unique_events.append(event)
                seen_event_ids.add(event_id)
        print(f"\nSynchronizing {len(unique_events)} unique events to calendar '{calendar_name}'")
        synchronize_events(service, unique_events, calendar_id, calendar_name, start_date, end_date)
        

if __name__ == "__main__":
    main()
