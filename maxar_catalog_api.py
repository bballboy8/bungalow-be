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
import pygeohash as pgh
import math

import shutil

# Get the terminal size
columns = shutil.get_terminal_size().columns

# Configuration
AUTH_TOKEN = ""
MAXAR_BASE_URL = "https://api.maxar.com/discovery/v1"


def latlon_to_geohash(lat, lon, range_km):
    # Map the range to geohash precision
    precision = (
        2
        if range_km > 100
        else 4 if range_km > 20 else 6 if range_km > 5 else 8 if range_km > 1 else 10
    )
    return geohash2.encode(lat, lon, precision=precision)



def get_geohash_corners(geohash: str) -> str:
    center_lat, center_lon = pgh.decode(geohash)
    lat_err, lon_err = pgh.decode_exactly(geohash)[-2:]
    
    top_left = (center_lat + lat_err, center_lon - lon_err)
    top_right = (center_lat + lat_err, center_lon + lon_err)
    bottom_left = (center_lat - lat_err, center_lon - lon_err)
    bottom_right = (center_lat - lat_err, center_lon + lon_err)
    
    lats = [top_left[0], top_right[0], bottom_left[0], bottom_right[0]]
    lons = [top_left[1], top_right[1], bottom_left[1], bottom_right[1]]
    
    xmin = math.ceil(min(lons))
    ymin = math.ceil(min(lats))
    xmax = math.ceil(max(lons))
    ymax = math.ceil(max(lats))
    
    # Format as a bbox string
    return f"{xmin},{ymin},{xmax},{ymax}"


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
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[
            :-4
        ]  # Truncate to two decimal places
    except (ValueError, TypeError):
        return datetime_str


def format_float(value, precision=2):
    """Format float to a string with the given precision."""
    try:
        return f"{float(value):.{precision}f}"
    except (ValueError, TypeError):
        return None


def get_maxar_collections(
    auth_token,
    sortby="datetime DESC",
    limit=5,
    page=1,
    bbox=None,
    intersects=None,
    datetime_range=None,
):
    """
    Fetches collections from the Maxar API.
    """
    collections = [ "wv01", "wv02"]
    collections_str = ",".join(collections)
    url = f"https://api.maxar.com/discovery/v1/search?collections={collections_str}&bbox={bbox}&datetime={datetime_range}"

    headers = {"Accept": "application/json", "MAXAR-API-KEY": auth_token}

    try:
        response = requests.request("GET",url, headers=headers)
        print(response.text)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

    return None


# Function to save features to CSV and GeoJSON
def save_features_to_files(features, output_dir='.'):
    # Prepare CSV output
    OUTPUT_CSV_FILE = f"{output_dir}/output_maxar.csv"
    os.makedirs(output_dir, exist_ok=True)  # Creates the directory if it doesn't exist

    OUTPUT_GEOJSON_FILE = f"{output_dir}/output_maxar.geojson"
    os.makedirs(output_dir, exist_ok=True)  # Creates the directory if it doesn't exist

    # with open(OUTPUT_CSV_FILE, mode='w', newline='') as csv_file:
    #     csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

    #     # Write the header row
    #     csv_writer.writerow([
    #         'id', 'geometry', 'acquired', 'cloud_percent',
    #         'item_type', 'provider', 'published',
    #         'satellite_azimuth', 'satellite_id', 'view_angle',
    #         'pixel_resolution', 'withhold_readable', 'withhold_hours'
    #     ])

    #     # Prepare GeoJSON output
    #     geojson_features = []

        # Write the data rows
    #     for feature in features:
    #         properties = feature.get('properties', {})
    #         geometry = feature.get('geometry', {})
    #         acquisition_date = format_datetime(properties.get('acquired', ''))
    #         publication_date = format_datetime(properties.get('published', ''))
    #         withhold_readable, withhold_hours = calculate_withhold_time(properties.get('acquired', ''),
    #                                                                     properties.get('published', ''))
    #         satellite_azimuth = format_float(properties.get('satellite_azimuth', ''), 2)
    #         view_angle = format_float(properties.get('view_angle', ''), 2)
    #         pixel_resolution = format_float(properties.get('pixel_resolution', ''), 2)

    #         csv_writer.writerow([
    #             feature.get('id', ''),
    #             json.dumps(geometry),  # Geometry as a JSON string
    #             acquisition_date,
    #             properties.get('cloud_percent', ''),
    #             properties.get('item_type', ''),
    #             properties.get('provider', ''),
    #             publication_date,
    #             satellite_azimuth,
    #             properties.get('satellite_id', ''),
    #             view_angle,
    #             pixel_resolution,
    #             withhold_readable,
    #             withhold_hours
    #         ])

    #         # Create a GeoJSON feature
    #         geojson_feature = {
    #             "type": "Feature",
    #             "geometry": geometry,
    #             "properties": {
    #                 "id": feature.get('id', ''),
    #                 "acquired": acquisition_date,
    #                 "cloud_percent": properties.get('cloud_percent', ''),
    #                 "item_type": properties.get('item_type', ''),
    #                 "provider": properties.get('provider', ''),
    #                 "published": publication_date,
    #                 "satellite_azimuth": satellite_azimuth,
    #                 "satellite_id": properties.get('satellite_id', ''),
    #                 "view_angle": view_angle,
    #                 "pixel_resolution": pixel_resolution,
    #                 "withhold_readable": withhold_readable,
    #                 "withhold_hours": withhold_hours
    #             }
    #         }
    #         geojson_features.append(geojson_feature)

    # # Save the GeoJSON file
    # geojson_output = {
    #     "type": "FeatureCollection",
    #     "features": geojson_features
    # }

    # with open(OUTPUT_GEOJSON_FILE, 'w') as geojson_file:
    #     json.dump(geojson_output, geojson_file, indent=4)

    # print(f"CSV and GeoJSON files have been saved:\nCSV: {OUTPUT_CSV_FILE}\nGeoJSON: {OUTPUT_GEOJSON_FILE}")

def process_featuress(features):
    print(features)

        

def main(START_DATE, END_DATE, OUTPUT_DIR, GEOHASH):
    geohashes = [GEOHASH]

    current_date = datetime.strptime(START_DATE, '%Y-%m-%d')
    end_date = datetime.strptime(END_DATE, '%Y-%m-%d')


    duration = (end_date - current_date).days
    all_features = []  # Collect all features for all dates
    print("-"*columns)
    description = f"Processing Maxar Catalog \nDate Range: {current_date.date()} to {end_date.date()} Both Inclusive \n lat: {LAT} and lon: {LON} Range:{RANGE} \nOutput Directory: {OUTPUT_DIR}"
    print(description)
    print("-"*columns)
    print("Duration :", duration, "days" if duration > 1 else "day")

    with tqdm(total=duration, desc="", unit="date") as pbar:

        while current_date < end_date:
            start_time = current_date.strftime('%Y-%m-%d')
            end_time = current_date.strftime('%Y-%m-%d')
            end_time = (current_date + timedelta(days=2)).strftime('%Y-%m-%d')

            for geohash in geohashes:
                bbox = get_geohash_corners(geohash)
                features = get_maxar_collections(
                    AUTH_TOKEN,
                    bbox=bbox,
                    datetime_range=f"{start_time}/{end_time}",
                )
                all_features.extend(features)

            current_date += timedelta(days=1)

            pbar.refresh()
            pbar.update(1)

        pbar.clear()
    tqdm.write("Completed processing Maxar data")

    # Save all collected features to files after processing all days
    # save_features_to_files(all_features, OUTPUT_DIR)


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description='Maxar Catelog API Executor')
    argument_parser.add_argument('--start-date', required=True, help='Start date')
    argument_parser.add_argument('--end-date', required=True, help='End date')
    argument_parser.add_argument('--lat', required=True, type=float, help='Latitude')
    argument_parser.add_argument('--long', required=True, type=float, help='Longitude')
    argument_parser.add_argument('--range', required=True, type=float, help='Range value')
    argument_parser.add_argument('--output-dir', required=True, help='Output directory')

    args = argument_parser.parse_args()
    START_DATE = args.start_date
    END_DATE = args.end_date
    OUTPUT_DIR = args.output_dir + f"/maxar/{START_DATE}_{END_DATE}"

    RANGE = int(args.range)
    LAT, LON = args.lat, args.long
    GEOHASH = latlon_to_geohash(LAT, LON, range_km=RANGE)
    print(f"Generated Geohash: {GEOHASH}")

    # Check if the directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    main(
        START_DATE,
        END_DATE,
        OUTPUT_DIR,
        GEOHASH
    )
