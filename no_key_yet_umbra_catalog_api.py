import requests

# Set your access token and date variables
access_token = '<access_token>'

start_date = '2023-10-20'  # Start date in yyyy-mm-dd format
end_date = '2023-10-21'    # End date in yyyy-mm-dd format


def query_api(access_token, start_date, end_date):
    url = "https://api.canopy.umbra.space/archive/search"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    datetime_range = f"{start_date}T00:00:00Z/{end_date}T00:00:00Z"
    payload = {
        "limit": 10,
        "datetime": datetime_range,
        "bbox": [
            -119.8792576517811,
            34.318681740683246,
            -119.54554123766826,
            34.503965775376656
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


# Call the function and print the results
result = query_api(access_token, start_date, end_date)
if result:
    print("API Response:")
    print(result)
else:
    print("Failed to retrieve data.")
