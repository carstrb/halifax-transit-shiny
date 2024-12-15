import unittest
from datetime import datetime, timedelta

import pandas as pd

from www.helpers.utilities import (
    calculate_time_difference,
    convert_to_minutes_from_now,
    get_stop_info,
    process_stop_times_date,
    stringify_trips_and_stops,
    get_time_value_in_minutes,
    generate_styles,
)


class TestUtilities(unittest.TestCase):
    def test_get_stop_info(self):
        sample_data = pd.DataFrame(
            {
                "stop_name": ["Stop A", "Stop B", "Stop A", "Stop C"],
                "route_id": [1, 2, 3, 4],
                "trip_headsign": ["Route 1", "Route 2", "Route 3", "Route 4"],
                "arrival_time_minutes_from_now": [15, 5, 10, 20],
                "arrival_difference_minutes": [1, -2, 0, 3],
            }
        )

        result = get_stop_info(sample_data, "Stop A")
        expected_data = {
            "route_id": [3, 1],
            "trip_headsign": ["Route 3", "Route 1"],
            "arrival_time_minutes_from_now": [10, 15],
            "arrival_difference_minutes": [0, 1],
        }
        expected_df = pd.DataFrame(expected_data)

        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected_df)

        # Check get_stop_info returns nothing when given an invalid stop
        result = get_stop_info(sample_data, "Nonexistent Stop")
        self.assertTrue(result.empty)

        # Check that get_stop_info returns no data when given empty dataframe
        empty_df = pd.DataFrame(
            columns=[
                "stop_name",
                "route_id",
                "trip_headsign",
                "arrival_time_minutes_from_now",
                "arrival_difference_minutes",
            ]
        )

        result = get_stop_info(empty_df, "Stop A")
        self.assertTrue(result.empty)

    def test_process_stop_times_date(self):
        # Assuming time_str is '05:49:00'
        result = process_stop_times_date("05:49:00")
        expected_time = datetime.now().replace(
            hour=5, minute=49, second=0, microsecond=0
        )
        self.assertEqual(result, expected_time)

        # Assuming time_str is '25:30:00' which should roll over to the next day at 1:30 AM
        result = process_stop_times_date("25:30:00")

        expected_time = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1, hours=1, minutes=30)
        self.assertEqual(result, expected_time)

        # Midnight case '00:00:00'
        result = process_stop_times_date("00:00:00")
        expected_time = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.assertEqual(result, expected_time)

        # Case where time_str is '24:00:00', which should roll over to the next day at midnight
        result = process_stop_times_date("24:00:00")
        expected_time = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        self.assertEqual(result, expected_time)

    def test_convert_to_minutes_from_now(self):
        now = datetime.now()
        future_time = pd.Series((now + timedelta(minutes=10)))
        result = convert_to_minutes_from_now(future_time)

        self.assertAlmostEqual(
            result.iloc[0], 10, delta=0.1
        )  # Allow a small delta due to execution time

        # Create a series with a timestamp 10 minutes in the past
        past_time = pd.Series((now - timedelta(minutes=10)))
        result = convert_to_minutes_from_now(past_time)

        self.assertAlmostEqual(result.iloc[0], -10, delta=0.1)

        # Create a series with the current time
        current_time = pd.Series(now)
        result = convert_to_minutes_from_now(current_time)

        self.assertAlmostEqual(result.iloc[0], 0, delta=0.1)

        # Create a series with an invalid time (e.g., NaN)
        invalid_time = pd.Series([None])
        result = convert_to_minutes_from_now(invalid_time)

        self.assertTrue(pd.isna(result.iloc[0]))  # Check if the result is NaN

        # Create a series with mixed valid and invalid timestamps
        data = [
            (now + timedelta(minutes=15)),  # 15 minutes in the future
            None,  # Invalid time
            (now - timedelta(minutes=5)),  # 5 minutes in the past
        ]
        mixed_times = pd.Series(data)
        result = convert_to_minutes_from_now(mixed_times)

        self.assertAlmostEqual(result.iloc[0], 15, delta=0.1)
        self.assertTrue(pd.isna(result.iloc[1]))
        self.assertAlmostEqual(result.iloc[2], -5, delta=0.1)

    def test_stringify_trips_and_stops(self):
        data = {
            "trip_id": [101, 102, 103],
            "stop_id": [201, 202, 203],
            "other_column": [1, 2, 3],
        }
        df = pd.DataFrame(data)

        stringify_trips_and_stops(df)

        self.assertEqual(df["trip_id"].iloc[0], "101")
        self.assertEqual(df["stop_id"].iloc[0], "201")

        self.assertEqual(df["other_column"].dtype, int)

    def test_calculate_time_difference(self):
        data = {
            "actual_time_column": [
                datetime(2024, 1, 1, 12, 0, 0),
                datetime(2024, 1, 1, 18, 0, 0),
                datetime(2024, 1, 1, 12, 5, 0),
            ],
            "expected_time_column": [
                datetime(2024, 1, 1, 12, 0, 0),
                datetime(2024, 1, 1, 17, 59, 0),
                datetime(2024, 1, 1, 12, 6, 0),
            ],
        }

        df = pd.DataFrame(data)

        expected_result = pd.Series(
            [timedelta(minutes=0), timedelta(minutes=1), timedelta(minutes=-1)]
        )

        result = calculate_time_difference(
            df["actual_time_column"], df["expected_time_column"]
        )

        for res, exp in zip(result, expected_result):
            self.assertEqual(res, exp)

    def test_get_time_value_in_minutes(self):
        data = {
            "time_difference": [
                timedelta(minutes=60),
                timedelta(minutes=20),
                timedelta(minutes=5),
            ]
        }

        df = pd.DataFrame(data)

        result = get_time_value_in_minutes(df["time_difference"])

        expected_result = pd.Series([60, 20, 5])

        for res, exp in zip(result, expected_result):
            self.assertEqual(res, exp)

    def test_generate_styles(self):
        data = {
            "time_difference": [12, -3, 0, 7, 2],
        }
        df = pd.DataFrame(data)

        styles = generate_styles(df, "time_difference")

        expected_styles = [
            {
                "location": "body",
                "rows": [0],
                "cols": [0],
                "style": {"background-color": "rgba(255, 0, 0, 0.8)"},
            },
            {
                "location": "body",
                "rows": [1],
                "cols": [0],
                "style": {"background-color": "rgba(0, 128, 0, 0.2)"},
            },
            {
                "location": "body",
                "rows": [2],
                "cols": [0],
                "style": {"background-color": "rgba(255, 255, 255, 1.0)"},
            },
            {
                "location": "body",
                "rows": [3],
                "cols": [0],
                "style": {"background-color": "rgba(255, 0, 0, 0.5)"},
            },
            {
                "location": "body",
                "rows": [4],
                "cols": [0],
                "style": {"background-color": "rgba(255, 0, 0, 0.2)"},
            },
        ]

        self.assertEqual(styles, expected_styles)
