from pathlib import Path
import subprocess
import tempfile

import marimo as mo


# TODO: bundle our script within our application
def r_plot_marimo(input: Path, id: str) -> mo.Html:
    """Takes some args and returns an R plot as bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        # real programmers simply don't have exceptions. skill issue
        subprocess.run(
            [
                "Rscript",
                "plotter.R",
                "--input",
                str(input) + "/",
                "--file",
                id,
                "--output",
                tmp,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # this is a grotesque hack but should work for now
        return mo.image(open((tmp + ("/" + id + ".png")), "rb").read())


def r_plot_raw(script: str, *args: str):
    """Call R immediately and do stuff."""
    subprocess.run(
        ["Rscript", script, *args],
        capture_output=True,
        text=True,
        check=True,
    )


def ffi_plot(input: Path, id: str, output: Path):
    """Makes a plot with R of both simulator's work."""
    # trailing slashes are required in R but not in Python.
    r_plot_raw(
        "plotter.R",
        "--input",
        str(input) + "/",
        "--file",
        id,
        "--output",
        str(output) + "/",
    )
