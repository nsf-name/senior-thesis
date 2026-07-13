import pprint
import time
import pandas as pd
from pathlib import Path

from concurrent.futures import ProcessPoolExecutor
from viztracer import VizTracer
from tqdm.contrib.concurrent import process_map

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
    key, obj = item
    #print(f"processing {key}...")
    for u in obj[0]:
        for v in obj[1]:
            pass
    #print(f"saving {key} to disk...")
    buoyfile = Path(__file__).parent / 'sim-data' / f'{key}_buoy.csv'
    icefile = Path(__file__).parent / 'sim-data' / f'{key}_ice.csv'
    buoypd, icepd = dump_sim(obj)
    with open(buoyfile, 'w') as f:
        buoypd.to_csv(f)
    with open(icefile, 'w') as f:
        icepd.to_csv(f)
    #print(f"done with {key}.")
    return (key, [obj[0].poslist, obj[1].poslist])

if __name__ == "__main__":
    start = time.perf_counter()
    print("SIM: loading, please be patient...")
    buoy_sims = dataloader.load_sim_data()
    with VizTracer(output_file="benchmarking.json") as tracer:
        print("SIM: running simulator in parallel...")
        with ProcessPoolExecutor() as ex:
            results = dict(process_map(simulator_funmap, buoy_sims.items(),
                                       chunksize=1, smoothing=0.1))
            print("SIM: done running simulations in parallel")
        with open("results.txt", "w") as f:
            print("SIM: writing results to .txt file")
            # much faster since we use streaming I/O
            PP = pprint.PrettyPrinter(indent=4, stream=f)
            PP.pprint(results)
    print("SIM: done! probably nothing broke...")
    print(f"Elapsed: {time.perf_counter() - start:.2f}s")

