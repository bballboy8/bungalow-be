import requests
import geohash2
from datetime import datetime, timedelta
import csv
import io
import time
import logging
import json
from dateutil import parser
import argparse
import os
from tqdm import tqdm
import math
import shutil
from utils import check_csv_and_rename_output_dir

# Get the terminal size
columns = shutil.get_terminal_size().columns


# Configuration
API_KEY = 'F9FsJJG8UncZGjJ9UcYEqMJgw6TBUpMiNuMCjCtORhB2KV9gcKlD4TiR6ydvLCcLCtBJtZIA8RNha-U9tTVwbA=='
# START_DATE = '2024-01-01'  # Specify the start date in 'YYYY-MM-DD' format
# END_DATE = '2024-08-07'
GEOHASH = 'w'
ITEMS_PER_PAGE = 500
START_PAGE = 1
WORKSPACE = "public-pneo"




# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def geohash_to_bbox(geohash):
    """Convert geohash to bounding box."""
    lat, lon, lat_err, lon_err = geohash2.decode_exactly(geohash)
    lat_min = lat - lat_err
    lat_max = lat + lat_err
    lon_min = lon - lon_err
    lon_max = lon + lon_err
    return lon_min, lat_min, lon_max, lat_max


def calculate_withhold_time(acquisition_date, publication_date):
    """Calculate the withhold time as total hours and human-readable format."""
    acq_date = parser.isoparse(acquisition_date)
    pub_date = parser.isoparse(publication_date)
    delta = pub_date - acq_date
    total_hours = int(delta.total_seconds() / 3600)  # convert to hours
    days = delta.days
    hours = delta.seconds // 3600
    return f"{days} days {hours} hours", total_hours

def latlon_to_geohash(lat, lon, range_km):
    # Map the range to geohash precision
    precision = (
        2 if range_km > 100 else
        4 if range_km > 20 else
        6 if range_km > 5 else
        8 if range_km > 1 else
        10
    )
    return geohash2.encode(lat, lon, precision=precision)


def sanitize_value(value):
    """Ensure values are suitable for GeoJSON by converting them to strings if necessary, except for None."""
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return None  # Keep None as is to maintain distinction in outputs
    return value


def format_datetime(datetime_str):
    """Format datetime string to 'YYYY-MM-DD HH:MM:SS.xx'."""
    try:
        dt = parser.isoparse(datetime_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]  # Truncate to two decimal places
    except (ValueError, TypeError):
        return datetime_str


def format_float(value, precision=2):
    """Format float to a string with the given precision."""
    try:
        return f"{float(value):.{precision}f}"
    except (ValueError, TypeError):
        return None


def search_images(api_key, bbox, start_date, end_date, output_csv_file=None, output_geojson_file=None, lat=None, lon=None, OUTPUT_DIR=None):

    # Set up headers for the authentication request
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    # Set up data for the authentication request
    data = [
        ('apikey', api_key),
        ('grant_type', 'api_key'),
        ('client_id', 'IDP'),
    ]

    # Authenticate and obtain the access token
    auth_response = requests.post(
        'https://authenticate.foundation.api.oneatlas.airbus.com/auth/realms/IDP/protocol/openid-connect/token',
        headers=headers,
        data=data
    )

    if auth_response.status_code == 200:
        access_token = auth_response.json().get('access_token')

        # Set up headers for the search request
        search_headers = {
            'Authorization': f'Bearer {access_token}',
            'Cache-Control': 'no-cache',
        }

        # Prepare CSV output
        csv_output = io.StringIO()
        csv_writer = csv.writer(csv_output, quoting=csv.QUOTE_ALL)

        # Write the header row
        csv_writer.writerow([
            'acquisitionIdentifier', 'geometry', 'acquisitionDate',
            'publicationDate', 'productPlatform', 'sensorType',
            'resolution', 'constellation', 'cloudCover',
            'incidenceAngle', 'azimuthAngle', 'withholdReadable', 'withholdHours'
        ])

        # Prepare a list to hold all GeoJSON features
        geojson_features = []

        # Iterate through each day in the date range
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        date_difference =  (end_date - current_date).days + 1

        print("-" * columns)
        description = f"Processing Airbus Catalog\nDates: {current_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} \n lat: {lat} and lon: {lon} \n Range: {RANGE} \nOutput Directory: {OUTPUT_DIR}"
        print(description)

        print("-" * columns)
        print("Duration :", date_difference, "days" if date_difference > 1 else "day")

        with tqdm(total=date_difference, desc="", unit="day") as pbar:
            while current_date <= end_date:
                total_items = 0
                current_page = START_PAGE

                while True:
                    start_date_str = current_date.strftime('%Y-%m-%dT00:00:00.000Z')
                    end_date_str = current_date.strftime('%Y-%m-%dT23:59:59.999Z')

                    querystring = {
                        "bbox": bbox,
                        "acquisitionDate": f"[{start_date_str},{end_date_str}]",
                        "itemsPerPage": ITEMS_PER_PAGE,
                        "startPage": current_page,
                        "workspace": WORKSPACE
                    }

                    # Make a GET request to the search endpoint
                    search_response = requests.get(
                        'https://search.foundation.api.oneatlas.airbus.com/api/v2/opensearch',
                        headers=search_headers,
                        params=querystring
                    )

                    if search_response.status_code == 200:
                        response_data = search_response.json()

                        # Process each feature and write to CSV and GeoJSON
                        features = response_data.get('features', [])
                        total_items += len(features)

                        for feature in features:
                            properties = feature.get('properties', {})
                            geometry = feature.get('geometry', {})

                            # Format dates and numeric values
                            acquisition_date = format_datetime(properties.get('acquisitionDate', ''))
                            publication_date = format_datetime(properties.get('publicationDate', ''))
                            withhold_readable, withhold_hours = calculate_withhold_time(
                                properties.get('acquisitionDate', ''), properties.get('publicationDate', ''))

                            incidence_angle = format_float(properties.get('incidenceAngle', ''), 2)
                            azimuth_angle = format_float(properties.get('azimuthAngle', ''), 2)

                            # Sanitize values for CSV output
                            csv_writer.writerow([
                                properties.get('acquisitionIdentifier', ''),
                                json.dumps(geometry),
                                acquisition_date,
                                publication_date,
                                properties.get('platform', ''),
                                properties.get('sensorType', ''),
                                properties.get('resolution', ''),
                                properties.get('constellation', ''),
                                properties.get('cloudCover', ''),
                                incidence_angle,
                                azimuth_angle,
                                withhold_readable,
                                withhold_hours
                            ])

                            # Add properties back with formatted angles and withhold
                            geojson_feature = {
                                "type": "Feature",
                                "geometry": geometry,
                                "properties": {
                                    "acquisitionIdentifier": sanitize_value(properties.get('acquisitionIdentifier', '')),
                                    "acquisitionDate": acquisition_date,
                                    "publicationDate": publication_date,
                                    "productPlatform": sanitize_value(properties.get('platform', '')),
                                    "sensorType": sanitize_value(properties.get('sensorType', '')),
                                    "resolution": sanitize_value(properties.get('resolution', '')),
                                    "constellation": sanitize_value(properties.get('constellation', '')),
                                    "cloudCover": sanitize_value(properties.get('cloudCover', '')),
                                    "incidenceAngle": incidence_angle,
                                    "azimuthAngle": azimuth_angle,
                                    "withholdReadable": withhold_readable,
                                    "withholdHours": withhold_hours
                                }
                            }
                            geojson_features.append(geojson_feature)

                        if len(features) < ITEMS_PER_PAGE:
                            break  # No more pages to process

                    else:
                        # logging.error(
                        #     f"Failed to fetch images for {current_date.strftime('%Y-%m-%d')}: {search_response.text}")
                        break  # Exit pagination loop on error

                    current_page += 1
                    time.sleep(1.1)  # Delay for 1.1 seconds between each API call

                current_date += timedelta(days=1)

                pbar.update(1)
                pbar.refresh()

        tqdm.write("Completed Processing Airbus")

        # Write CSV output to a file after all processing is complete
        with open(output_csv_file, 'w', newline='') as csv_file:
            csv_file.write(csv_output.getvalue())

        # Write GeoJSON output to a file after all processing is complete
        geojson_data = {
            "type": "FeatureCollection",
            "features": geojson_features
        }
        with open(output_geojson_file, 'w') as geojson_file:
            json.dump(geojson_data, geojson_file, indent=2)
    else:
        logging.error(f"Failed to authenticate: {auth_response.text}")
        pass


if __name__ == "__main__":
    parser_argument = argparse.ArgumentParser(description='Airbus Catalog API Executor')
    parser_argument.add_argument('--start-date', required=True, help='Start date')
    parser_argument.add_argument('--end-date', required=True, help='End date')
    parser_argument.add_argument('--lat', required=True, type=float, help='Latitude')
    parser_argument.add_argument('--long', required=True, type=float, help='Longitude')
    parser_argument.add_argument('--range', required=True, type=float, help='Range value')
    parser_argument.add_argument('--output-dir', required=True, help='Output directory')
    parser_argument.add_argument('--bbox', required=True, help='Bounding box')

    args = parser_argument.parse_args()
    START_DATE = args.start_date
    END_DATE = args.end_date

    OUTPUT_DIR = args.output_dir + f"/Airbus/{START_DATE}_{END_DATE}"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    RANGE = int(args.range)
    LAT, LON = args.lat, args.long

    BBOX = args.bbox.replace("t", "-")
    print(f"Generated BBOX: {BBOX}")


    OUTPUT_CSV_FILE = f'{OUTPUT_DIR}/output_airbus.csv'
    OUTPUT_GEOJSON_FILE = f'{OUTPUT_DIR}/output_airbus.geojson'
    search_images(API_KEY, BBOX, args.start_date, args.end_date, OUTPUT_CSV_FILE, OUTPUT_GEOJSON_FILE, LAT, LON, OUTPUT_DIR)

    check_csv_and_rename_output_dir(OUTPUT_CSV_FILE, OUTPUT_DIR, START_DATE, END_DATE, args.output_dir, "Airbus")