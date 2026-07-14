import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PARAMETERS = {
    "fx": ("fx", "px"),
    "fy": ("fy", "px"),
    "cx": ("cx", "px"),
    "cy": ("cy", "px"),
    "xi": ("xi", ""),
    "alpha": ("alpha", ""),
}

LIBRARY_COLORS = [
    "#2563eb",
    "#dc2626",
    "#059669",
    "#7c3aed",
    "#d97706",
    "#0891b2",
]

LIBRARY_SYMBOLS = [
    "circle",
    "diamond",
    "square",
    "triangle-up",
    "cross",
    "x",
]


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Build an HTML webpage containing number-line plots for "
            "camera calibration results."
        )
    )

    parser.add_argument(
        "output_html",
        type=Path,
        help="Path of the generated HTML report.",
    )

    parser.add_argument(
        "--results",
        action="append",
        nargs=2,
        metavar=("LIBRARY", "CSV"),
        required=True,
        help=(
            "Calibration library name and the CSV file containing its parsed "
            "results. Pass this option once for each calibration library."
        ),
    )

    return parser.parse_args()


def load_results(path, library):
    path = Path(path)
    results = pd.read_csv(path)

    required_columns = {
        "bag",
        "sensor_name",
        "camera_model",
        "source_file",
        *PARAMETERS.keys(),
    }

    missing_columns = required_columns - set(results.columns)
    if missing_columns:
        raise ValueError(
            f"{path}: missing required columns: "
            f"{', '.join(sorted(missing_columns))}"
        )

    if results.empty:
        raise ValueError(f"No calibration results found in {path}")

    # NOTE(Jack): The library name is supplied externally because parsed result files do
    # not contain calibration-library metadata.
    results["calibration_library"] = library

    for parameter in PARAMETERS:
        results[parameter] = pd.to_numeric(results[parameter], errors="coerce")

    return results


def load_all_results(result_inputs):
    result_frames = []
    for library, csv_path in result_inputs:
        result_frames.append(load_results(Path(csv_path), library))

    return pd.concat(result_frames, ignore_index=True)


def expanded_range(values, minimum_width=0.0):
    minimum = float(values.min())
    maximum = float(values.max())

    data_width = maximum - minimum
    range_width = max(data_width, minimum_width)

    padding = max(range_width * 0.08, 0.01)
    center = (minimum + maximum) / 2.0

    half_width = range_width / 2.0 + padding

    return center - half_width, center + half_width


def make_library_styles(libraries):
    return {
        library: {
            "color": LIBRARY_COLORS[index % len(LIBRARY_COLORS)],
            "symbol": LIBRARY_SYMBOLS[index % len(LIBRARY_SYMBOLS)],
        }
        for index, library in enumerate(libraries)
    }


def make_sensor_positions(sensors):
    return {sensor: position for position, sensor in enumerate(reversed(sensors))}


def make_figure(results):
    parameter_count = len(PARAMETERS)

    sensors = list(results["sensor_name"].drop_duplicates())
    libraries = list(results["calibration_library"].drop_duplicates())

    if not sensors:
        raise ValueError("No sensors found in the calibration results")

    if not libraries:
        raise ValueError("No calibration libraries were provided")

    sensor_positions = make_sensor_positions(sensors)
    library_styles = make_library_styles(libraries)

    figure = make_subplots(
        rows=parameter_count,
        cols=1,
        subplot_titles=[
            f"{title}{f' ({unit})' if unit else ''}"
            for title, unit in PARAMETERS.values()
        ],
        vertical_spacing=0.055,
    )

    custom_columns = [
        "bag",
        "sensor_name",
        "camera_model",
        "calibration_library",
        "source_file",
    ]

    for row, (parameter, (title, unit)) in enumerate(PARAMETERS.items(), start=1):
        minimum_width = 10.0 if unit == "px" else 0.1
        x_min, x_max = expanded_range(results[parameter], minimum_width)

        # Draw one horizontal number line for every sensor.
        for sensor, y_position in sensor_positions.items():
            figure.add_shape(
                type="line",
                x0=x_min,
                x1=x_max,
                y0=y_position,
                y1=y_position,
                line={
                    "color": "#cbd5e1",
                    "width": 2,
                },
                layer="below",
                row=row,
                col=1,
            )

        # Place every result for the same sensor on the same number line.
        for library_index, library in enumerate(libraries):
            selection = results[results["calibration_library"] == library].copy()

            if selection.empty:
                continue

            selection["sensor_position"] = selection["sensor_name"].map(
                sensor_positions
            )

            style = library_styles[library]

            figure.add_trace(
                go.Scatter(
                    x=selection[parameter],
                    y=selection["sensor_position"],
                    mode="markers",
                    name=str(library),
                    legendgroup=str(library),
                    showlegend=row == 1,
                    marker={
                        "size": 20,
                        "color": style["color"],
                        "symbol": style["symbol"],
                        "opacity": 0.75,
                        "line": {
                            "color": "white",
                            "width": 1,
                        },
                    },
                    customdata=selection[custom_columns].to_numpy(),
                    hovertemplate=(
                        f"<b>{title}: %{{x:.10g}}"
                        f"{f' {unit}' if unit else ''}</b><br>"
                        "Camera: %{customdata[1]}<br>"
                        "Dataset: %{customdata[0]}<br>"
                        "Library: %{customdata[3]}<br>"
                        "Model: %{customdata[2]}<br>"
                        "Source: %{customdata[4]}"
                        "<extra></extra>"
                    ),
                ),
                row=row,
                col=1,
            )

        figure.update_xaxes(
            title_text=f"{parameter}{f' [{unit}]' if unit else ''}",
            range=[x_min, x_max],
            showgrid=True,
            gridcolor="#e2e8f0",
            zeroline=False,
            ticks="outside",
            automargin=True,
            row=row,
            col=1,
        )

        figure.update_yaxes(
            tickmode="array",
            tickvals=list(sensor_positions.values()),
            ticktext=list(sensor_positions.keys()),
            range=[
                -0.55,
                max(sensor_positions.values()) + 0.55,
            ],
            showgrid=False,
            zeroline=False,
            ticks="",
            automargin=True,
            fixedrange=True,
            row=row,
            col=1,
        )

    dataset_count = results["bag"].nunique()
    sensor_count = results["sensor_name"].nunique()
    library_count = results["calibration_library"].nunique()

    figure.update_layout(
        title={
            "text": (
                "Double Sphere camera intrinsics"
                f"<br><sup>{dataset_count} datasets · "
                f"{sensor_count} cameras · "
                f"{library_count} calibration libraries</sup>"
            ),
            "x": 0.02,
            "xanchor": "left",
        },
        template="plotly_white",
        autosize=True,
        height=max(
            1250,
            parameter_count * (170 + 45 * sensor_count),
        ),
        margin={
            "l": 145,
            "r": 35,
            "t": 145,
            "b": 65,
        },
        font={
            "family": "Arial, sans-serif",
            "size": 13,
            "color": "#1f2937",
        },
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        hovermode="closest",
        legend={
            "title": {
                "text": "Calibration library",
            },
            "orientation": "h",
            "x": 1.0,
            "xanchor": "right",
            "y": 1.025,
            "yanchor": "bottom",
            "itemsizing": "constant",
        },
    )

    for annotation in figure.layout.annotations:
        annotation.update(
            x=0,
            xanchor="left",
            font={
                "size": 16,
                "color": "#334155",
            },
        )

    return figure


def write_figure(figure, output_html):
    output_html.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure.write_html(
        output_html,
        full_html=True,
        include_plotlyjs=True,
        config={
            "displaylogo": False,
            "responsive": True,
            "scrollZoom": False,
            "modeBarButtonsToRemove": [
                "lasso2d",
                "select2d",
                "zoom2d",
                "pan2d",
                "zoomIn2d",
                "zoomOut2d",
                "autoScale2d",
            ],
            "toImageButtonOptions": {
                "format": "svg",
                "filename": "double_sphere_intrinsics_number_lines",
            },
        },
    )


def main():
    arguments = parse_arguments()

    results = load_all_results(arguments.results)
    figure = make_figure(results)

    write_figure(
        figure,
        arguments.output_html,
    )

    print(f"Wrote report to {arguments.output_html}")


if __name__ == "__main__":
    main()
