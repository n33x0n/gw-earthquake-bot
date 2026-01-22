# GW Earthquake Bot

Automated earthquake monitoring and alerting system that tracks USGS earthquake data, generates interactive Datawrapper maps, and sends email notifications.

## Features

- **Real-time Monitoring**: Polls USGS earthquake feed every 5 minutes
- **Magnitude Filtering**: Alerts only for earthquakes > 5.0M (configurable)
- **Interactive Maps**: Automatically creates Datawrapper locator maps with markers
- **Email Alerts**: Sends notifications with map links, embed codes, and raw data
- **Polish Localization**: Translates directional prefixes in location names
- **History Tracking**: Prevents duplicate alerts for the same event

## Requirements

- Python 3.7+
- `requests` library

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/gw-earthquake-bot.git
   cd gw-earthquake-bot
   ```

2. Install dependencies:
   ```bash
   pip install requests
   ```

3. Configure the script by editing the configuration section in `earthquake_bot.py`:
   - `DW_API_KEY`: Your Datawrapper API key
   - `EMAIL_SENDER`: Gmail address for sending alerts
   - `EMAIL_PASSWORD`: Gmail App Password (not regular password)
   - `EMAIL_RECIPIENT`: Primary recipient email
   - `EMAIL_CC`: CC recipient email

## Usage

### Production Mode
```bash
python3 earthquake_bot.py
```
Runs continuously, checking for new earthquakes every 5 minutes.

### Test Mode
```bash
python3 earthquake_bot.py --test
```
Processes the latest earthquake regardless of magnitude or history, then exits.

## Configuration

| Variable | Description |
|----------|-------------|
| `DW_API_KEY` | Datawrapper API token with chart creation permissions |
| `EMAIL_SENDER` | Gmail address used to send alerts |
| `EMAIL_PASSWORD` | Gmail App Password |
| `EMAIL_RECIPIENT` | Primary email recipient |
| `EMAIL_CC` | Carbon copy recipient |
| `CHECK_INTERVAL_SECONDS` | Polling interval (default: 300) |
| `HISTORY_FILE` | JSON file to store processed event IDs |

## API Dependencies

- **USGS Earthquake API**: https://earthquake.usgs.gov/earthquakes/feed/
- **Datawrapper API**: https://developer.datawrapper.de/

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Tomasz Lebioda**  
Email: tlebioda@gmail.com
