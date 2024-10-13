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
    limit=1,
    page=1,
    bbox=None,
    datetime_range=None,
):
    """
    Fetches collections from the Maxar API.
    """
    collections = [ "wv01", "wv02"]
    collections_str = ",".join(collections)
    url = f"https://api.maxar.com/discovery/v1/search?collections={collections_str}&bbox={bbox}&datetime={datetime_range}&limit={limit}&page={page}"

    headers = {"Accept": "application/json", "MAXAR-API-KEY": auth_token}

    try:
        response = requests.request("GET",url, headers=headers)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

    return None


def process_geojson(geojson_features):
    # Save the GeoJSON file
    geojson_output = {
        "type": "FeatureCollection",
        "features": geojson_features
    }

    with open(OUTPUT_GEOJSON_FILE, 'w') as geojson_file:
        json.dump(geojson_output, geojson_file, indent=4)

def process_csv(properties_list, geometries_list, feature_ids):
    write_header = not os.path.exists(OUTPUT_CSV_FILE) or os.path.getsize(OUTPUT_CSV_FILE) == 0

    with open(OUTPUT_CSV_FILE, mode='a', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

        list_of_features = ["id"] + list(properties_list[0].keys()) + ['geometry'] if properties_list else []

        if write_header and properties_list:
            csv_writer.writerow(list_of_features)

        for feature_id, properties, geometry in zip(feature_ids, properties_list, geometries_list):
            row = [feature_id] + [sanitize_value(properties.get(key)) for key in list_of_features[1:-1]] + [json.dumps(geometry)]
            csv_writer.writerow(row)

def process_features(features, geojson_features, properties_list, geometries_list, feature_ids):
    feature_records = features.get("features")
    for feature in feature_records:
        feature_id = feature.get('id', '')
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})

        # Collect data for GeoJSON and CSV
        geojson_feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": properties,
            "id": feature_id
        }

        geojson_features.append(geojson_feature)
        properties_list.append(properties)
        geometries_list.append(geometry)
        feature_ids.append(feature_id)

def fetch_and_process_records(auth_token, bbox, start_time, end_time):
    geojson_features = []
    properties_list = []
    geometries_list = []
    feature_ids = []

    page = 1
    while True:
        records = get_maxar_collections(auth_token, bbox=bbox, datetime_range=f"{start_time}/{end_time}", page=page)
        if records is None:
            break
        
        process_features(records, geojson_features, properties_list, geometries_list, feature_ids)

        if not records.get("links") or not any(link.get("rel") == "next" for link in records["links"]):
            break
        
        page += 1

    # Write all collected features to the GeoJSON file
    process_geojson(geojson_features)

    # Write all collected features to the CSV file
    process_csv(properties_list, geometries_list, feature_ids)


def main(START_DATE, END_DATE, OUTPUT_DIR, GEOHASH):
    geohashes = [GEOHASH]
    current_date = datetime.strptime(START_DATE, '%Y-%m-%d')
    end_date = datetime.strptime(END_DATE, '%Y-%m-%d')

    duration = (end_date - current_date).days
    print("-" * columns)
    description = (f"Processing Maxar Catalog \nDate Range: {current_date.date()} to {end_date.date()} Both Inclusive \n"
                   f"lat: {LAT} and lon: {LON} Range: {RANGE} \nOutput Directory: {OUTPUT_DIR}")
    print(description)
    print("-" * columns)
    print("Duration :", duration, "days" if duration > 1 else "day")

    with tqdm(total=duration, desc="", unit="date") as pbar:
        while current_date < end_date:  # Inclusive of end_date
            start_time = current_date.strftime('%Y-%m-%d')
            end_time = (current_date + timedelta(days=2)).strftime('%Y-%m-%d')

            for geohash in geohashes:
                bbox = get_geohash_corners(geohash)
                fetch_and_process_records(AUTH_TOKEN, bbox, start_time, end_time)

            current_date += timedelta(days=1)  # Move to the next day
            pbar.update(1)  # Update progress bar


        pbar.clear()
    tqdm.write("Completed processing Maxar data")


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


    OUTPUT_GEOJSON_FILE = f"{OUTPUT_DIR}/output_maxar.geojson"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    OUTPUT_CSV_FILE = f"{OUTPUT_DIR}/output_maxar.csv"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Check if the directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    main(
        START_DATE,
        END_DATE,
        OUTPUT_DIR,
        GEOHASH
    )
