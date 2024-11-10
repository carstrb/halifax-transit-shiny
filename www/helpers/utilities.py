from datetime import datetime, timedelta

import pandas as pd


def get_stop_info(merged_df: pd.DataFrame, stop_name: str) -> pd.DataFrame:
    # Filter the dataframe for the selected stop_name
    stop_df = merged_df[merged_df["stop_name"] == stop_name]

    # Select the relevant columns: route_id, arrival_time, and the difference
    output_df = stop_df[
        [
            "route_id",
            "trip_headsign",
            "arrival_time_minutes_from_now",
            "arrival_difference_minutes",
        ]
    ]

    # Sort by arrival_time for better readability
    output_df = output_df.sort_values("arrival_time_minutes_from_now")

    return output_df


def process_stop_times_date(time_str) -> str:
    # Parse the time string based on how it's presented in stop_times (e.g. 5:49:00)
    time_parts = time_str.split(":")
    hours = int(time_parts[0])
    minutes = int(time_parts[1])
    seconds = int(time_parts[2])

    # Get today's date
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # If hours >= 24, adjust the time and add a day
    if hours >= 24:
        adjusted_time = today + timedelta(
            days=1, hours=(hours - 24), minutes=minutes, seconds=seconds
        )
    else:
        adjusted_time = today + timedelta(hours=hours, minutes=minutes, seconds=seconds)

    return adjusted_time


def convert_to_minutes_from_now(arrival_time_series) -> bool:
    now = datetime.now()
    arrival_times = pd.to_datetime(
        arrival_time_series, unit="ms", errors="coerce"
    )  # Convert to datetime
    differences = (
        arrival_times - now
    ).dt.total_seconds() / 60  # Calculate difference in minutes
    return differences


def stringify_trips_and_stops(feed: pd.DataFrame):
    if "trip_id" in feed.columns:
        feed["trip_id"] = feed["trip_id"].astype(str)

    if "stop_id" in feed.columns:
        feed["stop_id"] = feed["stop_id"].astype(str)


def calculate_time_difference(
    actual_time_column: pd.Series, expected_time_column: pd.Series
) -> pd.Series:
    return actual_time_column - expected_time_column


def get_time_value_in_minutes(time_column: pd.Series) -> pd.Series:
    return time_column.dt.total_seconds() / 60


def generate_styles(df, column_name):
    styles = []

    for index, value in enumerate(df[column_name]):
        if value > 0:
            color = "rgba(255, 0, 0, {opacity})"
        elif value < 0:
            color = "rgba(0, 128, 0, {opacity})"
        else:
            color = "rgba(255, 255, 255, 1.0)"

        if value >= 10:
            opacity = 0.8
        elif value >= 5:
            opacity = 0.5
        else:
            opacity = 0.2

        background_color = color.format(opacity=opacity)

        styles.append(
            {
                "location": "body",
                "rows": [index],
                "cols": [df.columns.get_loc(column_name)],
                "style": {
                    "background-color": background_color,
                },
            }
        )

    return styles

def check_ids_match(real_time_trip_id_series: pd.Series, static_trip_id_series: pd.Series, static_dataset_path: str) -> pd.Series:
    if not real_time_trip_id_series.isin(static_trip_id_series).all():
        raise ValueError(f"IDs from the real-time data do not match the static IDs in '{static_dataset_path}'.")
