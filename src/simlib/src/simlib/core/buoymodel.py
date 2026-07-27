from dataclasses import dataclass
from datetime import datetime
from typing import cast
from itertools import chain

from haversine import Unit, haversine_vector
import polars as pl
from simlib.core.basemodel import Trajectory


@dataclass(repr=False)
class BuoyTrajectory(Trajectory):
    """Class to wrap buoy data. Does not require iteration.

    Attributes:
        dataframe: Source polars dataframe containing buoy run.
    """

    # TODO: to clean them, do the following:
    # pl.read_csv(csvfiles[0]).with_columns(pl.col('datetime').str.to_datetime())
    dataframe: pl.DataFrame

    def __post_init__(self):
        super().__post_init__()
        self._log.info("BuoyTrajectory init starting")

        begin_bound = self.dataframe.head(1).get_column("datetime").item()
        end_bound = self.dataframe.tail(1).get_column("datetime").item()

        # snap to a correct START bound.
        if self.start_day is None:
            self.start_day = begin_bound
        # start day can't be before the bounds of our data
        elif self.start_day < begin_bound:
            self.start_day = begin_bound

        # snap to a correct END bound.
        if self.end_day is None:
            self.end_day = end_bound
        # end day can't be beyond the bounds of our data
        elif self.end_day > end_bound:
            self.end_day = end_bound

        # now, filter accordingly.
        self.dataframe.filter(
            (pl.col("datetime") >= self.start_day)
            & (pl.col("datetime") <= self.end_day)
        )

        # report our date status to ensure we didn't bungle it
        self._log.debug(f"Timestep resolution: {self.timestep}")
        self._log.debug(f"Current date bounds: {self.start_day}, {self.end_day}")

        # now it'll do basically all the hard work for us
        self._log.debug("Preparing to automate all math...")
        self._setup()
        self._log.info("BuoyTrajectory complete, is now consumed")

        # then call .export() at create-time to dump this back out!

    def _setup(self):
        self.pos_list = self.dataframe.select(["lat", "lon"]).rows()
        self.date_list = list(
            chain.from_iterable(
                # Pyright can't see I'm clearly correct here
                cast(list[datetime], self.dataframe.select("datetime").rows())  # type: ignore[reportArgumentType]
            )
        )
        array = self.dataframe.select(["lat", "lon"]).to_numpy()
        try:
            self.dist_list = haversine_vector(
                array[:-1], array[1:], unit=Unit.KILOMETERS
            )
        except Exception as err:
            self._log.warning(f"ERROR: haversine failed with exception {err}")
        self._is_consumed = True

    def __len__(self):
        # .shape returns (rows, columns).
        return self.dataframe.shape[0]

    # TODO: implement plot methods
    def plot(self):
        raise NotImplementedError

    def curried_plot(self):
        raise NotImplementedError
