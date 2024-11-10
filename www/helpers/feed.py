import io
import urllib.request
import zipfile
from datetime import datetime

import pandas as pd
from google.transit import gtfs_realtime_pb2

from www.helpers.constants import FEED_URL, STOP_TIMES_PATH, STOPS_PATH, TRIPS_PATH
from www.helpers.utilities import (
    calculate_time_difference,
    convert_to_minutes_from_now,
    get_time_value_in_minutes,
    process_stop_times_date,
    stringify_trips_and_stops,
)
from www.helpers.schemas import real_time_schema, trips_schema, stops_schema, stop_times_schema


def download_and_extract_zip(url, extract_to="."):
    with urllib.request.urlopen(url) as response:
        zip_data = response.read()

    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        z.extractall(path=extract_to)


def get_realtime_transit_feed(pb_url: str):
    with urllib.request.urlopen(pb_url) as response:
        vehicle_data = response.read()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(vehicle_data)

    return feed


def parse_feed(feed):
    data = []
    for entity in feed.entity:
        if entity.HasField("trip_update"):
            trip_update = entity.trip_update
            trip_id = trip_update.trip.trip_id

            for stop_time_update in trip_update.stop_time_update:
                stop_id = stop_time_update.stop_id
                stop_sequence = stop_time_update.stop_sequence
                arrival_time = datetime.fromtimestamp(
                    stop_time_update.arrival.time
                ).strftime("%Y-%m-%d %H:%M:%S")
                departure_time = datetime.fromtimestamp(
                    stop_time_update.departure.time
                ).strftime("%Y-%m-%d %H:%M:%S")

                data.append(
                    {
                        "trip_id": trip_id,
                        "stop_id": stop_id,
                        "stop_sequence": stop_sequence,
                        "arrival_time": arrival_time,
                        "departure_time": departure_time,
                    }
                )

    return pd.DataFrame(data)


def fetch_and_process_data() -> dict:
    pb_url = FEED_URL
    feed = get_realtime_transit_feed(pb_url)
    realtime_data = parse_feed(feed)

    stop_times = pd.read_csv(STOP_TIMES_PATH)
    trips = pd.read_csv(TRIPS_PATH)
    stops = pd.read_csv(STOPS_PATH)

    stop_times["arrival_time"] = stop_times["arrival_time"].apply(
        process_stop_times_date
    )
    stop_times["departure_time"] = stop_times["departure_time"].apply(
        process_stop_times_date
    )

    stringify_trips_and_stops(stop_times)
    stringify_trips_and_stops(realtime_data)
    stringify_trips_and_stops(trips)
    stringify_trips_and_stops(stops)

    real_time_schema.validate(realtime_data)
    stops_schema.validate(stops)
    trips_schema.validate(trips)
    stop_times_schema.validate(stop_times)

    merged_df = pd.merge(
        realtime_data,
        stop_times,
        on=["trip_id", "stop_id", "stop_sequence"],
        how="left",
        suffixes=("", "_expected"),
    )

    merged_df = pd.merge(
        merged_df,
        stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]],
        on="stop_id",
        how="left",
    )

    merged_df = pd.merge(
        merged_df, trips[["trip_id", "trip_headsign"]], on=["trip_id"], how="left"
    )

    datetime_columns = [
        "arrival_time",
        "departure_time",
        "arrival_time_expected",
        "departure_time_expected",
    ]

    for column in datetime_columns:
        merged_df[column] = pd.to_datetime(merged_df[column], errors="coerce")

    merged_df["arrival_time_minutes_from_now"] = convert_to_minutes_from_now(
        merged_df["arrival_time"]
    )

    merged_df["arrival_difference"] = calculate_time_difference(
        merged_df["arrival_time"], merged_df["arrival_time_expected"]
    )
    merged_df["departure_difference"] = calculate_time_difference(
        merged_df["departure_time"], merged_df["departure_time_expected"]
    )

    merged_df["arrival_difference_minutes"] = get_time_value_in_minutes(
        merged_df["arrival_difference"]
    )
    merged_df["departure_difference_minutes"] = get_time_value_in_minutes(
        merged_df["departure_difference"]
    )

    merged_df = pd.merge(
        merged_df, trips[["trip_id", "route_id"]], on="trip_id", how="left"
    )

    merged_df = merged_df[
        (merged_df["arrival_difference_minutes"] <= 1440)
        & (merged_df["arrival_difference_minutes"] >= -1440)
    ]

    median_delays = (
        merged_df.groupby("route_id")["arrival_difference_minutes"]
        .median()
        .reset_index()
    )

    median_delays_dict = median_delays.to_dict(orient="list")

    merged_df_dict = merged_df.to_dict(orient="list")

    histogram_data = merged_df["arrival_difference_minutes"].dropna().tolist()
    delays_heatmap_data = (
        merged_df[["stop_id", "stop_lat", "stop_lon", "arrival_difference_minutes"]]
        .dropna(
            subset=["stop_id", "stop_lat", "stop_lon", "arrival_difference_minutes"]
        )
        .to_dict(orient="list")
    )
    stop_names = sorted(merged_df["stop_name"].dropna().unique().tolist())

    return {
        "merged_df": merged_df_dict,
        "median_delays": median_delays_dict,
        "histogram_data": histogram_data,
        "stop_names": stop_names,
        "delays_heatmap_data": delays_heatmap_data,
    }
