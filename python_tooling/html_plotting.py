import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PARAMETERS = {
    "fx": ("Focal length fx", "px"),
    "fy": ("Focal length fy", "px"),
    "cx": ("Principal point cx", "px"),
    "cy": ("Principal point cy", "px"),
    "xi": ("Double Sphere xi", ""),
    "alpha": ("Double Sphere alpha", ""),
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
        description="Create a static number-line report for camera calibration results."
    )
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_html", type=Path)
    parser.add_argument(
        "--library",
        default="Kalibr",
        help="Library name used when the CSV has no calibration_library column.",
    )
    return parser.parse_args()


def load_results(path, default_library):
    results = pd.read_csv(path)

    required_columns = {
        "bag",
        "sensor_name",
        "camera_model",
        *PARAMETERS.keys(),
    }

    missing_columns = required_columns - set(results.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )

    if results.empty:
        raise ValueError(f"No calibration results found in {path}")

    if "calibration_library" not in results.columns:
        results["calibration_library"] = default_library

    if "source_file" not in results.columns:
        results["source_file"] = ""

    for parameter in PARAMETERS:
        numeric = pd.to_numeric(results[parameter], errors="coerce")
        invalid = numeric.isna() & results[parameter].notna()

        if invalid.any():
            invalid_values = results.loc[invalid, parameter].astype(str).unique()
            raise ValueError(
                f"Column {parameter!r} contains non-numeric values: "
                f"{', '.join(invalid_values)}"
            )

        results[parameter] = numeric

    return results


def expanded_range(values):
    minimum = float(values.min())
    maximum = float(values.max())

    if minimum == maximum:
        padding = max(abs(minimum) * 0.02, 0.01)
    else:
        padding = (maximum - minimum) * 0.08

    return minimum - padding, maximum + padding


def make_figure(results):
    parameter_count = len(PARAMETERS)
    sensors = list(results["sensor_name"].drop_duplicates())
    libraries = list(results["calibration_library"].drop_duplicates())

    sensor_positions = {
        sensor: position for position, sensor in enumerate(reversed(sensors))
    }

    library_styles = {
        library: {
            "color": LIBRARY_COLORS[index % len(LIBRARY_COLORS)],
            "symbol": LIBRARY_SYMBOLS[index % len(LIBRARY_SYMBOLS)],
        }
        for index, library in enumerate(libraries)
    }

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
        x_min, x_max = expanded_range(results[parameter])

        # Draw one horizontal number line for each sensor.
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

        # Put every result for the same camera on the same number line.
        for library_index, library in enumerate(libraries):
            selection = results[results["calibration_library"] == library].copy()

            if selection.empty:
                continue

            # Small deterministic offsets prevent different libraries from
            # completely covering each other while preserving the number-line
            # interpretation.
            offset = (library_index - (len(libraries) - 1) / 2) * 0.10

            selection["sensor_position"] = (
                selection["sensor_name"].map(sensor_positions) + offset
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
                        "size": 11,
                        "color": style["color"],
                        "symbol": style["symbol"],
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
            range=[-0.55, max(sensor_positions.values()) + 0.55],
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
        height=max(1250, parameter_count * (170 + 45 * sensor_count)),
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
            "title": {"text": "Calibration library"},
            "orientation": "h",
            "x": 0.02,
            "xanchor": "left",
            "y": 1.025,
            "yanchor": "bottom",
            "itemsizing": "constant",
        },
    )

    for annotation in figure.layout.annotations:
        annotation.update(
            x=0,
            xanchor="left",
            font={"size": 16, "color": "#334155"},
        )

    return figure


def main():
    arguments = parse_arguments()
    results = load_results(arguments.input_csv, arguments.library)
    figure = make_figure(results)

    arguments.output_html.parent.mkdir(parents=True, exist_ok=True)

    figure.write_html(
        arguments.output_html,
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

    print(f"Wrote report to {arguments.output_html}")


if __name__ == "__main__":
    main()
