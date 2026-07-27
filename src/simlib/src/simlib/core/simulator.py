from dataclasses import dataclass
from glob import glob
import pathlib
from queue import Queue
from typing import Optional
from typing import Any

import polars as pl
from simlib.core import BuoyTrajectory, IceTrajectory
from simlib.tools.logging import LogLevel, conf_interactive_logger, conf_worker_logger


@dataclass(repr=False)
class Simulator:
    """Holds, creates, manages, and runs simulations.

    Attributes:
        log_queue: Handler to the main log of the runner. If None, creates one.
        loglevel: The amount of logs to be emitted for sims. If None, uses LogLevel.WARNING.
        name: Defines a name; suffixed with "Simulator". If None, just uses "Simulator".
    """

    buoydir: pathlib.Path
    icedir: pathlib.Path
    log_queue: Optional[Queue[Any]] = None
    loglevel: Optional[LogLevel] = None
    name: Optional[str] = None

    def __post_init__(self):
        if self.loglevel is None:
            self.loglevel = LogLevel.WARNING

        if self.name is None:
            self.name = "Simulator"
        else:
            self.name = self.name + "-Simulator"

        if self.log_queue is None:
            self._log = conf_interactive_logger(self.name, self.loglevel)
        else:
            self._log = conf_worker_logger(self.name, self.log_queue, self.loglevel)

        self._log.info("Simulator init is complete, now making simulators...")
        # get cleaned paths for each one
        buoylist = map(pathlib.Path, list(sorted(glob(str(self.buoydir) + "/*.csv"))))

        # TODO:
        # conceptually, the runs aren't that bad. the buoys is just a glob over
        # the files we were passed in. then the ice files are just loading the netCDF.
        # of course, what we need to do is just do buoys first. ice comes second.
        # we also need to finish the plotter. do ice one at a time...

        # now make a dictionary to hold all the runs
        self._sim_dict = dict()

        for location in buoylist:
            name = location.name.rstrip(".csv")
            self._log.debug(f"Creating simulator for {name}...")
            data = pl.read_csv(location).with_columns(
                pl.col("datetime").str.to_datetime()
            )
            self._sim_dict[name] = BuoyTrajectory(
                id=name, dataframe=data, loglevel=self.loglevel
            )

        self._log.info("Simulator setup complete")

    def plot_sim(self, simpair: tuple[BuoyTrajectory, IceTrajectory]):
        """Save an image of the two simulators to disk."""
        raise NotImplementedError
        # TODO: this is where R will be dropped in
        # we need to FFI to R in order to do plots, since Cartopy sucks

    @property
    def simulators(self) -> list[int]:
        return list(self._sim_dict.keys())

    @property
    def simdict(self) -> dict:
        return self._sim_dict

    # TODO: a method to fetch just ice objects and buoy objects would be cool,
    # but isn't strictly needed. probably requires zip() trickery which is expensive
