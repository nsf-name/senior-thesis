from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from haversine import Unit, haversine_vector
import numpy as np
import pandas as pd
from simlib.core.basemodel import Trajectory
from simlib.tools.utilities import ImpossibleArgumentsError, MissingDatesError
import xarray as xr


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
        # expensive, but we do need it, at least for now
        import pyproj

        self._inv = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3408")
        self._fwd = pyproj.Transformer.from_crs("EPSG:3408", "EPSG:4326")

        # self._pos is our (x,y); self._vec, our (lat,lon)
        self._pos = (self.init_pos[0], self.init_pos[1])
        try:
            self._vec = self._conv_xy((self._pos[0], self._pos[1]))
        except Exception as err:
            self._log.error(f"""
            ERROR: failed to create simulator, exception: {err}
            Initial passed values were {self._pos}
            Treating this simulator as if it were complete.  
            """)
            self._end_iter()

        # correctly set self._t and self.end_day if undefined
        if not isinstance(self._t, datetime):
            self._t = pd.to_datetime(self.start_day)
        else:
            self._t = self.start_day

        if self.end_day is None:
            # set to datetime(2025, 1, 1), the limit of this data.
            self.end_day = datetime(2025, 1, 1)

        # clean up typing since they're internally raw Unix time
        if not isinstance(self.end_day, datetime):
            self.end_day = pd.to_datetime(self.end_day)
        if not isinstance(self.start_day, datetime):
            self.start_day = pd.to_datetime(self.start_day)

        self._log.debug(f"Timestep resolution: {self.timestep}")
        self._log.debug(f"Current date bounds: {self.start_day}, {self.end_day}")
        # now, we cut our dataset to size...
        self.dataset = self.dataset.sel(time=slice(self.start_day, self.end_day))
        # let's see if we defined a timestamp, and use indexing if so
        if self.timestep is None:
            # not the clearest variable name, but no need for a refactor
            self._tlen = self.dataset.indexes["time"].to_pydatetime()  # type: ignore
            self._t_index = 0
        self._log.debug("Init complete")

        # TODO: IceTrajectory needs to regroup by pandas time ticks so
        # that vectors are added correctly, if that is something Alice deems is needed.
        # or maybe I just add it for fun. who knows?

    # TODO: this len() is actually just plainly incorrect
    def __len__(self) -> int:
        if self.pos_list != []:
            return len(self.pos_list)
        return 0

    def __iter__(self):
        return self

    def step(self):
        """Step the simulator by exactly one tick."""
        return next(self)

    def __next__(self) -> tuple[float, float]:
        """Returns the next position."""
        # invariant: if this fails, something is wrong
        assert isinstance(self._t, datetime)

        # TODO: comment _end_iter() so we know why we ended iteration.
        # this will help with debugging.

        # if we're done, we shouldn't be iterating, so suspend safely.
        if self.consumed:
            raise StopIteration
        # our vector dataset contains no entries beyond this.
        if self._t >= datetime(2025, 1, 1):
            self._end_iter()
        # don't iter beyond our last date, but do include it
        if (self.end_day is not None) and (self._t > self.end_day):
            self._end_iter()
        # if we're rolling with an index-based method: stop iterating at len()
        if (self.timestep is None) and (self._t_index >= len(self._tlen) - 1):
            self._end_iter()

        self._log.debug(f"TIME: currently {self._t}")
        # if we have no index, call lookup vector appropriately
        if self.timestep is None:
            newvec = self._lookup_vector(self._pos, index=self._t_index)
        else:
            newvec = self._lookup_vector(self._pos, t=self._t)

        # combine our new float correctly, and convert coordinate.
        # TODO: step through one day manually???
        self._vec = (self._vec[0] + newvec[0], self._vec[1] + newvec[1])
        self._pos = self._conv_latlon(self._vec)
        self._log.debug(f"DIFF: was {newvec}, now {self._vec}")

        if self.timestep is None:
            self._t_index += 1
            self._t = self._tlen[self._t_index]
        else:
            self._t += self.timestep

        self.pos_list.append(self._pos)
        self.date_list.append(self._t)
        self.vec_list.append(self._vec)

        self._log.debug(f"COORDS: {self._pos}")
        return self._pos

    def _lookup_vector(
        self,
        xy: tuple[float, float],
        t: Optional[datetime] = None,
        index: Optional[int] = None,
    ) -> tuple[float, float]:  # type: ignore
        """Lookup a (x,y) coordinate and return the vector motion."""

        if t is None and index is None:
            raise ImpossibleArgumentsError(
                "You must call _lookup_vector with at least one of t or index"
            )

        if t is not None and index is not None:
            raise ImpossibleArgumentsError(
                "You must call _lookup_vector with only one argument"
            )

        if t is not None:
            vector = self.dataset.sel(x=xy[0], y=xy[1], time=t, method="nearest")
            # conversion: (1 cm/s x 86,400 s/day) / 100cm/m = 864 m/day
            u = float(np.nan_to_num(vector.u.values.item() * 864))
            v = float(np.nan_to_num(vector.v.values.item() * 864))
            self._log.debug(f"PHYSICS: vector pulls the object: ({u}, {v}) m")
            self._log.debug("TIME: stepping one day")
            return (u, v)

        if index is not None:
            vector = self.dataset.sel(
                x=xy[0], y=xy[1], time=self._tlen[index], method="nearest"
            )

            # conversion: (1 cm/s x TIME s) / 100 cm/m = ?? m/TIME
            delta = (self._tlen[index + 1] - self._tlen[index]).total_seconds() / 100
            u = float(np.nan_to_num(vector.u.values.item() * delta))
            v = float(np.nan_to_num(vector.v.values.item() * delta))
            self._log.debug(f"PHYSICS: vector pulls the object: ({u}, {v}) m")
            self._log.debug(f"TIME: stepping {delta * 100}s")
            return (u, v)

    # these conv aren't static because they reuse the objects to avoid pyproj
    # having to recreate them, and to share loggers, too.

    def _conv_latlon(self, xy) -> tuple[float, float]:
        """Convert (x,y) to (lat,lon)."""
        lat, lon = self._fwd.transform(xy[0], xy[1])
        self._log.debug(
            f"LOOKUP: ({xy[0]},{xy[1]}) [x,y] is ({lat},{lon}) in [lat,lon]"
        )
        return (lat, lon)

    def _conv_xy(self, latlon) -> tuple[float, float]:
        """Convert (lat,lon) to (x,y)."""
        x, y = self._inv.transform(latlon[0], latlon[1])
        self._log.debug(
            f"LOOKUP: ({latlon[0]},{latlon[1]}) [lat,lon] is ({x},{y}) in [x,y]"
        )
        return (x, y)

    def _end_iter(self):
        """One-way transition to stopping execution."""
        self._log.debug("SIM TERMINATED")
        # since we are now done, we can compute the position list fast, in km of course.
        xv, yv = self.pos_list[:-1], self.pos_list[1:]
        try:
            self.dist_list = haversine_vector(xv, yv, unit=Unit.KILOMETERS)
        except Exception as err:
            self._log.warning(f"ERROR: haversine failed with exception {err}")
        self._is_consumed = True
        raise StopIteration

    def runsim(self):
        """Exhaust the simulator's internal iterator."""
        for _ in self:
            pass

    # TODO: implement plot methods
    def plot(self):
        raise NotImplementedError

    def curried_plot(self):
        raise NotImplementedError
