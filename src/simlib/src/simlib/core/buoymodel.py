from dataclasses import dataclass
from datetime import datetime
from itertools import chain
from typing import cast

import polars as pl
from haversine import Unit, haversine_vector

from simlib.core.basemodel import Trajectory


@dataclass(repr=False)
class BuoyTrajectory(Trajectory):
    """Class to wrap buoy data. Does not require iteration.

    Attributes:
        dataframe: Source polars dataframe containing buoy run.
    """

    dataframe: pl.DataFrame

    def __post_init__(self):
        super().__post_init__()
        self._log.info("BuoyTrajectory init starting")

        begin_bound = self.dataframe.head(1).get_column("datetime").item()
        end_bound = self.dataframe.tail(1).get_column("datetime").item()

        # start day can't be before the bounds of our data
        if self.start_day is None or self.start_day < begin_bound:
            self.start_day = begin_bound

        # end day can't be beyond the bounds of our data
        if self.end_day is None or self.end_day > end_bound:
            self.end_day = end_bound

        # now, filter accordingly.
        self.dataframe.filter(
            (pl.col("datetime") >= self.start_day)
            & (pl.col("datetime") <= self.end_day)
        )

        # report our date status to ensure we didn't bungle it
        self._log.debug("Timestep resolution: %s", self.timestep)
        self._log.debug("Current date bounds: %s, %s", self.start_day, self.end_day)

        # now it'll do basically all the hard work for us
        self._log.debug("Preparing to automate all math...")
        self._setup()
        self._log.info("BuoyTrajectory complete, is now consumed")
        # then call .export() at create-time to dump this back out!

    def _setup(self):
        self.pos_list = self.dataframe.select(["lat", "lon"]).rows()
        self.date_list = list(
            chain.from_iterable(
                cast(list[datetime], self.dataframe.select("datetime").rows())
            )
        )
        array = self.dataframe.select(["lat", "lon"]).to_numpy()
        try:
            xv, yv = array[:-1], array[1:]
            self.dist_list = haversine_vector(xv, yv, unit=Unit.KILOMETERS)
        except ValueError:
            self._log.warning("ERROR: haversine failed due to simulator also failing!")
        except IndexError:
            self._log.warning("ERROR: haversine failed due to simulator also failing!")
        self._is_consumed = True

    def __len__(self):
        # .shape returns (rows, columns).
        return self.dataframe.shape[0]
