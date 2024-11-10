from pandera import Column, DataFrameSchema
from datetime import datetime

real_time_schema = DataFrameSchema(
    {
        "trip_id": Column(str),
        "stop_id": Column(str),
        "stop_sequence": Column(int),
        "arrival_time": Column(datetime),
        "departure_time": Column(datetime),
    },
    strict=True,
    coerce=True,
)

stops_schema = DataFrameSchema(
    {
        'stop_id': Column(str), 
        'stop_code': Column(int),
        'stop_name': Column(str), 
        'stop_desc': Column(str, nullable=True), 
        'stop_lat': Column(float),
        'stop_lon': Column(float), 
        'zone_id': Column(str, nullable=True), 
        'stop_url': Column(str, nullable=True), 
        'location_type': Column(str, nullable=True,),
        'parent_station': Column(str, nullable=True),
        'stop_timezone': Column(str, nullable=True),
        'wheelchair_boarding': Column(int, nullable=True),
    },
    strict=True,
    coerce=True,
)

stop_times_schema = DataFrameSchema(
    {
        'trip_id': Column(str), 
        'arrival_time': Column(datetime),
        'departure_time': Column(datetime), 
        'stop_id': Column(str), 
        'stop_sequence': Column(int),
        'stop_headsign': Column(str, nullable=True), 
        'pickup_type': Column(int), 
        'drop_off_type': Column(str, nullable=True), 
        'shape_dist_traveled': Column(float, nullable=True),
        'timepoint': Column(int),
    },
    strict=True,
    coerce=True,
)

trips_schema = DataFrameSchema(
    {
        'route_id': Column(str), 
        'service_id': Column(str),
        'trip_id': Column(str), 
        'trip_headsign': Column(str), 
        'trip_short_name': Column(str, nullable=True),
        'direction_id': Column(int), 
        'block_id': Column(int), 
        'shape_id': Column(int), 
        'wheelchair_accessible': Column(int),
        'bikes_allowed': Column(int),
    },
    strict=True,
    coerce=True,
)
