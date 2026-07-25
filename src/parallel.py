import pprint
import time
import argparse
import os
import warnings
from pathlib import Path

import pandas as pd
from concurrent.futures import ProcessPoolExecutor

import simlib.core.dataloader as data
from simlib.core import IceTrajectory, BuoyTrajectory, Simulator
from simlib.tools import * 

def simulator_funmap(item: list) -> tuple[str, list[list]]:
    """Run the simulator for this worker automagically."""
    start = time.perf_counter()
    key, obj = item

    buoysim, icesim = obj
    buoysim.runsim()
    icesim.runsim()
    # TODO: haversine data should be included
    buoyfile = Path(__file__).parent / 'sim-data' / f'{key}_buoy.csv'
    icefile = Path(__file__).parent / 'sim-data' / f'{key}_ice.csv'
    plotfile = Path(__file__).parent / 'sim-data' / f'{key}.png'
    buoypd, icepd = Simulator.dump_sim([buoysim, icesim])
    Simulator.plot_sim(key, plotfile, [buoysim, icesim])
    
    with open(buoyfile, 'w') as f:
        buoypd.to_csv(f)
    with open(icefile, 'w') as f:
        icepd.to_csv(f)

    elapsed = time.perf_counter() - start
    print(f"[{colored(" OK ", "green", ["bold", "underline"])}] {key}: {elapsed:.2f}s")
    return (key, [obj[0].poslist, obj[1].poslist])

if __name__ == "__main__":
    # TODO: this is a bad sign for many reasons
    warnings.filterwarnings('ignore', module='matplotlib')
    warnings.filterwarnings('ignore', module='cartopy')
    console = Console()
    start = time.perf_counter()
    print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Loading, please be patient...")
    buoy_sims = Simulator(buoy_data=data.load_buoy_data(),
                          ice_data=data.load_ice_data())
    print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Running simulators in parallel...")
    # the default is not fine because I/O overhead is dominated by context switch,
    # so we actually want to keep the pool overscheduled.
    with ProcessPoolExecutor(max_workers=os.cpu_count() * 2) as ex:
        results = dict(ex.map(simulator_funmap, buoy_sims.objects.items(), chunksize=1))
        print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Done running simulations in parallel.")
    with open("results.txt", "w") as f:
        print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Writing results to .txt file")
        # much faster since we use streaming I/O
        PP = pprint.PrettyPrinter(indent=4, stream=f)
        PP.pprint(results)
    print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Done writing! All runs complete.")
    print(f"Elapsed: {colored(f"{time.perf_counter() - start:.2f}", "green", ["bold"])}s")

