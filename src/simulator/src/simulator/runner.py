from datetime import datetime
from functools import partial
from glob import glob
from multiprocessing import Pool
from subprocess import CalledProcessError
import os
import pathlib
import sys
import time

import polars as pl
from tqdm import tqdm
import xarray as xr

from simlib.core.buoymodel import BuoyTrajectory
from simlib.core.dataloader import load_ice_data
from simlib.core.icemodel import IceTrajectory
from simlib.tools.ffi_plot import ffi_plot
from simlib.tools.logging import LogLevel, conf_file_logger, conf_interactive_logger
from simlib.tools.utilities import DataExportType


def simulator_worker(
    buoy_path: pathlib.Path,
    ice_data: xr.Dataset,
    write_path: pathlib.Path,
    log_level: LogLevel,
):
    """Spawns a worker to run each buoy simulator."""

    name = buoy_path.name.rstrip(".csv")
    log = conf_file_logger(name, write_path / (name + ".log"), LogLevel.DEBUG)
    log.info("Preparing: %s", name)
    data = pl.read_csv(buoy_path).with_columns(pl.col("datetime").str.to_datetime())
    buoy = BuoyTrajectory(
        id=name,
        dataframe=data,
        logger=log,
        loglevel=log_level,
    )
    log.info("Done with loading and preparations. Executing %s...", buoy.filename)
    buoy.export(DataExportType.CSV, write_path / (buoy.filename + ".csv"))
    log.info("Done exporting buoy, now executing ice simulator...")
    ice = IceTrajectory(
        id=name,
        start_day=buoy.timehead,
        end_day=buoy.timetail,
        init_pos=buoy.poshead,
        loglevel=log_level,
        logger=log,
        dataset=ice_data,
    )
    ice.runsim()
    log.info("Done running %s. Now exporting...", ice.filename)
    ice.export(DataExportType.CSV, write_path / (ice.filename + ".csv"))
    log.info("Done executing %s.", name)
    log.info("Making a plot for both simulators for %s...", name)
    try:
        ffi_plot(write_path, name, write_path)
    except CalledProcessError as err:
        log.error("R FFI plot failed with error %s", err)
    log.info("Done plotting %s.", name)


def create_simpaths(outdir: pathlib.Path, append: str) -> pathlib.Path:
    """Create the path for holding simulator output; user-defined + append."""
    pathname = "run_" + append
    newpath = outdir / pathname
    os.makedirs(newpath)
    return newpath


def run_simulation(args):
    """The main event loop for all code."""
    mainlog = conf_interactive_logger(
        "mainprocess", LogLevel.DEBUG if args.verbose else LogLevel.INFO
    )
    init_time = time.perf_counter()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M")

    mainlog.info("Preparing simulation for runtime...")
    mainlog.debug("Working path: %s.", pathlib.Path().cwd())
    if os.path.exists(args.out_dir / ("run_" + timestamp)):
        mainlog.error("The output directory already has a run for this timestamp.")
        sys.exit(1)

    # assemble the list of buoys to be simulated with functional magic
    buoylist = list(map(pathlib.Path, sorted(glob(str(args.buoy_data) + "/*.csv"))))
    if len(buoylist) == 0:
        mainlog.error("Buoy data directory is missing or empty.")
        sys.exit(1)

    mainlog.info("Now reading in simulation data, please wait...")
    icedata = load_ice_data(args.ice_data)

    output = create_simpaths(args.out_dir, timestamp)
    mainlog.info("Saving to: %s", output)

    # curry because map() can't take two args
    partial_worker = partial(
        simulator_worker,
        write_path=output,
        ice_data=icedata,
        log_level=LogLevel.INFO,
    )

    mainlog.info("Preparations complete. Started process pool. Executing...")
    with Pool(processes=args.nproc) as pool:
        # why not ProcessPoolExecutor()? because this is lazy, not eager.
        results = pool.imap_unordered(partial_worker, buoylist, chunksize=1)
        for _ in tqdm(
            results, total=len(buoylist), disable=args.verbose, colour="green"
        ):
            pass

    mainlog.info("Simulation complete. Processed %d items.", len(buoylist))

    end_time = time.perf_counter()
    diff = end_time - init_time
    mainlog.info("Elapsed: %.2fsm (%.2fss)", diff / 60, diff)
    sys.exit(0)
