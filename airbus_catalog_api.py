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


def search_images(api_key, geohash, start_date, end_date, output_csv_file=None, output_geojson_file=None):
    # Convert geohash to bounding box
    bbox = geohash_to_bbox(geohash)
    bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

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

        date_difference = end_date - current_date

        description = f"Processing Airbus for Dates: {current_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        with tqdm(total=date_difference.days, desc=description, unit="day", position=0, leave=False) as pbar:
            while current_date <= end_date:
                total_items = 0
                current_page = START_PAGE

                while True:
                    start_date_str = current_date.strftime('%Y-%m-%dT00:00:00.000Z')
                    end_date_str = current_date.strftime('%Y-%m-%dT23:59:59.999Z')

                    querystring = {
                        "bbox": bbox_str,
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
        # logging.error(f"Failed to authenticate: {auth_response.text}")
        pass


if __name__ == "__main__":
    parser_argument = argparse.ArgumentParser(description='Airbus Catalog API Executor')
    parser_argument.add_argument('--start-date', required=True, help='Start date')
    parser_argument.add_argument('--end-date', required=True, help='End date')
    parser_argument.add_argument('--lat', required=True, type=float, help='Latitude')
    parser_argument.add_argument('--long', required=True, type=float, help='Longitude')
    parser_argument.add_argument('--range', required=True, type=float, help='Range value')
    parser_argument.add_argument('--output-dir', required=True, help='Output directory')

    args = parser_argument.parse_args()
    START_DATE = args.start_date
    END_DATE = args.end_date

    OUTPUT_DIR = args.output_dir + f"/Airbus/{START_DATE}_{END_DATE}"
    os.makedirs(OUTPUT_DIR, exist_ok=True)


    OUTPUT_CSV_FILE = f'{OUTPUT_DIR}/output_airbus.csv'
    OUTPUT_GEOJSON_FILE = f'{OUTPUT_DIR}/output_airbus.geojson'
    search_images(API_KEY, GEOHASH, args.start_date, args.end_date, OUTPUT_CSV_FILE, OUTPUT_GEOJSON_FILE)