from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from functools import partial
import multiprocessing
import os
import pathlib
import time

from simlib.core import BuoyTrajectory, IceTrajectory, Simulator
from simlib.tools.logging import (
    LogLevel,
    conf_interactive_logger,
    conf_manager_logger,
    conf_worker_logger,
)
from tqdm import tqdm

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
    mainlog = conf_interactive_logger(
        "mainprocess", LogLevel.DEBUG if args.verbose else LogLevel.INFO
    )
    init_time = time.perf_counter()
    mainlog.info("Preparing simulation for runtime...")
    mainlog.debug(f"Working path: {pathlib.Path().resolve()}")
    output = create_simpaths(args.out_dir)
    mainlog.info(f"Saving to: {output}")
    
    queue = multiprocessing.Manager().Queue()
    listener = conf_manager_logger(
        queue, output / "workers.log", args.verbose
    )
    listener.start()
    
    # map can only take one argument, so we need to curry here
    partial_worker = partial(simulator_worker, log_queue=queue)
    mainlog.info("Preparations complete. Starting process pool. Executing...")

    # TODO: replace this example with the real one.
    randomstuff = dict()
    for i in range(0, 100000):
        randomstuff[i] = i * 2
    
    # the default is not fine because I/O overhead is dominated by context switch,
    # so we actually want to keep the pool overscheduled.
    with ProcessPoolExecutor() as ex:
        results = dict(
            tqdm(
                ex.map(
                    partial_worker,
                    randomstuff.items(),
                    chunksize=1
                ),
                total=len(randomstuff),
                disable=args.verbose
            )
        )

    listener.stop()
    mainlog.info(f"Simulation complete. Processed {len(results.keys())} items.")
    
    end_time = time.perf_counter()
    mainlog.info(f"Elapsed: { end_time - init_time:.2f}s")
