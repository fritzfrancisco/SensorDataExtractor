#!/usr/bin/env python

import argparse
import datetime
import glob
import os
import subprocess
import sys

import matplotlib.pylab as plt
import numpy as np
import pandas as pd

## Fancy Interactive Plotting
import plotly
import plotly.graph_objects as go
import pytz
import seaborn as sns
from gooey import Gooey, GooeyParser
from plotly.subplots import make_subplots

# plotly.offline.init_notebook_mode(connected=True)

@Gooey
def main():
    #################### ARGUMENT PARSER ####################
    # parser = argparse.ArgumentParser()
    parser = GooeyParser(description="Sensor Data Logger")

    # Input files from sensors
    parser.add_argument(
        "-temp",
        "--temp_light",
        help="Logger output for tempueratur and light (.xlsx)",
        default="/home/fritz/Documents/0_FieldWork/0_Buston_Rueger_PNG/4_Analysis/0_MorganAbiotics/CombinedAbiotics/merged_light_temp-20241204-124521.xlsx",
        widget="FileChooser",
        required=True,
    )
    parser.add_argument(
        "-ph",
        "--ph",
        help="Logger output for pH (.xlsx)",
        default="/home/fritz/Documents/0_FieldWork/0_Buston_Rueger_PNG/4_Analysis/0_MorganAbiotics/CombinedAbiotics/merged_pH-20241204-124524.xlsx",
        widget="FileChooser",
        required=True,
    )
    parser.add_argument(
        "-co",
        "--conductivity",
        help="Logger output for conductivity (.csv)",
        default="/home/fritz/Documents/0_FieldWork/0_Buston_Rueger_PNG/4_Analysis/0_MorganAbiotics/CombinedAbiotics/merged_conductivity-20241204-124813.csv",
        widget="FileChooser",
        required=True,
    )
    parser.add_argument(
        "-do",
        "--dissolved_oxygen",
        help="Logger output for dissolved oxygen (.txt)",
        default="/home/fritz/Documents/0_FieldWork/0_Buston_Rueger_PNG/4_Analysis/0_MorganAbiotics/CombinedAbiotics/merged_dissolved_oxygen-20241204-124530.txt",
        widget="FileChooser",
        required=True,
    )
    parser.add_argument(
        "-cu",
        "--current",
        help="Logger output for current meter (.csv)",
        default="/home/fritz/Documents/0_FieldWork/0_Buston_Rueger_PNG/4_Analysis/0_MorganAbiotics/CombinedAbiotics/merged_current-20241204-124526.csv",
        widget="FileChooser",
        required=True,
    )
    parser.add_argument(
        "-ds",
        "--datasheet",
        help='Datasheet containing dates and times at which to extract sensor data. (Column Format: "Date": "2024-07-11"; "Abiotics in": "15:08:00")(.xlsx)',
        default="/home/fritz/Documents/0_FieldWork/0_Buston_Rueger_PNG/4_Analysis/0_MorganAbiotics/TranslocationExperiment_DataEntry_20241103_ALL.xlsx",
        widget="FileChooser",
        required=False,
    )
    parser.add_argument(
        "-s",
        "--sampling_frequency",
        widget="IntegerField",
        help="Sampling frequency (Hz)",
        default=60,
        required=False,
    )
    parser.add_argument(
        "-w",
        "--measurement_window",
        widget="IntegerField",
        help="Window over which to check for values (Minutes)",
        default=5,
        required=False,
    )
    parser.add_argument(
        "-v",
        "--visualize",
        help='Visualize logger output as plot. Press "q" to close plot window',
        action="store_true",
        default=False,
        required=False,
    )
    parser.add_argument(
        "-m",
        "--merged",
        help='Select if using already merged sensor datasheets across multiple measurement instances',
        action="store_true",
        default=False,
        required=False,
    )
    parser.add_argument(
        "-o",
        "--output",
        widget="DirChooser",
        help="Output directory for timestamp data",
        default=".",
        required=False,
    )
    args = parser.parse_args()
    # print (sys.argv[1:])

    #################### SETUP ####################

    # Define timezones
    png_time = pytz.timezone(
        "Pacific/Port_Moresby"
    )  # Port Moresby is in PNG Time (GMT+10)
    utc = pytz.utc

    #################### READ DATA ####################

    templight = pd.read_excel(args.temp_light)
    ph = pd.read_excel(args.ph)
    if args.merged == True:
        conductivity = pd.read_csv(args.conductivity)
        do = pd.read_csv(args.dissolved_oxygen,
        sep=",")
    else:
        conductivity = pd.read_csv(args.conductivity, skiprows=1)
        do = pd.read_fwf(
            args.dissolved_oxygen,
            sep=",",
            header=None,
            skiprows=9,  # Skip header of file with unused rows
            names=[
                "Unix Timestamp (s)",
                "UTC_Date",
                "UTC Time",
                "Greenwich Mean Date",
                "Greenwich Mean Time",
                "Battery (V)",
                "Temperature (°C)",
                "Dissolved Oxygen (mg/l)",
                "Dissolved Oxygen Saturation (%)",
                "Q",
            ],
        ).replace(",", "", regex=True)
    current = pd.read_csv(args.current)
    # timestamps = pd.read_csv(args.timestamps, header=None).to_numpy()
    # datasheet = pd.read_excel(args.datasheet)
    datasheet = pd.ExcelFile(args.datasheet)
    sheets = datasheet.sheet_names  # see all sheet names
    sheets = np.array(sheets)[~np.isin(sheets, ['Anemone_Measurements', 'Fish_Measurements'])]
    datasheet = pd.concat(
        [pd.read_excel(args.datasheet, sheet_name=sheet) for sheet in sheets], axis=0
    ).reset_index()
    datasheet.loc[datasheet["Abiotics in"] == 0, "Abiotics in"] = (
        np.nan
    )  ## Convert 0 to NAN
    datasheet.loc[datasheet["Abiotics in"] == datetime.time(0, 0), "Abiotics in"] = (
        np.nan
    )
    mask = pd.notna(
        datasheet["Abiotics in"]
    )  # Filter to only include values at which sensors where deployed
    datasheet = datasheet[mask]
    query_timestamp = (
        datasheet["Date"].astype(str)
        + " "
        + datasheet["Abiotics in"].astype(str)
        + "+10:00"
    )
    datasheet["Timestamp"] = pd.to_datetime(query_timestamp, errors="coerce")
    selected_rows = datasheet[pd.isnull(datasheet["Timestamp"]) == False].copy()
    selected_rows["PNG Timestamp"] = selected_rows["Timestamp"].dt.tz_convert(
        png_time
    )  # PNG Time
    timestamps = selected_rows["PNG Timestamp"]

    #################### STANDARDIZE TIMEZONES & DATE TIME FORMAT ####################

    templight_timestamp = pd.to_datetime(
        templight["Date-Time (Papua New Guinea Standard Time)"]
    )  # PNG Time
    templight_timestamp = templight_timestamp.dt.tz_localize(png_time).dt.tz_convert(
        png_time
    )  # PNG Time
    templight["PNG Timestamp"] = templight_timestamp
    templight["Light (lux) "] = pd.to_numeric(templight["Light (lux) "])

    current_timestamp = pd.to_datetime(current["ISO 8601 Time"])
    current_timestamp = current_timestamp.dt.tz_localize(png_time).dt.tz_convert(
        png_time
    )  # PNG Time
    current["PNG Timestamp"] = current_timestamp

    ph_timestamp = pd.to_datetime(
        ph["Date-Time (Papua New Guinea Standard Time)"]
    )  # PNG Time
    ph_timestamp = ph_timestamp.dt.tz_localize(png_time).dt.tz_convert(
        png_time
    )  # PNG Time
    ph["PNG Timestamp"] = ph_timestamp
    ph["pH (pH) "] = pd.to_numeric(ph["pH (pH) "])

    conductivity_timestamp = pd.to_datetime(conductivity["Date Time, GMT+10:00"], format='%m/%d/%y %I:%M:%S %p')
    conductivity_timestamp = conductivity_timestamp.dt.tz_localize(
        png_time
    ).dt.tz_convert(
        png_time
    )  # PNG Time
    conductivity["PNG Timestamp"] = conductivity_timestamp

    do_timestamp = pd.to_datetime(do["Unix Timestamp (s)"].to_numpy().astype(int), unit="s")  # UTC
    do_timestamp = do_timestamp.tz_localize(utc).tz_convert(png_time)  # PNG Time
    do["PNG Timestamp"] = do_timestamp
    do["Dissolved Oxygen (mg/l)"] = pd.to_numeric(do["Dissolved Oxygen (mg/l)"])

    #################### EXTRACT TIMESTAMP DATA ####################

    if args.datasheet is not None:
        output = []
        sampling_times = []
        for time in timestamps:
            time = pd.to_datetime(time)
            sampling_times.append(time)
            prev_time = None
            print("Starting time: ", time)

            timestamp_rows = selected_rows.iloc[
                np.where(selected_rows["PNG Timestamp"] == time)[0], :
            ].reset_index()

            for i in np.arange(int(args.measurement_window)):
                if prev_time == None:
                    time = time
                else:
                    time = prev_time + pd.Timedelta(
                        seconds=int(args.sampling_frequency)
                    )
                prev_time = time
                print("Measurement time: ", prev_time)

                for index, row in timestamp_rows.iterrows():
                    out = []
                    # sensor_names = ["Temperature", "pH", "Conductivity", "DO", "Current"]
                    for i, sensor_data in enumerate(
                        [templight, ph, conductivity, do, current]
                    ):
                        sensor_value = (
                            sensor_data.iloc[
                                np.where(sensor_data["PNG Timestamp"] == time)[0], :
                            ]
                            .copy()
                            .reset_index()
                        )
                        if i == 0:
                            sensor_value["Tag"] = row["Tag"]
                            sensor_value["Reef"] = row["Reef"]
                            sensor_value["Depth"] = row["Depth"]
                            sensor_value["PNG Timestamp"] = time
                        else:
                            ## Rename timestamp column
                            # sensor_value.rename(columns={"PNG Timestamp": "PNG Timestamp {}".format(sensor_names[i])}, inplace=True)
                            sensor_value = sensor_value.drop("PNG Timestamp", axis=1)
                        out.append(sensor_value.reset_index(drop=True))
                    out = pd.concat(out, axis=1)
                    output.append(out)
        output = pd.concat(output, axis=0)

        output = output.drop(
            [
                "index",
                "#",
                "Date-Time (Papua New Guinea Standard Time)",
                "Date Time, GMT+10:00",
                "ISO 8601 Time",
                "End Of File (LGR S/N: 21785664)",
                "Coupler Attached (LGR S/N: 21785664)",
                "Host Connected (LGR S/N: 21785664)",
                # "Stopped (LGR S/N: 21785664)",
                "Coupler Detached (LGR S/N: 21785664)",
            ],
            axis=1,
        )

        ## Switch column order [Reef, Tag, Date, PNG Timestamp ]
        for column in ["Depth", "PNG Timestamp", "Tag", "Reef"]:
            selected_column = output.pop(column) 
            output.insert(0, column, selected_column) 

        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = "{}/sensor_output_{}.csv".format(args.output, timestamp)
        output.to_csv(filename, index=False)

    #################### PLOT SIGNALS ####################

    if args.visualize == True:
        try:
            ylim_values = []
            fig = make_subplots(
                rows=6,
                cols=1,
                shared_xaxes=True)

            # Light
            templight = templight.sort_values(by='PNG Timestamp')
            fig.add_trace(
                go.Scatter(
                    x=templight["PNG Timestamp"],
                    y=templight["Light (lux) "],
                    mode="lines",
                    name="Light",
                ),
                row=1,
                col=1,
            )
            ylim_values.append(
                [templight["Light (lux) "].min(), templight["Light (lux) "].max()]
            )

            # Temperature
            fig.add_trace(
                go.Scatter(
                    x=templight["PNG Timestamp"],
                    y=templight["Temperature (°C) "],
                    mode="lines",
                    name="Temperature",
                ),
                row=2,
                col=1,
            )
            ylim_values.append(
                [
                    templight["Temperature (°C) "].min(),
                    templight["Temperature (°C) "].max(),
                ]
            )

            # Current
            current = current.sort_values(by='PNG Timestamp')
            fig.add_trace(
                go.Scatter(
                    x=current["PNG Timestamp"],
                    y=current["Speed (cm/s)"],
                    mode="lines",
                    name="Current Speed",
                ),
                row=3,
                col=1,
            )
            ylim_values.append(
                [
                    np.min(current["Speed (cm/s)"]),
                    np.max(current["Speed (cm/s)"]),
                ]
            )

            # pH
            ph = ph.sort_values(by='PNG Timestamp')
            fig.add_trace(
                go.Scatter(
                    x=ph["PNG Timestamp"], y=ph["pH (pH) "], mode="lines", name="pH"
                ),
                row=4,
                col=1,
            )
            ylim_values.append([ph["pH (pH) "].min(), ph["pH (pH) "].max()])

            # Conductivity
            conductivity = conductivity.sort_values(by='PNG Timestamp')
            fig.add_trace(
                go.Scatter(
                    x=conductivity["PNG Timestamp"],
                    y=conductivity[
                        "Low Range, μS/cm (LGR S/N: 21785664, SEN S/N: 21785664)"
                    ],
                    mode="lines",
                    name="Low Range",
                ),
                row=5,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=conductivity["PNG Timestamp"],
                    y=conductivity[
                        "High Range, μS/cm (LGR S/N: 21785664, SEN S/N: 21785664)"
                    ],
                    mode="lines",
                    name="High Range",
                ),
                row=5,
                col=1,
            )

            ylim_values.append(
                [
                    np.min(
                        [
                            conductivity[
                                "High Range, μS/cm (LGR S/N: 21785664, SEN S/N: 21785664)"
                            ].min(),
                            conductivity[
                                "Low Range, μS/cm (LGR S/N: 21785664, SEN S/N: 21785664)"
                            ].min(),
                        ]
                    ),
                    np.max(
                        [
                            conductivity[
                                "High Range, μS/cm (LGR S/N: 21785664, SEN S/N: 21785664)"
                            ].max(),
                            conductivity[
                                "Low Range, μS/cm (LGR S/N: 21785664, SEN S/N: 21785664)"
                            ].max(),
                        ]
                    ),
                ]
            )

            # Dissolved Oxygen
            do = do.sort_values(by='PNG Timestamp')
            fig.add_trace(
                go.Scatter(
                    x=do["PNG Timestamp"],
                    y=do["Dissolved Oxygen (mg/l)"],
                    mode="lines",
                    name="DO",
                ),
                row=6,
                col=1,
            )
            ylim_values.append(
                [
                    do["Dissolved Oxygen (mg/l)"].min(),
                    do["Dissolved Oxygen (mg/l)"].max(),
                ]
            )

            # Add vertical lines to each subplot
            for time in sampling_times:
                label = ""
                for t in output[output["PNG Timestamp"] == time]["Tag"].to_numpy():
                    label += t + " "
                for r in np.arange(1, 7):
                    fig.add_trace(
                        go.Scatter(
                            x=[time, time],
                            y=[ylim_values[r - 1][0], ylim_values[r - 1][1]],
                            mode="lines",
                            line_width=1,
                            line=dict(color="#080061"),
                            opacity=0.2,
                            showlegend=False,
                            name="",
                            hovertext=label,
                            zorder=-1,
                        ),
                        row=r,
                        col=1,
                    )

            fig.update_layout(
                title_text="Sensor Data",
                autosize=True,
                # width=1200,
                # height=700,
            )

            fig.show()

        except:
            fig, ax = plt.subplots(5, 1, figsize=(20, 10), sharex=True)

            # Temperature & Light 
            sns.lineplot(
                data=templight.sort_values(by='PNG Timestamp'),
                x="PNG Timestamp",
                y="Light (lux) ",
                ax=ax[0],
            )

            # Current
            sns.lineplot(
                data=current.sort_values(by='PNG Timestamp'), x="PNG Timestamp", y="Speed (cm/s)", label="Current Speed", ax=ax[1]
            )
        
            # pH
            sns.lineplot(data=ph.sort_values(by='PNG Timestamp'), x="PNG Timestamp", y="pH (pH) ", ax=ax[2])

            # Conductivity
            sns.lineplot(
                data=conductivity.sort_values(by='PNG Timestamp'),
                x="PNG Timestamp",
                y="Low Range, μS/cm (LGR S/N: 21785664, SEN S/N: 21785664)",
                ax=ax[3],
                label="Low Range",
            )
            sns.lineplot(
                data=conductivity.sort_values(by='PNG Timestamp'),
                x="PNG Timestamp",
                y="High Range, μS/cm (LGR S/N: 21785664, SEN S/N: 21785664)",
                ax=ax[3],
                label="High Range",
            )

            # Dissolved Oxygen
            sns.lineplot(
                data=do, x="PNG Timestamp", y="Dissolved Oxygen (mg/l)", ax=ax[4]
            )

            ax[0].set_title("Light")
            ax[1].set_title("Current")
            ax[1].set_ylabel("Acceleration (g)")
            ax[2].set_title("pH")
            ax[3].set_title("Conductivity")
            ax[3].set_ylabel("Conductivity (μS/cm)")
            ax[4].set_title("DO")

            # for a in ax:
            #     a.set_xlim(pd.Timestamp("2024-07-08"), pd.Timestamp("2024-07-10"))

            plt.show()


if __name__ == "__main__":
    main()
