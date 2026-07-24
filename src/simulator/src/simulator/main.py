import argparse
import pathlib

from simulator.runner import run_simulation

# TODO: port parallel.py to fit in this new shape.

def main():    
    parser = argparse.ArgumentParser(
        prog="simulator",
        description="Simulate sea ice buoys",
        epilog="Copyright Nathaniel Flores 2026, MIT license."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    base = pathlib.Path().resolve()

    run_p = sub.add_parser("run",
        description="Simulate Lagrangian buoys in sea ice",
        epilog="This can be very computationally intensive.")
    run_p.add_argument("-v", "--verbose",
                       help="enable debug messages",
                       action="store_true")
    run_p.add_argument("-o", "--out-dir", metavar="PATH",
                       help="default: ./sim-data/runs",
                       action="store", type=pathlib.Path,
                       default=base / "sim-data" / "runs")
    run_p.add_argument("-b", "--buoy-data", metavar="PATH",
                       help="default: ./buoy-data",
                       action="store", type=pathlib.Path,
                       default=base / "buoy-data")
    run_p.add_argument("-i", "--ice-data", metavar="PATH",
                       help="default: ./ice-data",
                       action="store", type=pathlib.Path,
                       default=base / "ice-data")
    run_p.set_defaults(func=run_simulation)

    plot_p = sub.add_parser("plot",
        description="Plot the simulator's output data",
        epilog="You must run the simulator first for this to work.")
    plot_p.add_argument("-v", "--verbose",
                       help="enable debug messages",
                       action="store_true")
    plot_p.add_argument("-i", "--in-dir", metavar="PATH",
                       help="default: ./sim-data/runs",
                       action="store", type=pathlib.Path,
                       default=base / "sim-data" / "runs")
    plot_p.add_argument("-o", "--out-dir", metavar="PATH",
                       help="default: ./sim-data/plots",
                       action="store", type=pathlib.Path,
                       default=base / "sim-data" / "plots")

    fetch_p = sub.add_parser("fetch",
        description="Download required data for the simulator",
        epilog="Not implemented yet!")
    fetch_p.add_argument("-v", "--verbose",
                       help="enable debug messages",
                       action="store_true")
    fetch_p.add_argument("-b", "--buoy-data", metavar="PATH",
                       help="default: ./buoy-data",
                       action="store", type=pathlib.Path,
                       default=base / "buoy-data")
    fetch_p.add_argument("-i", "--ice-data", metavar="PATH",
                       help="default: ./ice-data",
                       action="store", type=pathlib.Path,
                       default=base / "ice-data")
    
    args = parser.parse_args()
    args.func(args)

