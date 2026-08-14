import argparse
from pathlib import Path

import dominate
import pandas as pd
import plotly.graph_objects as go
from dominate.tags import body, button, div, head, meta, script, style, title
from dominate.util import raw
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
        description=("Build an HTML webpage containing number-line plots for " "camera calibration results.")
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
        raise ValueError(f"{path}: missing required columns: " f"{', '.join(sorted(missing_columns))}")

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


def make_figure(results, title):
    sensors = list(results["sensor_name"].drop_duplicates())
    libraries = list(results["calibration_library"].drop_duplicates())

    if not sensors:
        raise ValueError("No sensors found in the calibration results")

    if not libraries:
        raise ValueError("No calibration libraries were provided")

    sensor_positions = {sensor: position for position, sensor in enumerate(reversed(sensors))}
    library_styles = {
        library: {
            "color": LIBRARY_COLORS[index % len(LIBRARY_COLORS)],
            "symbol": LIBRARY_SYMBOLS[index % len(LIBRARY_SYMBOLS)],
        }
        for index, library in enumerate(libraries)
    }

    figure = make_subplots(
        rows=len(PARAMETERS),
        cols=1,
        subplot_titles=[f"{title}" for title, _ in PARAMETERS.values()],
        vertical_spacing=0.055,
    )

    custom_columns = [
        "bag",
        "camera_model",
    ]

    for row, (parameter, (parameter_title, unit)) in enumerate(PARAMETERS.items(), start=1):
        minimum_width = 20.0 if unit == "px" else 0.2
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
        for library in libraries:
            selection = results[results["calibration_library"] == library].copy()

            if selection.empty:
                continue

            selection["sensor_position"] = selection["sensor_name"].map(sensor_positions)

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
                        "Dataset: %{customdata[0]}<br>"
                        "Model: %{customdata[1]}<br>"
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
                title + f"<br><sup>{dataset_count} datasets · "
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
            len(PARAMETERS) * (170 + 45 * sensor_count),
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
        annotation.update(x=0, xanchor="left", font={"size": 16, "color": "#334155"})

    return figure


def write_figures(intrinsics_figure, extrinsics_figure, output_html):
    output_html.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "displaylogo": False,
        "responsive": True,
        "scrollZoom": False,
    }

    intrinsics_html = intrinsics_figure.to_html(
        full_html=False,
        include_plotlyjs=True,
        config=config,
    )

    extrinsics_html = extrinsics_figure.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=config,
    )

    document = dominate.document(title="Calibration Benchmarking")

    with document.head:
        meta(charset="utf-8")
        meta(name="viewport", content="width=device-width, initial-scale=1")

        style("""
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #ffffff;
                color: #1f2937;
            }

            .tabs {
                display: flex;
                gap: 8px;
                padding: 16px 24px;
                border-bottom: 1px solid #e2e8f0;
            }

            .tab-button {
                border: none;
                background: transparent;
                padding: 10px 18px;
                cursor: pointer;
                font-size: 15px;
                color: #64748b;
            }

            .tab-button.active {
                font-weight: bold;
                color: #1f2937;
                border-bottom: 2px solid #1f2937;
            }

            .tab-content {
                display: none;
            }

            .tab-content.active {
                display: block;
            }
            """)

    with document.body:
        with div(cls="tabs"):
            button(
                "Intrinsics",
                cls="tab-button active",
                onclick="showTab('intrinsics', this)",
            )
            button(
                "Extrinsics",
                cls="tab-button",
                onclick="showTab('extrinsics', this)",
            )

        with div(id="intrinsics", cls="tab-content active"):
            raw(intrinsics_html)

        with div(id="extrinsics", cls="tab-content"):
            raw(extrinsics_html)

        script(raw("""
                function showTab(id, button) {
                    document.querySelectorAll(".tab-content").forEach(element => {
                        element.classList.remove("active");
                    });

                    document.querySelectorAll(".tab-button").forEach(element => {
                        element.classList.remove("active");
                    });

                    const content = document.getElementById(id);

                    content.classList.add("active");
                    button.classList.add("active");

                    content.querySelectorAll(".plotly-graph-div").forEach(plot => {
                        Plotly.Plots.resize(plot);
                    });
                }
                """))

    output_html.write_text(document.render(), encoding="utf-8")


def main():
    arguments = parse_arguments()

    results = load_all_results(arguments.results)

    intrinsics_figure = make_figure(
        results,
        "Double Sphere camera intrinsics",
    )

    # TODO(Jack): Replace with actual extrinsic results once parsing is implemented.
    extrinsics_figure = make_figure(
        results,
        "Camera-IMU extrinsics",
    )

    write_figures(
        intrinsics_figure,
        extrinsics_figure,
        arguments.output_html,
    )

    print(f"Wrote report to {arguments.output_html}")


if __name__ == "__main__":
    main()
