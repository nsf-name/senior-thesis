import subprocess
import tempfile
from pathlib import Path

import marimo as mo


def r_plot_marimo(inpath: Path, inid: str) -> mo.Html:
    """Takes some args and returns an R plot as bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        # real programmers simply don't have exceptions. skill issue
        subprocess.run(
            [
                "Rscript",
                "plotter.R",
                "--input",
                str(inpath) + "/",
                "--file",
                inid,
                "--output",
                tmp,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # this is a grotesque hack but should work for now
        return mo.image(open((tmp + ("/" + str(id) + ".png")), "rb").read())


def r_ffi(script: str, *args: str):
    """Call an R script and do something."""
    subprocess.run(
        ["Rscript", script, *args],
        capture_output=True,
        text=True,
        check=True,
    )


def ffi_plot(
    function: str,
    inpath: Path,
    inid: str,
    output: Path,
    dims: tuple[int, int] | None = None,
):
    """Makes a plot with R of some data."""
    # trailing slashes are required in R but not in Python.
    if dims is not None:
        r_ffi(
            function,
            "--input",
            str(inpath) + "/",
            "--file",
            inid,
            "--output",
            str(output) + "/",
            "--height",
            str(dims[0]),
            "--width",
            str(dims[1]),
        )
    else:
        r_ffi(
            function,
            "--input",
            str(inpath) + "/",
            "--file",
            inid,
            "--output",
            str(output) + "/",
        )
