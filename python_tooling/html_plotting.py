import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PARAMETERS = {
    "fx": "Focal length fx [px]",
    "fy": "Focal length fy [px]",
    "cx": "Principal point cx [px]",
    "cy": "Principal point cy [px]",
    "xi": "Double Sphere xi",
    "alpha": "Double Sphere alpha",
}


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Create a static Plotly calibration-results webpage."
    )
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_html", type=Path)
    parser.add_argument(
        "--library",
        default="Kalibr",
        help="Calibration library name.",
    )
    return parser.parse_args()


def load_results(path, library):
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
        results["calibration_library"] = library

    if "source_file" not in results.columns:
        results["source_file"] = ""

    for parameter in PARAMETERS:
        results[parameter] = pd.to_numeric(
            results[parameter],
            errors="raise",
        )

    results["result_label"] = (
        results["bag"].astype(str)
        + " · "
        + results["sensor_name"].astype(str)
        + " · "
        + results["calibration_library"].astype(str)
    )

    return results


def make_figure(results):
    figure = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=list(PARAMETERS.values()),
        horizontal_spacing=0.15,
        vertical_spacing=0.12,
    )

    subplot_positions = {
        "fx": (1, 1),
        "fy": (1, 2),
        "cx": (2, 1),
        "cy": (2, 2),
        "xi": (3, 1),
        "alpha": (3, 2),
    }

    libraries = list(results["calibration_library"].drop_duplicates())

    for parameter, title in PARAMETERS.items():
        row, column = subplot_positions[parameter]

        for library_index, library in enumerate(libraries):
            library_results = results[results["calibration_library"] == library]

            custom_data = library_results[
                [
                    "bag",
                    "sensor_name",
                    "camera_model",
                    "calibration_library",
                    "source_file",
                ]
            ]

            figure.add_trace(
                go.Scatter(
                    x=library_results[parameter],
                    y=library_results["result_label"],
                    mode="markers",
                    name=str(library),
                    legendgroup=str(library),
                    showlegend=parameter == "fx",
                    marker={
                        "size": 12,
                        "symbol": library_index,
                        "line": {"width": 1},
                    },
                    customdata=custom_data,
                    hovertemplate=(
                        f"<b>{parameter}: %{{x:.10g}}</b><br>"
                        "Dataset: %{customdata[0]}<br>"
                        "Sensor: %{customdata[1]}<br>"
                        "Camera model: %{customdata[2]}<br>"
                        "Calibration library: %{customdata[3]}<br>"
                        "Source file: %{customdata[4]}"
                        "<extra></extra>"
                    ),
                ),
                row=row,
                col=column,
            )

        figure.update_xaxes(
            title_text=title,
            showgrid=True,
            zeroline=False,
            row=row,
            col=column,
        )

        figure.update_yaxes(
            title_text="Dataset · sensor · library",
            automargin=True,
            row=row,
            col=column,
        )

    dataset_count = results["bag"].nunique()
    sensor_count = results["sensor_name"].nunique()
    library_count = results["calibration_library"].nunique()

    figure.update_layout(
        title={
            "text": (
                "Double Sphere Intrinsic Calibration Results"
                f"<br><sup>{len(results)} results · "
                f"{dataset_count} datasets · "
                f"{sensor_count} sensors · "
                f"{library_count} calibration libraries</sup>"
            ),
            "x": 0.5,
        },
        template="plotly_white",
        height=1200,
        margin={
            "l": 180,
            "r": 50,
            "t": 120,
            "b": 70,
        },
        legend={
            "title": {"text": "Calibration library"},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.04,
            "xanchor": "center",
            "x": 0.5,
        },
        hovermode="closest",
    )

    return figure


def main():
    arguments = parse_arguments()

    results = load_results(
        arguments.input_csv,
        arguments.library,
    )

    figure = make_figure(results)

    arguments.output_html.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure.write_html(
        arguments.output_html,
        full_html=True,
        include_plotlyjs=True,
        config={
            "displaylogo": False,
            "responsive": True,
            "toImageButtonOptions": {
                "format": "svg",
                "filename": "double_sphere_intrinsics",
            },
        },
    )

    print(f"Wrote report to {arguments.output_html}")


if __name__ == "__main__":
    main()
