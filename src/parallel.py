from concurrent.futures import ProcessPoolExecutor
import pprint
import modules.core.data as dataloader

def simulator_funmap(item: list) -> tuple[str, list[list]]:
    """Apply the simulator loop over a set of items."""
    key, obj = item
    print(f"processing {key}...")
    for u in obj[0]:
        for v in obj[1]:
            pass
    print(f"done with {key}.")
    return (key, [obj[0].poslist, obj[1].poslist])

if __name__ == "__main__":
    print("SIM: loading, please be patient...")
    buoy_sims = dataloader.load_sim_data()
    print("SIM: running simulator in parallel...")
    with ProcessPoolExecutor() as ex:
        results = dict(ex.map(simulator_funmap, buoy_sims.items()))
    print("SIM: done running simulations in parallel")
    with open("results.txt", "w") as f:
        print("SIM: writing results to .txt file")
        # much faster since we use streaming I/O
        PP = pprint.PrettyPrinter(indent=4, stream=f)
        PP.pprint(results)
        print("SIM: done! probably nothing broke...")

