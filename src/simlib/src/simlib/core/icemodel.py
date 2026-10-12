from dataclasses import dataclass, field
from datetime import datetime

from haversine import Unit, haversine_vector
import numpy as np
import pandas as pd
import xarray as xr
import pyproj

from simlib.core.basemodel import Trajectory
from simlib.tools.utilities import ImpossibleArgumentsError, MissingDatesError


@dataclass(repr=False)
class IceTrajectory(Trajectory):
    """Class to simulate ice vector trajectory objects. Must be iterated.

    Attributes:
        dataset: Source xarray dataset of ice vectors.
        init_pos: (lat, lon) coordinate tuple where the simulator starts moving from.
        vec_list: Accumulated motion vectors. For external capture.
    """

    dataset: xr.Dataset
    init_pos: tuple[float, float]
    vec_list: list[tuple[float, float]] = field(default_factory=list)

    def __post_init__(self):
        if self.start_day is None:
            raise MissingDatesError("IceTrajectory needs a start date")
        super().__post_init__()
        self._log.info("IceTrajectory init starting")
        self.dataset = self.dataset.sortby("time")

        self._inv = pyproj.Transformer.from_crs(
            "EPSG:4326", "EPSG:3408", always_xy=True
        )
        self._fwd = pyproj.Transformer.from_crs(
            "EPSG:3408", "EPSG:4326", always_xy=True
        )

        self._log.info("Starting position: %s", self.init_pos)
        try:
            self._pos_xy = self._latlon_to_xy(self.init_pos)
        except TypeError as err:
            self._kill_iter(f"failed to create simulator: {err}")

        if not isinstance(self._t, datetime):
            self._t = pd.to_datetime(self.start_day)
        else:
            self._t = self.start_day

        if self.end_day is None:
            # the ice vector dataset is undefined past this point
            self.end_day = datetime(2025, 1, 1)

        # clean up typing since they're internally raw Unix time
        if not isinstance(self.end_day, datetime):
            self.end_day = pd.to_datetime(self.end_day)
        if not isinstance(self.start_day, datetime):
            self.start_day = pd.to_datetime(self.start_day)

        self._log.debug("Timestep resolution: %s", self.timestep)
        self._log.debug("Current date bounds: %s, %s", self.start_day, self.end_day)

        self.dataset = self.dataset.sel(time=slice(self.start_day, self.end_day))
        # used for sanity checking later
        self.x_vals = self.dataset.x.values
        self.y_vals = self.dataset.y.values

        # let's see if we defined a timestamp, and use indexing if so
        if self.timestep is None:
            self._tlen = self.dataset.indexes["time"].to_pydatetime()
            self._t_index = 0
        self._log.debug("Init complete")

    def __len__(self) -> int:
        if self.pos_list:
            return len(self.pos_list)
        return 0

    def __iter__(self):
        return self

    def step(self):
        """Step the simulator by exactly one tick."""
        return next(self)

    def __next__(self) -> tuple[float, float]:
        """Returns the next position."""
        # if we're done, we shouldn't be iterating, so suspend safely.
        if self.consumed:
            raise StopIteration
        # our vector dataset contains no entries beyond this.
        if self._t >= datetime(2025, 1, 1):
            self._kill_iter("Impossible starting date.")
        # don't iter beyond our last date, but do include it
        if (self.end_day is not None) and (self._t > self.end_day):
            self._kill_iter("Impossible ending date.")
        # if we're rolling with an index-based method: stop iterating at len()
        if (self.timestep is None) and (self._t_index >= len(self._tlen) - 1):
            self._end_iter("Exceeded bounds of timestep indexing.")

        self._log.debug("TIME: currently %s", self._t)
        # if we have no index, call lookup vector appropriately
        if self.timestep is None:
            newvec = self._lookup_vector(self._pos_xy, index=self._t_index)
        else:
            newvec = self._lookup_vector(self._pos_xy, t=self._t)

        self._log.debug("DIFF: was %s, now %s", newvec, self._pos_xy)
        self._pos_xy = (self._pos_xy[0] + newvec[0], self._pos_xy[1] + newvec[1])

        latlon = self._xy_to_latlon(self._pos_xy)

        self.pos_list.append(latlon)
        self.vec_list.append(newvec)

        if self.timestep is None:
            self._t_index += 1
            self._t = self._tlen[self._t_index]
        else:
            self._t += self.timestep

        self.date_list.append(self._t)

        self._log.debug("COORDS: %s", latlon)
        return latlon

    def _lookup_vector(
        self,
        xy: tuple[float, float],
        t: datetime | None = None,
        index: int | None = None,
    ) -> tuple[float, float]:
        """Lookup a (x,y) coordinate and return the vector motion."""

        if t is None and index is None:
            raise ImpossibleArgumentsError(
                "You must call _lookup_vector with at least one of t or index"
            )

        if t is not None and index is not None:
            raise ImpossibleArgumentsError(
                "You must call _lookup_vector with only one argument"
            )

        # out of bounds check: are we too far from the nearest grid cell
        # for the values to physically make sense?
        # if (
        #     abs(self.x_vals - xy[0]).min() > 12500.0
        #     or abs(self.y_vals - xy[1]).min() > 12500.0
        # ):
        #     self._kill_iter("Drifted too far from nearest grid cell.")

        if t is not None:
            vector = self.dataset.sel(x=xy[0], y=xy[1], time=t, method="nearest")
            # conversion: (1 cm/s x 86,400 s/day) / 100cm/m = 864 m/day
            u = float(vector.u.values.item() * 864)
            v = float(vector.v.values.item() * 864)
            if np.isnan(u) or np.isnan(v):
                self._kill_iter("Illegal u or v value.")
            self._log.debug("PHYSICS: vector pulls the object: (%s, %s) m", u, v)
            self._log.debug("TIME: stepping one day")
            return (u, v)

        if index is not None:
            vector = self.dataset.sel(
                x=xy[0], y=xy[1], time=self._tlen[index], method="nearest"
            )

            # conversion: (1 cm/s x TIME s) / 100 cm/m = ?? m/TIME
            delta = (self._tlen[index + 1] - self._tlen[index]).total_seconds() * 0.01
            u = float(vector.u.values.item() * delta)
            v = float(vector.v.values.item() * delta)
            if np.isnan(u) or np.isnan(v):
                self._kill_iter("Illegal u or v value.")
            self._log.debug("PHYSICS: vector pulls the object: (%s, %s) m", u, v)
            self._log.debug("TIME: stepping %ss", delta * 100)
            return (u, v)

    def _latlon_to_xy(self, latlon: tuple[float, float]) -> tuple[float, float]:
        """(lat, lon) -> (x, y) in EPSG:3408"""
        x, y = self._inv.transform(latlon[1], latlon[0])  # always_xy wants (lon, lat)
        return (x, y)

    def _xy_to_latlon(self, xy: tuple[float, float]) -> tuple[float, float]:
        """(x, y) in EPSG:3408 -> (lat, lon)"""
        lon, lat = self._fwd.transform(xy[0], xy[1])  # always_xy returns (lon, lat)
        return (lat, lon)

    def _end_iter(self, msg: str | None):
        """One-way transition to stopping execution."""
        self._log.debug("SIM TERMINATED")

        if msg is not None:
            self._log.info("Message: %s", msg)

        try:
            xv, yv = self.pos_list[:-1], self.pos_list[1:]
            self.dist_list = haversine_vector(xv, yv, unit=Unit.KILOMETERS)
        except ValueError:
            self._log.warning("ERROR: haversine failed due to simulator also failing!")
        except IndexError:
            self._log.warning("ERROR: haversine failed due to simulator also failing!")

        self._is_consumed = True
        raise StopIteration

    def _kill_iter(self, err: str):
        """One-way transition to stopping, with a warning."""
        self._log.debug("SIM TERMINATED")
        self._log.error("SOMETHING IS WRONG: %s", err)
        self._is_consumed = True
        raise StopIteration

    def runsim(self):
        """Exhaust the simulator's internal iterator."""
        for _ in self:
            pass
