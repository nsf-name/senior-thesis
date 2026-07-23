import argparse
from dataclasses import dataclass
import pathlib

@dataclass()
class SimulatorPrefs:
    out_path: pathlib.Path

def run_simulation(args):
    print("""
    They say science is done on the shoulders of giants.
    Not here; at Aperture we do all our science from scratch. No hand-holding. 
    """)
    if args.verbose:
        print("And we're also very verbose.")
    print(args.directory)

def main():    
    parser = argparse.ArgumentParser(
        prog="simulator",
        description="Simulate sea ice buoys",
        epilog="Copyright Nathaniel Flores 2026, MIT license."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run",
        description="Simulate sea ice buoys",
        epilog="This can be very computationally intensive.")
    run_p.add_argument("-v", "--verbose",
                       help="enable debug messages",
                       action="store_true")
    run_p.add_argument("-d", "--directory",
                       help="output to a specific directory",
                       action="store", type=pathlib.Path)
    run_p.set_defaults(func=run_simulation)

    plot_p = sub.add_parser("plot",
        description="Plot the simulator's output data",
        epilog="You must run the simulator first for this to work.")
    plot_p.add_argument("-v", "--verbose",
                       help="enable debug messages",
                       action="store_true")
    plot_p.add_argument("-d", "--directory",
                       help="output to a specific directory",
                       action="store", type=pathlib.Path)

    fetch_p = sub.add_parser("fetch",
        description="Download required data for the simulator",
        epilog="Not implemented yet!")
    fetch_p.add_argument("-v", "--verbose",
                       help="enable debug messages",
                       action="store_true")
    fetch_p.add_argument("-d", "--directory",
                       help="output to a specific directory",
                       action="store", type=pathlib.Path)
    
    args = parser.parse_args()
    args.func(args)

