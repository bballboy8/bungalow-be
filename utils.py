import os
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image, ImageChops
import numpy as np
import rasterio
from rasterio.transform import from_bounds


MAX_THREADS = 10


def check_csv_and_rename_output_dir(
    OUTPUT_CSV_FILE, OUTPUT_DIR, START_DATE, END_DATE, output_base_dir, vendor_name
):
    with open(OUTPUT_CSV_FILE, "r") as f:
        reader = csv.reader(f)
        row_count = sum(1 for _ in reader)

        if row_count < 2:
            print("No data found for the given parameters")
            new_output_dir = os.path.join(
                output_base_dir, f"{vendor_name}/0_{START_DATE}_{END_DATE}"
            )

            if os.path.exists(new_output_dir):
                counter = 1
                while os.path.exists(f"{new_output_dir}_{counter}"):
                    counter += 1
                new_output_dir = f"{new_output_dir}_{counter}"

            os.rename(OUTPUT_DIR, new_output_dir)


def check_folder_content_and_rename_output_dir(
    OUTPUT_THUMBNAIL_FOLDER,
    OUTPUT_DIR,
    START_DATE,
    END_DATE,
    output_base_dir,
    vendor_name,
):
    if len(os.listdir(OUTPUT_THUMBNAIL_FOLDER)) == 0:
        print("No data found for the given parameters")
        new_output_dir = os.path.join(
            output_base_dir, f"{vendor_name}/0_{START_DATE}_{END_DATE}"
        )

        if os.path.exists(new_output_dir):
            counter = 1
            while os.path.exists(f"{new_output_dir}_{counter}"):
                counter += 1
            new_output_dir = f"{new_output_dir}_{counter}"

        os.rename(OUTPUT_DIR, new_output_dir)


def process_geojson(features, OUTPUT_GEOJSON_FOLDER):
    """Saves each feature as a separate GeoJSON file."""
    for feature in features:
        feature_id = feature.get("id", "unknown")
        geojson_data = {
            "type": "FeatureCollection",
            "features": [feature],  # Save each feature individually
        }

        geojson_filename = f"{feature_id}.geojson"
        geojson_path = os.path.join(OUTPUT_GEOJSON_FOLDER, geojson_filename)

        with open(geojson_path, "w") as geojson_file:
            json.dump(geojson_data, geojson_file, indent=4)

def calculate_bbox(geometry):
    """Calculate the bounding box from the GeoJSON polygon coordinates."""
    coordinates = geometry['coordinates'][0]  # Assuming the first polygon
    longitudes = [coord[0] for coord in coordinates]
    latitudes = [coord[1] for coord in coordinates]
    
    min_long = min(longitudes)
    max_long = max(longitudes)
    min_lat = min(latitudes)
    max_lat = max(latitudes)
    
    return min_long, min_lat, max_long, max_lat


def save_image(feature, OUTPUT_THUMBNAILS_FOLDER, OUTPUT_GEOTIFF_FOLDER, AUTH_TOKEN):
    """Downloads an image from the provided URL and saves it to the specified path."""
    try:
        url = feature.get("url")
        bbox = calculate_bbox(feature.get("geometry"))
        save_path = os.path.join(OUTPUT_THUMBNAILS_FOLDER, f"{feature.get('id')}.png")
        headers = {"Authorization": "Bearer " + AUTH_TOKEN}
        response = requests.get(url, headers=headers, stream=True)

        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            georectify_image(save_path, bbox, OUTPUT_GEOTIFF_FOLDER, feature.get("id"))
        else:
            print(f"Error during download: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception occurred while downloading image: {
            feature.get('id')}: {e}"
        )
        return False


def download_thumbnails(
    features, OUTPUT_THUMBNAILS_FOLDER, OUTPUT_GEOTIFF_FOLDER, AUTH_TOKEN
):
    """Download and save thumbnail images for the given features."""

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {
            executor.submit(
                save_image,
                feature,
                OUTPUT_THUMBNAILS_FOLDER,
                OUTPUT_GEOTIFF_FOLDER,
                AUTH_TOKEN,
            ): feature
            for feature in features
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    # print(f"Successfully downloaded thumbnail for feature {feature.get('id')}")
                    pass
                else:
                    # print(f"Failed to download thumbnail for feature {feature.get('id')}")
                    pass
            except Exception as e:
                # print(f"Exception occurred while downloading thumbnail for feature {feature.get('id')}: {e}")
                pass


def remove_black_borders(img):
    """Remove black borders from the image."""
    bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def georectify_image(
    png_path, bbox, geotiffs_folder, image_id, target_resolution=(1500, 1500)
):
    try:
        with Image.open(png_path) as img:
            img = remove_black_borders(img)
            img = img.resize(target_resolution, Image.Resampling.LANCZOS)
            img_array = np.array(img)

        width, height = target_resolution

        left, bottom, right, top = bbox

        transform = from_bounds(left, bottom, right, top, width, height)

        geotiff_name = f"{image_id}.tif"
        geotiff_path = os.path.join(geotiffs_folder, geotiff_name)

        if len(img_array.shape) == 2:
            img_array = np.expand_dims(img_array, axis=-1)
            count = 1
        else:
            count = img_array.shape[2]

        # Write the GeoTIFF file using rasterio
        with rasterio.open(
            geotiff_path,
            "w",
            driver="GTiff",
            height=img_array.shape[0],
            width=img_array.shape[1],
            count=count,
            dtype=img_array.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            for i in range(1, count + 1):
                dst.write(img_array[:, :, i - 1], i)

    except Exception as e:
        pass


def process_geojson(features, OUTPUT_GEOJSON_FOLDER):
    """Saves each feature as a separate GeoJSON file."""
    for feature in features:
        feature_id = feature.get("id", "unknown")
        geojson_data = feature
        geojson_filename = f"{feature_id}.geojson"
        geojson_path = os.path.join(OUTPUT_GEOJSON_FOLDER, geojson_filename)

        with open(geojson_path, "w") as geojson_file:
            json.dump(geojson_data, geojson_file, indent=4)
