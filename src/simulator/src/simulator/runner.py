# TODO: figure out how to import simlib in here
from dataclasses import dataclass
from pathlib import Path

from simlib.tools.logging import conf_interactive_logger, LogLevel

@dataclass()
class SimulatorPrefs:
    out_path: Path

def run_simulation(args):
    log = conf_interactive_logger("main", LogLevel.INFO)
    print("""
    They say science is done on the shoulders of giants.
    Not here; at Aperture we do all our science from scratch. No hand-holding. 
    """)
    if args.verbose:
        print("And we're also very verbose.")
    print(args.directory)
    log.debug("we are LIVE")
