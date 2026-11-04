import os
import pathlib
import signal
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from functools import partial
from glob import glob
from subprocess import CalledProcessError

import polars as pl
import psutil
import xarray as xr
from haversine import Unit, haversine_vector
from simlib.core.buoymodel import BuoyTrajectory
from simlib.core.dataloader import load_ice_data
from simlib.core.icemodel import IceTrajectory
from simlib.tools.ffi_plot import ffi_plot
from simlib.tools.logging import LogLevel, conf_file_logger, conf_interactive_logger
from simlib.tools.utilities import DataExportType
from tqdm import tqdm


def score_plot(
    iceframe: pl.DataFrame, buoyframe: pl.DataFrame, every: str = "7d"
) -> pl.DataFrame:
    """Make a plot of the score between the two dataframes."""
    # TODO: handle time deltas automatically

    start, end = iceframe["time"].min(), iceframe["time"].max()
    buoyframe = (
        buoyframe.filter(pl.col("time").is_between(start, end))
        .group_by_dynamic("time", every=every, start_by="datapoint")
        .agg(
            pl.col("lat").median(),
            pl.col("lon").median(),
        )
        .with_columns(pl.col("time").dt.truncate(every))
        .rename({"lat": "buoylat", "lon": "buoylon"})
    )
    iceframe = iceframe.with_columns(pl.col("time").dt.truncate(every)).rename(
        {"lat": "icelat", "lon": "icelon"}
    )

    merger = buoyframe.join(iceframe, on=["time"], how="inner").drop(["dist", "id"])
    buoylist = list(zip(merger["buoylat"].to_list(), merger["buoylon"].to_list()))
    icelist = list(zip(merger["icelat"].to_list(), merger["icelon"].to_list()))
    return merger.select(
        [
            "time",
            pl.Series(
                "distances", haversine_vector(buoylist, icelist, unit=Unit.KILOMETERS)
            ),
        ]
    )


def get_resource_usage() -> dict:
    parent = psutil.Process(os.getpid())
    procs = [parent] + parent.children(recursive=True)

    cpu_user = sum(p.cpu_times().user for p in procs if p.is_running())
    cpu_sys = sum(p.cpu_times().system for p in procs if p.is_running())
    mem_rss = sum(p.memory_info().rss for p in procs if p.is_running())

    return {"cpu_user_s": cpu_user, "cpu_sys_s": cpu_sys, "mem_rss_mb": mem_rss / 1e6}


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
    # Clean up that dataset by removing known-buggy data. TODO put this in later
    data = pl.read_csv(buoy_path).with_columns(
        pl.col("datetime").str.to_datetime(time_zone="UTC")
    )
    buoy = BuoyTrajectory(
        id=name,
        dataframe=data,
        logger=log,
        loglevel=log_level,
    )
    log.info("Done with loading and preparations. Executing %s...", buoy.filename)
    buoyframe = buoy.export(DataExportType.CSV, write_path / (buoy.filename + ".csv"))
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
    iceframe = ice.export(DataExportType.CSV, write_path / (ice.filename + ".csv"))
    log.info("Done executing %s.", name)
    log.info("Now making distance scores...")
    try:
        # TODO: need to manually edit this every time
        dist = score_plot(iceframe, buoyframe, "7d")
        dist.write_csv(write_path / f"{name}-InterSimDist.csv")
    except Exception as e:  # noqa: BLE001
        log.error("Distance plot failed with error %s", e)
    log.info("Done exporting distance scores.")
    log.info("Making plots for both simulators for %s...", name)
    try:
        ffi_plot("plotter.R", write_path, name, write_path)
        ffi_plot("distance.R", write_path, name, write_path)
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
    # process shell emergency exit
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    # start logging now
    mainlog = conf_interactive_logger(
        "mainprocess", LogLevel.DEBUG if args.verbose else LogLevel.INFO
    )
    init_time = time.perf_counter()
    # in the user's local timezone, not that of the data
    timestamp = datetime.now(tz=(datetime.now().astimezone().tzinfo)).strftime(
        "%Y-%m-%d_%H:%M"
    )

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
    with ProcessPoolExecutor(max_workers=args.nproc) as executor:
        futures = {executor.submit(partial_worker, job) for job in buoylist}
        for _ in tqdm(
            as_completed(futures),
            total=len(buoylist),
            disable=args.verbose,
            colour="green",
        ):
            pass
        stats = get_resource_usage()

    mainlog.info("Simulation complete. Processed %d items.", len(buoylist))

    end_time = time.perf_counter()
    diff = end_time - init_time
    mainlog.info("Elapsed (Wall): %.2fm (%.2fs)", diff / 60, diff)
    # in order: overall CPU use, parallelism efficiency, CPU sys, RAM.
    mainlog.info(
        "Resources: [CPU user: %.2fs (%.2fs) | CPU sys: %.2fs | Mem: %.1f MB]",
        stats["cpu_user_s"],
        stats["cpu_user_s"] / args.nproc,
        stats["cpu_sys_s"],
        stats["mem_rss_mb"],
    )
    sys.exit(0)
