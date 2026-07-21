import pprint
import time
import os
from pathlib import Path

import pandas as pd
from termcolor import colored
from rich.console import Console
from concurrent.futures import ProcessPoolExecutor

import modules.core.data as dataloader

def dump_sim(buoy_sim: list[BuoyTrajectory, IceTrajectory]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Dump a buoy simulation into a DataFrame; first is simulated, second is real."""
    buoy_poslist, buoy_timelist = buoy_sim[0].poslist, buoy_sim[0].timlist 
    ice_poslist, ice_timelist = buoy_sim[1].poslist, buoy_sim[1].timlist 
    buoy_zipper = [(*pos, t) for pos, t in zip(buoy_poslist, buoy_timelist)]
    ice_zipper = [(*pos, t) for pos, t in zip(ice_poslist, ice_timelist)]
    return (pd.DataFrame(buoy_zipper, columns=["lat", "lon", "time"]),
            pd.DataFrame(ice_zipper, columns=["lat", "lon", "time"]))

def simulator_funmap(item: list) -> tuple[str, list[list]]:
    """Apply the simulator loop over a set of items."""
    start = time.perf_counter()
    key, obj = item
    #print(f"processing {key}...")
    for u in obj[0]:
        for v in obj[1]:
            pass
    #print(f"saving {key} to disk...")
    buoyfile = Path(__file__).parent / 'sim-data' / f'{key}_buoy.csv'
    icefile = Path(__file__).parent / 'sim-data' / f'{key}_ice.csv'
    buoypd, icepd = dump_sim(obj)
    # TODO: this is so slow that I'm tempted to use polars for just this
    with open(buoyfile, 'w') as f:
        buoypd.to_csv(f)
    with open(icefile, 'w') as f:
        icepd.to_csv(f)
    #print(f"done with {key}.")
    elapsed = time.perf_counter() - start
    print(f"[{colored(" OK ", "green", ["bold", "underline"])}] {key}: {elapsed:.2f}s")
    return (key, [obj[0].poslist, obj[1].poslist])

if __name__ == "__main__":
    console = Console()
    start = time.perf_counter()
    print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Loading, please be patient...")
    buoy_sims = dataloader.load_sim_data()
    print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Running simulator in parallel...")
    # the default is not fine because I/O overhead is dominated by context switch,
    # so we actually want to keep the pool overscheduled.
    with ProcessPoolExecutor(max_workers=os.cpu_count() * 2) as ex:
        results = dict(ex.map(simulator_funmap, buoy_sims.items(), chunksize=1))
        print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Done running simulations in parallel.")
    with open("results.txt", "w") as f:
        print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Writing results to .txt file")
        # much faster since we use streaming I/O
        PP = pprint.PrettyPrinter(indent=4, stream=f)
        PP.pprint(results)
    print(f"[{colored(" SIM ", "light_grey", ["bold", "underline"])}]: Done writing! All runs complete.")
    print(f"Elapsed: {colored(f"{time.perf_counter() - start:.2f}", "green", ["bold"])}s")

