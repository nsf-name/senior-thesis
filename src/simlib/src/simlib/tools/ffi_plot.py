from pathlib import Path
import subprocess
import tempfile

import marimo as mo
from simlib.core import BuoyTrajectory, IceTrajectory


# TODO: bundle our script within our application
# also, to do plots on objects... that should be our next goal
# take in TWO sims and return a plot for both. nice!
def quickplot(
    ice: IceTrajectory,
    buoy: BuoyTrajectory,
    output: Path | None = None,
    dims: tuple[int, int] | None = None,
):
    """Render a plot to marimo's output."""
    pass


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


def r_ffi(script: str, *args: str):
    """Call an R script and do something."""
    subprocess.run(
        ["Rscript", script, *args],
        capture_output=True,
        text=True,
        check=True,
    )


def ffi_plot(input: Path, id: str, output: Path, dims: tuple[int, int] | None = None):
    """Makes a plot with R of both simulator's work."""
    # trailing slashes are required in R but not in Python.
    r_ffi(
        "plotter.R",
        "--input",
        str(input) + "/",
        "--file",
        id,
        "--output",
        str(output) + "/",
    )
