 # The Villages Google Calendar Event Sync

 This Python script synchronizes events from The Villages Event API to Google Calendars based on search criteria defined in a CSV file (`search_terms.csv`). It fetches events for the current date to 14 days in the future, filters them by title, location, category, and tags, and synchronizes them to Google Calendars. The script handles local EDT (`America/New_York`) times, parsing dates from `eventDate` (`YYYY-MM-DDTHH:MM:SS`) and times from `startTime`/`endTime` (`%I:%M %p`).

 ## Features

 - Fetches events from The Villages Entertainment API for the current date to 14 days in the future.
 - Filters events based on criteria in `search_terms.csv` (calendar, title, location, category, tags).
 - Groups events by calendar name into a single data structure for efficient synchronization.
 - Adds events to Google Calendars, preventing duplicates using `eventId`.
 - Preserves existing calendar events.
 - Deletes events no longer on the Villages Calendar for those 14 days
 - Handles local EDT times, combining `eventDate` for dates and `startTime`/`endTime` for times.
 - Runs in a Docker container with volume mappings for easy file updates.
 - Minimal logging for debugging (parsing details, no `synced_ids`).

 ## Requirements

 - **Python 3.11+**
 - **Docker** (recommended for containerized execution)
 - **Google Cloud Project** with the Google Calendar API enabled
 - **Dependencies** (listed in `requirements.txt`):
   - `requests`
   - `pytz`
   - `google-auth`
   - `google-auth-oauthlib`
   - `google-api-python-client`
 - A `credentials.json` file from the Google Cloud Console for OAuth 2.0 authentication
 - A `search_terms.csv` file specifying calendar names and search criteria
 - Internet access to fetch events from the API and authenticate with Google

 ## Setup

 ### 1. Clone the Repository
 Clone the project to your local machine and navigate to the project directory:

 ```bash
 git clone https://github.com/your-username/google-calendar-event-sync.git
 cd google-calendar-event-sync
 ```

 ### 2. Install Dependencies
 Choose one of the following options to install the required Python dependencies:

 #### Option 1: Local Installation
 - Ensure Python 3.11 or higher is installed:
   ```bash
   python3 --version
   ```
   If Python is not installed, download it from [python.org](https://www.python.org/downloads/) or use a package manager (e.g., `apt`, `brew`).
 - Create a `requirements.txt` file in the project directory with the following content:
   ```text
   requests
   icalendar
   datetime
   pytz
   google-auth
   google-auth-oauthlib
   google-api-python-client

   ```
 - Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   If `pip` is not found, try:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

 #### Option 2: Docker Installation
 - Ensure Docker is installed:
   ```bash
   docker --version
   ```
   If Docker is not installed, follow instructions at [docker.com](https://docs.docker.com/get-docker/).
 - Create a `requirements.txt` file in the project directory with the content above.
 - Create a `Dockerfile` in the project directory with the following content:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY gcs.py .
   CMD ["python", "gcs.py"]
   ```
 - Build the Docker image:
   ```bash
   docker build -t google-calendar-sync .
   ```

 ### 3. Set Up Google Calendar API
 The script uses the Google Calendar API to manage calendars and events. Follow these steps to set up authentication:

 1. **Create a Google Cloud Project**:
    - Go to the [Google Cloud Console](https://console.cloud.google.com/).
    - Click **New Project**, name it (e.g., `Calendar Sync`), and click **Create**.
    - Select the project from the top dropdown.

 2. **Enable the Google Calendar API**:
    - Navigate to **APIs & Services > Library**.
    - Search for "Google Calendar API" and click **Enable**.

 3. **Create OAuth 2.0 Credentials**:
    - Go to **APIs & Services > Credentials**.
    - Click **Create Credentials > OAuth 2.0 Client IDs**.
    - Select **Desktop app** as the application type, name it (e.g., `Calendar Sync Client`), and click **Create**.
    - Download the credentials JSON file and rename it to `credentials.json`.
    - Place `credentials.json` in the project directory (`google-calendar-event-sync/`).

 4. **Authenticate on First Run**:
    - Run the script (see [Run the Script](#run-the-script) below).
    - The script will open a browser for Google account authentication.
    - Sign in, grant permissions to access Google Calendar, and the script will generate `token.json` in the project directory.
    - **Note**: Mount `token.json` in Docker runs to persist authentication (see [Run the Script](#run-the-script)).

 ### 4. Prepare `search_terms.csv`
 - Create a CSV file named `search_terms.csv` in the project directory.
 - Define calendars and search criteria (see [CSV File Format](#csv-file-format) for details).
 - Example:
   ```csv
   calendar,title,location,category,tags
   all entertainment,science & technology,Bridgeport,Social Clubs,'social clubs'
   Dance Events,,brownwood,Dance,'dance,swing'
   Dance Events,rumba,spanish springs,Dance,'dance,latin'
   Fitness Events,combo swim,colony,Recreation,'recreation,indoor'
   ```

 ### 5. Run the Script
 Choose one of the following options to run the script:

 #### Option 1: Run Locally
 - Ensure `credentials.json` and `search_terms.csv` are in the project directory.
 - Run:
   ```bash
   python gcs.py
   ```

 #### Option 2: Run with Docker
 - Mount `credentials.json`, `search_terms.csv`, and `token.json` using volume mappings to allow easy file updates:
   ```bash
   docker run -it --rm -v $(pwd)/credentials.json:/app/credentials.json -v $(pwd)/search_terms.csv:/app/search_terms.csv -v $(pwd)/token.json:/app/token.json google-calendar-sync
   ```
 - **Note**: Ensure `credentials.json` and `search_terms.csv` exist in the project directory. The `token.json` file is generated on first run and should be mounted to persist authentication. If `token.json` does not exist initially, the script will create it after authentication.

 ## Usage

 1. **Configure `search_terms.csv`**:
    - Define calendars and search criteria (e.g., title, location, category, tags) in `search_terms.csv`.
    - Run the script to fetch events from the API for the current date to 14 days in the future.
    - Events are filtered and added to the specified Google Calendars (e.g., `all entertainment`, `Dance Events`).

 2. **Output**:
    - The script logs:
      - Date range (e.g., `start date: <current_date>, end date: <current_date + 14 days>`).
      - Number of fetched events (e.g., `Fetched 30 events`).
      - Matching events per search term (e.g., `Found 1 matching events: Science & Technology`).
      - Parsing details (e.g., `Parsed startTime (EDT): <current_date> 13:00:00-04:00`).
      - Events added to calendars (e.g., `Added event 'Groove Slayers' to calendar 'all entertainment'`).
      - Confirmation of no deletions (e.g., `No events deleted from calendar 'all entertainment'`).

 3. **Check Google Calendar**:
    - Open [Google Calendar](https://calendar.google.com/) to verify events (e.g., `Groove Slayers` at 5:00 AM EDT on the event date).
    - Ensure calendar timezone is set to `America/New_York`.

 ## CSV File Format

 The `search_terms.csv` file specifies which events to sync to which Google Calendars. It must include the following columns:
 - **calendar**: Name of the Google Calendar (e.g., `all entertainment`). If the calendar doesn’t exist, it’s created.
 - **title**: Filter events by title (partial match, case-insensitive, e.g., `science & technology`). Leave empty to skip.
 - **location**: Filter by location (partial match, e.g., `Bridgeport`). Leave empty to skip.
 - **category**: Filter by category name (partial match, e.g., `Social Clubs`). Leave empty to skip.
 - **tags**: Comma-separated list of tags (e.g., `'social clubs'` or `'dance,swing'`). Leave empty to skip.

 ### Example

 ```csv
 calendar,title,location,category,tags
 Social,science & technology,Bridgeport,Social Clubs,'social clubs'
 Dance Events,,brownwood,Dance,'dance,swing'
 Dance Events,rumba,spanish springs,Dance,'dance,latin'
 Fitness Events,combo swim,colony,Recreation,'recreation,indoor'
 ```

 - Row 1: Adds events with `science & technology` in title, `Bridgeport` in location, `Social Clubs` category, and `social clubs` tag to the `Social` calendar.
 - Row 2: Adds events with `brownwood` location, `Dance` category, and `dance` or `swing` tags to `Dance Events`.
 - Row 3: Adds events with `rumba` in title, `spanish springs` location, `Dance` category, and `dance` or `latin` tags to `Dance Events`.
 - Row 4: Adds events with `combo swim` in title, `colony` location, `Recreation` category, and `recreation` or `indoor` tags to `Fitness Events`.

 ## API Details

 The script fetches events from The Villages API for the current date to 14 days in the future. Each event includes:
 - `eventId`: Unique ID used as the Google Calendar event ID.
 - `title`: Event name (e.g., `Groove Slayers`).
 - `location`: Event location (e.g., `Lake Sumter Landing Market Square`).
 - `eventDate`: Date in `YYYY-MM-DDTHH:MM:SS` (EDT, e.g., `2025-07-01T05:00:00`).
 - `startTime`: Start time in `%I:%M %p` (EDT, e.g., `5:00 AM`).
 - `endTime`: End time in `%I:%M %p` (EDT, e.g., `9:00 PM`).
 - `category`: Category object (e.g., `{"id": 147, "name": "Entertainment"}`).
 - `tags`: List of tag objects (e.g., `[{"id": 181, "name": "Classic Rock"}, ...]`).

 ## Dockerfile

 The `Dockerfile` sets up the Python environment and script:

 ```dockerfile
 FROM python:3.11-slim
 WORKDIR /app
 COPY requirements.txt .
 RUN pip install -r requirements.txt
 COPY gcs.py .
 CMD ["python", "gcs.py"]
 ```

 **Note**: `credentials.json`, `search_terms.csv`, and `token.json` are mounted at runtime using volume mappings (`-v`) to allow easy updates without rebuilding the image.

 ## Troubleshooting

 1. **Authentication Errors**:
    - If `token.json` is invalid or missing:
      ```bash
      rm token.json
      python gcs.py
      ```
    - Ensure `credentials.json` is valid from Google Cloud Console.
    - Add debug to `get_calendar_service`:
      ```python
      except Exception as e:
          print(f"Error authenticating: {e}")
          import traceback
          traceback.print_exc()
          return None
      ```

 2. **Time Parsing Errors**:
    - Check output for parsing errors (e.g., `Error parsing eventDate '...'`).
    - Verify Google Calendar events (e.g., `Groove Slayers` at 5:00 AM EDT on the event date).
    - Ensure calendar timezone:
      - Google Calendar > Settings > Calendar name > Time zone > `America/New_York`.

 3. **Missing Events**:
    - Confirm `"No events deleted ..."`.
    - Check `search_terms.csv` for correct filters.
    - Share:
      - Script output.
      - `search_terms.csv`.
      - Google Calendar contents.
      - API event sample (`print(json.dumps(events[0], indent=2))`).

 4. **Docker Issues**:
    - Verify Docker image:
      ```bash
      docker run google-calendar-sync python -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d'))"
      ```
    - Ensure files are mounted correctly:
      ```bash
      docker run -it --rm -v $(pwd)/credentials.json:/app/credentials.json -v $(pwd)/search_terms.csv:/app/search_terms.csv -v $(pwd)/token.json:/app/token.json bash google-calendar-sync
      ```
    - If files are missing, create them in the project directory before running.

 ## Contributing

 Contributions are welcome! Please:
 1. Fork the repository.
 2. Create a feature branch (`git checkout -b feature/your-feature`).
 3. Commit changes (`git commit -m 'Add your feature'`).
 4. Push to the branch (`git push origin feature/your-feature`).
 5. Open a pull request.

 ## License

 This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

 ## Contact

 For issues or questions, open a GitHub issue or contact [your-email@example.com](mailto:your-email@example.com).
