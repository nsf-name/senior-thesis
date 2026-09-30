from datetime import datetime
from functools import partial
from glob import glob
from multiprocessing import Pool
import os
import pathlib
import sys
import time

import polars as pl
from simlib.core.buoymodel import BuoyTrajectory
from simlib.core.dataloader import load_ice_data
from simlib.core.icemodel import IceTrajectory
from simlib.tools.logging import (
    LogLevel,
    conf_interactive_logger,
    conf_file_logger,
)
from simlib.tools.utilities import DataExportType
from simlib.tools.ffi_plot import ffi_plot
from tqdm import tqdm
import xarray as xr


def simulator_worker(
    buoy_path: pathlib.Path,
    ice_data: xr.Dataset,
    write_path: pathlib.Path,
    log_level: LogLevel,
):
    """Spawns a worker to run each buoy simulator."""

    name = buoy_path.name.rstrip(".csv")
    log = conf_file_logger(name, write_path / (name + ".log"), LogLevel.DEBUG)
    log.info(f"Preparing: {name}")
    data = pl.read_csv(buoy_path).with_columns(pl.col("datetime").str.to_datetime())
    buoy = BuoyTrajectory(
        id=name,
        write_path=write_path,
        dataframe=data,
        logger=log,
        loglevel=log_level,
    )
    log.info(f"Done with loading and preparations. Executing {buoy.filename}...")
    buoy.export(DataExportType.CSV, write_path / (buoy.filename + ".csv"))
    log.info("Done exporting buoy, now executing ice simulator...")
    ice = IceTrajectory(
        id=name,
        write_path=write_path,
        start_day=buoy.timehead,
        end_day=buoy.timetail,
        init_pos=buoy.poshead,
        loglevel=log_level,
        logger=log,
        dataset=ice_data,
    )
    ice.runsim()
    log.info(f"Done running {ice.filename}. Now exporting...")
    ice.export(DataExportType.CSV, write_path / (ice.filename + ".csv"))
    log.info(f"Done executing {name}")
    log.info(f"Making a plot for both simulators for {name}...")
    ffi_plot(write_path, name, write_path)
    log.info(f"Done plotting {name}.")


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
    mainlog.info("Preparing simulation for runtime...")
    mainlog.debug(f"Working path: {pathlib.Path().resolve()}")

    # create our uniquely identifying timestamp for this run.
    append = datetime.now().strftime("%Y-%m-%d_%H:%M")

    # invariant: one run per minute, maximum.
    if os.path.exists(args.out_dir / ("run_" + append)):
        mainlog.error("The output directory already has a run for this timestamp.")
        sys.exit(1)

    # assemble the list of buoys to be simulated with functional magic
    buoylist = list(
        map(pathlib.Path, list(sorted(glob(str(args.buoy_data) + "/*.csv"))))
    )

    # invariant: there is at least one buoy.
    if len(buoylist) == 0:
        mainlog.error("Buoy data directory is missing or empty.")
        sys.exit(1)

    mainlog.info("Now reading in simulation data, please wait...")

    output = create_simpaths(args.out_dir, append)
    mainlog.info(f"Saving to: {output}")

    # TODO: slow in many ways
    icedata = load_ice_data()

    # map can only take one argument, so we need to curry here
    partial_worker = partial(
        simulator_worker,
        write_path=output,
        ice_data=icedata,
        log_level=LogLevel.INFO,
    )

    mainlog.info("Preparations complete. Started process pool. Executing...")

    # have to use a pool, otherwise macOS complains about too many files open
    with Pool(processes=12) as pool:
        # why not ProcessPoolExecutor()? because this is lazy, and faster
        # TODO: we have a much larger pool now...
        # maybe we should scale this for HPC universe. to get better perf.
        results = pool.imap_unordered(partial_worker, buoylist, chunksize=1)
        for _ in tqdm(
            results, total=len(buoylist), disable=args.verbose, colour="green"
        ):
            pass

    mainlog.info(f"Simulation complete. Processed {len(buoylist)} items.")

    end_time = time.perf_counter()
    mainlog.info(f"Elapsed: {end_time - init_time:.2f}s")

    # we delay this to allow for queues to drain in the background
    sys.exit(0)
