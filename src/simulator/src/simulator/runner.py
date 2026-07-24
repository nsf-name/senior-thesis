import pathlib
import time
import os
import multiprocessing

from functools import partial
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

from simlib.tools.logging import (
    LogLevel,
    conf_interactive_logger,
    conf_manager_logger,
    conf_worker_logger
)
from simlib.core import IceTrajectory, BuoyTrajectory, Simulator

# TODO: redefine the workers when real workload time
def simulator_worker(
        item: tuple[int, int],
        log_queue: multiprocessing.Queue
    ):
    key, obj = item
    log = conf_worker_logger(str(key),
                             log_queue,
                             LogLevel.DEBUG)
    log.debug(f"hello! my number is: {str(obj)}")
    return (key, obj)

def create_simpaths(outdir: pathlib.Path) -> pathlib.Path:
    """Create the user-specified paths."""
    pathname = "run_" + datetime.now().strftime("%Y-%m-%d_%H:%M")
    newpath = outdir / pathname
    os.makedirs(newpath)
    return newpath

def run_simulation(args):
    mainlog = conf_interactive_logger("main", LogLevel.DEBUG)
    init_time = time.perf_counter()
    mainlog.info("Preparing simulation for runtime...")
    mainlog.info(f"Working path: {pathlib.Path().resolve()}")
    queue = multiprocessing.Manager().Queue()
    output = create_simpaths(args.out_dir)
    mainlog.info(f"Saving to: {output}")
    listener = conf_manager_logger(queue, output / "workers.log")
    listener.start()
    # map can only take one argument, so we need to curry here
    partial_worker = partial(simulator_worker, log_queue=queue)
    mainlog.info("Preparations complete. Executing...")

    # TODO: replace this example with the real one.
    randomstuff = dict()
    for i in range(0, 100000):
        randomstuff[i] = i * 2
    
    # the default is not fine because I/O overhead is dominated by context switch,
    # so we actually want to keep the pool overscheduled.
    with ProcessPoolExecutor() as ex:
        results = dict(
            ex.map(
                partial_worker,
                randomstuff.items(),
                chunksize=1
            )
        )

    listener.stop()
    mainlog.info(f"Simulation complete. Processed {len(results.keys())} items.")
    
    end_time = time.perf_counter()
    mainlog.info(f"Elapsed: { end_time - init_time:.2f}")
