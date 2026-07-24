from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from haversine import haversine_vector, Unit
import numpy as np
import pandas as pd

from simlib.core.basemodel import Trajectory
from simlib.tools.utilities import MissingDatesError

@dataclass(repr=False)
class IceTrajectory(Trajectory):
    """Class to simulate ice vector trajectory objects.

    Attributes:
        init_pos: (lat, lon) coordinate tuple where the simulator starts moving from.
        vec_list: Accumulated motion vectors. For external capture.
    """
    init_pos: np.ndarray
    vec_list: Optional[list[np.ndarray]] = field(default_factory=list)

    def __post_init__(self, timestep):
        if self.start_day == None:
            raise MissingDatesError("IceTrajectory needs a start date")
        super().__post_init__(timestep)
        self.dataset = self.dataset.sortby("time")
        # expensive to instantiate, but we need to do this exactly once. i hate pyproj
        import pyproj
        self._inv = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3408")

        # self._pos is our (x,y); self._vec, our (lat,lon)
        self._pos = np.array([self.init_pos[0], self.init_pos[1]])
        self._vec = self._conv_xy((self.init_pos[0], self.init_pos[1]))

        # correctly set self._t and self.end_day if undefined
        if type(self._t) != datetime:
            self._t = pd.to_datetime(self.start_day)
        else:
            self._t = self.start_day

        if self.end_day == None:
            # set to datetime(2025, 1, 1), the limit of this data.
            self.end_day = datetime(2025, 1, 1)

        # clean up the ends, too, if needed
        if type(self.end_day) != datetime:
            self.end_day = pd.to_datetime(self.end_day)
        if type(self.start_day) != datetime: 
            self.start_day = pd.to_datetime(self.start_day)

        self._log.debug("init finished")

        # each self.timestep, IceTrajectory looks up the vector for its coordinates
        # and picks the closest one.
        # TODO: IceTrajectory needs to regroup by pandas time ticks so
        # that vectors are added correctly,
        # if that is something Alice deems is needed. or maybe I just add it for fun.

    def __next__(self) -> tuple[np.ndarray]:
        # our vector dataset contains no entries beyond this.
        if self._t >= datetime(2025, 1, 1):
            self._end_iter()
        # don't iter beyond our last date, but do include it
        if self._t > self.end_day:
            self._end_iter()

        self._log.debug(f"TIME: now {self._t}")
        newvec = self._lookup_vector(self._pos, self._t)
        self._vec += newvec
        # converting at each step is expensive but there's no better way
        newcoord = self._conv_latlon(self._vec, self._t)
        self._pos = newcoord
        self._log.debug(f"DIFF: {newvec - self._vec}")
        self._t += self.timestep

        # for some reason this order is fastest??? I'll never understand Python
        self.pos_list.append(self._pos)
        self.date_list.append(self._t)
        self.vec_list.append(self._vec)

        self._log.debug(f"COORDS: {self._pos}")
        return tuple(self._pos)

    def _lookup_vector(self, xy, t) -> np.ndarray:
        vector = self.dataset.sel(x=xy[0], y=xy[1], time=t, method="nearest")
        # conversion: (1 cm/s x 86,400 s/day) / 100cm/m = 864 m/day
        u = np.nan_to_num(vector.u.values.item() * 864)
        v = np.nan_to_num(vector.v.values.item() * 864)
        self._log.debug(f"PHYSICS: vector pulls the object: ({u}, {v}) m")
        return np.array([u,v])

    # TODO: these _conv methods probably should be static

    def _conv_latlon(self, xy, t) -> np.ndarray:
        latlon = self.dataset.sel(x=xy[0], y=xy[1], time=t, method="nearest")
        lat = latlon.latitude.values.item()
        lon = latlon.longitude.values.item()
        self._log.debug(f"LOOKUP: ({xy[0]},{xy[1]}) [x,y] is ({lat},{lon}) in [lat,lon]")
        return np.array([lat,lon])

    def _conv_xy(self, latlon) -> np.ndarray:
        x, y = self._inv.transform(latlon[0], latlon[1])
        self._log.debug(f"LOOKUP: ({latlon[0]},{latlon[1]}) [lat,lon] is ({x},{y}) in [x,y]")
        return np.array([x,y])

    def _end_iter(self):
        self._log.debug(f"SIM TERMINATED")
        # since we are now done, we can compute the position list fast, in km of course.
        xv, yv = self.poslist[:-1], self.poslist[1:]
        try:
            self.dist_list = haversine_vector(
                xv, yv, unit=Unit.KILOMETERS
            )
        except Exception as err:
            self._log.debug(f"unexpected {err=} when haversine-calculating")
        self._is_consumed = True
        raise StopIteration

    # TODO: implement plot methods
    def plot(self):
        raise NotImplementedError

    def curried_plot(self):
        raise NotImplementedError
