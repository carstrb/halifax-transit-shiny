from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from shiny import App, render, reactive, ui
from ipyleaflet import Map, basemaps, Marker, Icon, Heatmap
from shinywidgets import render_widget, output_widget
from www.helpers.utilities import generate_styles
from www.helpers.constants import CONTAINER_HEIGHT, DATA_REFRESH_INTERVAL_SECONDS
from www.helpers.feed import fetch_and_process_realtime_data, fetch_and_process_static_data
import ipywidgets as widgets
from www.helpers.utilities import get_stop_info

fetch_and_process_static_data()

# Reactive polling function
@reactive.poll(fetch_and_process_realtime_data, interval_secs=DATA_REFRESH_INTERVAL_SECONDS)  # Updated based on refresh interval
def get_processed_data():
    return fetch_and_process_realtime_data()

def app_ui():
    return ui.page_navbar(
        ui.nav_panel(
            "Delays",
            ui.row(
                ui.column(
                    4,
                    ui.div(
                        ui.output_data_frame("delays"),
                        style="width: 100%; height: 100%;"
                    ),
                ),
                ui.column(8, ui.output_plot("histogram", height=CONTAINER_HEIGHT)),
            ),
        ),
        ui.nav_panel(
            "Route Details",
            ui.row(
                ui.column(
                    12,
                    ui.output_ui("stop_selector"),
                ),
            ),
            ui.row(
                ui.column(
                    6,
                    ui.output_data_frame("stop_details"),
                ),
                ui.column(
                    6,
                    output_widget("map"),
                ),
            ),
        ),
        ui.nav_panel(
            "Heatmap",
            ui.column(
                12,
                output_widget("delays_heatmap"),
            ),
        ),
        title="Halifax Transit Live Metrics",
    )

def server(input, output, session):
    @render.data_frame
    def delays():
        data = get_processed_data()
        median_delays_df = pd.DataFrame(data["median_delays"])
        median_delays_df.rename(
            columns={
                "arrival_difference_minutes": "Median Delay (Minutes)",
                "route_id": "Route ID",
            },
            inplace=True,
        )
        median_delays_df["Median Delay (Minutes)"] = (
            median_delays_df["Median Delay (Minutes)"].round().astype(int)
        )
        median_delays_df = median_delays_df.sort_values(
            by="Median Delay (Minutes)", ascending=False
        )
        return render.DataGrid(
            median_delays_df, 
            width="100%", 
            height="85vh",
        )

    @render.plot(alt="Histogram of Delays (Minutes) by Trip ID")
    def histogram():
        data = get_processed_data()
        fig, ax = plt.subplots()
        ax.hist(
            data["histogram_data"],
            bins=100,
            edgecolor="black",
        )
        ax.set_title("Current Delays (Minutes)")
        ax.set_xlabel("Stop Arrival Difference (Minutes)")
        ax.set_ylabel("Frequency")
        ax.grid(True)

        return fig
    
    @render.ui
    def stop_selector():
        data = fetch_and_process_realtime_data()
        choices = data["stop_names"]
        return ui.input_selectize("selected_stop", "Select a Stop", choices=choices, multiple=False)
    
    @render.data_frame
    def stop_details():
        data = get_processed_data()

        merged_df = pd.DataFrame(data['merged_df'])

        stop_details = get_stop_info(merged_df, input.selected_stop())

        stop_details["arrival_time_minutes_from_now"] = (
            stop_details["arrival_time_minutes_from_now"].round().astype(int)
        )

        stop_details["arrival_difference_minutes"] = (
            stop_details["arrival_difference_minutes"].round().astype(int)
        )

        stop_details = stop_details[stop_details["arrival_time_minutes_from_now"] >= 0]

        stop_details.rename(
            columns={
                "route_id": "Route ID",
                "trip_headsign": "Route Description",
                "arrival_time_minutes_from_now": "ETA (Minutes)",
                "arrival_difference_minutes": "Delay (Minutes)",
                
            },
            inplace=True,
        )

        df_styles = generate_styles(stop_details, "Delay (Minutes)")

        return render.DataGrid(
            stop_details,
            width="100%",
            height="75vh",
            styles=df_styles,
        )
    
    @render_widget
    def map():
        data = fetch_and_process_realtime_data()

        merged_df = pd.DataFrame(data['merged_df'])
        unique_stops_df = merged_df.drop_duplicates(subset=["stop_name", "stop_lat", "stop_lon"])

        selected_stop = input.selected_stop()

        if selected_stop:
            selected_stop_data = unique_stops_df[unique_stops_df["stop_name"] == selected_stop]
            if not selected_stop_data.empty:
                lat = selected_stop_data["stop_lat"].values[0]
                lon = selected_stop_data["stop_lon"].values[0]
            else:
                lat, lon = 44.70, -63.5552  # Default center if the stop is not found
        else:
            lat, lon = 44.70, -63.5552  # Default center if no stop is selected

        # Create the map centered at the selected stop or default location
        m = Map(
            center=[lat, lon],
            zoom=12,
            basemap=basemaps.CartoDB.DarkMatter,
            scroll_wheel_zoom=True,
            zoom_control=False,
            layout=widgets.Layout(width="67vw", height="70vh"),
        )

        # Add a marker only for the selected stop
        if selected_stop and not selected_stop_data.empty:
            icon = Icon(icon_url="img/Canberra_Bus_icon.png", icon_size=[12, 12])
            marker = Marker(location=(lat, lon), title=selected_stop, icon=icon)
            m.add_layer(marker)

        return m
    
    @render_widget
    def delays_heatmap():
        data = get_processed_data()

        delays_heatmap_df = pd.DataFrame(data['delays_heatmap_data'])

        median_arrival_diff_df = (
        delays_heatmap_df.groupby('stop_id')['arrival_difference_minutes']
            .median()
            .reset_index()
        )

        median_arrival_diff_df = pd.merge(
            median_arrival_diff_df,
            delays_heatmap_df[['stop_id', 'stop_lat', 'stop_lon']].drop_duplicates(),
            on='stop_id',
            how='left'
        )

        heatmap_data = median_arrival_diff_df[['stop_lat', 'stop_lon', 'arrival_difference_minutes']]

        center = [median_arrival_diff_df['stop_lat'].mean(), median_arrival_diff_df['stop_lon'].mean()]
        m = Map(
            center=center,
            zoom=12,
            basemap=basemaps.CartoDB.DarkMatter,
            scroll_wheel_zoom=True,
            zoom_control=False,
            layout=widgets.Layout(width="100vw", height="90vh"),
        )

        # Prepare heatmap data for ipyleaflet (lat, lon, intensity)
        heatmap_list = heatmap_data[['stop_lat', 'stop_lon', 'arrival_difference_minutes']].values.tolist()

        # Create the heatmap layer
        heatmap = Heatmap(locations=heatmap_list, radius=15)

        # Add heatmap layer to the map
        m.add_layer(heatmap)

        # Display the map
        return m




www_dir = Path(__file__).parent / "www"
app = App(app_ui(), server, static_assets=www_dir)
