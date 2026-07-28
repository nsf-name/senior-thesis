from datetime import datetime
from functools import partial
from glob import glob
from multiprocessing import Pool
import multiprocessing
import os
import pathlib
from queue import Queue
import sys
import time
from typing import Any

import polars as pl
from simlib.core.buoymodel import BuoyTrajectory
from simlib.core.dataloader import load_ice_data
from simlib.core.icemodel import IceTrajectory
from simlib.tools.logging import (
    LogLevel,
    conf_interactive_logger,
    conf_manager_logger,
    conf_worker_logger,
)
from simlib.tools.utilities import DataExportType
from tqdm import tqdm
import xarray as xr


def simulator_worker(
    buoy_path: pathlib.Path,
    ice_data: xr.Dataset,
    write_path: pathlib.Path,
    log_queue: Queue[Any],
    log_level: LogLevel,
):
    """Spawns a worker to run each simulator."""

    name = buoy_path.name.rstrip(".csv")
    log = conf_worker_logger(name, log_queue, LogLevel.DEBUG)
    log.info(f"Preparing: {name}")
    data = pl.read_csv(buoy_path).with_columns(pl.col("datetime").str.to_datetime())
    buoy = BuoyTrajectory(
        id=name,
        dataframe=data,
        logger=log,
        loglevel=log_level,
    )
    log.info(f"Done with loading and preparations. Executing {buoy.filename}...")
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
    log.info(f"Done running {ice.filename}. Now exporting...")
    ice.export(DataExportType.CSV, write_path / (ice.filename + ".csv"))
    log.info(f"Done executing {name}")


def create_simpaths(outdir: pathlib.Path, append: str) -> pathlib.Path:
    """Create the path for holding simulator output; user-defined + append."""
    pathname = "run_" + append
    newpath = outdir / pathname
    os.makedirs(newpath)
    return newpath


def run_simulation(args):
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

    output = create_simpaths(args.out_dir, append)
    mainlog.info(f"Saving to: {output}")

    queue = multiprocessing.Manager().Queue()
    listener = conf_manager_logger(queue, output / "workers.log", args.verbose)
    listener.start()

    # assemble the list of buoys to be simulated with functional magic
    buoylist = list(
        map(pathlib.Path, list(sorted(glob(str(args.buoy_data) + "/*.csv"))))
    )

    # invariant: there is at least one buoy.
    if len(buoylist) == 0:
        mainlog.error("Buoy data directory is missing or empty.")
        sys.exit(1)

    mainlog.info("Now reading in simulation data, please wait...")
    icedata = load_ice_data()

    # map can only take one argument, so we need to curry here
    partial_worker = partial(
        simulator_worker,
        write_path=output,
        ice_data=icedata,
        log_queue=queue,
        log_level=LogLevel.INFO,
    )

    mainlog.info("Preparations complete. Started process pool. Executing...")

    # have to use a pool, otherwise macOS complains about too many files open
    with Pool(processes=12) as pool:
        # why not ProcessPoolExecutor()? because this is lazy, and faster
        results = pool.imap_unordered(partial_worker, buoylist, chunksize=1)
        for _ in tqdm(
            results, total=len(buoylist), disable=args.verbose, colour="green"
        ):
            pass

    mainlog.info(f"Simulation complete. Processed {len(buoylist)} items.")

    end_time = time.perf_counter()
    mainlog.info(f"Elapsed: {end_time - init_time:.2f}s")

    # we delay this to allow for queues to drain in the background
    listener.stop()
    sys.exit(0)
