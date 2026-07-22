import xarray as xr
import numpy as np
import pandas as pd
import geopandas as gpd
import pyproj
import haversine
from shapely.geometry import Point

from dataclasses import dataclass, InitVar, field
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime, timedelta

from simlib.core import Trajectory
from simlib.tools import *

# IceTrajectory is special in that it needs a starting set of coordinates...
# need to catch the bug where that isn't right.
@dataclass(repr=False)
class IceTrajectory(Trajectory):
    # unique requirements not held by the superclass
    init_pos: np.ndarray
    # optional for debug reasons. holds the list of vectors
    vec_list: Optional[list[np.ndarray]] = field(default_factory=list)

    def __post_init__(self, timestep):
        # IceTrajectory MUST have a start date. otherwise, it throws!
        # this is so important it runs before the constructor!
        if self.start_day == None:
            raise MissingDatesError("IceTrajectory's behavior is undefined without a start date")
        super().__post_init__(timestep)
        self.dataset = self.dataset.sortby("time")
        # expensive to instantiate, but we need to do this exactly once. i hate pyproj
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

        # each self.timestep, IceTrajectory looks up the vector for its coordinates and picks the closest one.
        # TODO: IceTrajectory needs to regroup by pandas time ticks so that vectors are added correctly,
        # if that is something Alice deems is needed. or maybe I just add it for fun. who knows

    def __next__(self) -> np.ndarray:
        # our vector dataset contains no entries beyond this.
        if self._t >= datetime(2025, 1, 1):
            self._end_iter()
        # don't iter beyond our last date, but do include it
        if self._t > self.end_day:
            self._end_iter()

        maybe_apply(self.verbose, lambda: print(f"TIME: {self._t}:"))
        newvec = self._lookup_vector(self._pos, self._t)
        self._vec += newvec
        # converting at each step is expensive but there's no better way
        newcoord = self._conv_latlon(self._vec, self._t)
        self._pos = newcoord
        maybe_apply(self.verbose, lambda: print(f"DIFF: {newvec - self._vec}"))
        self._t += self.timestep

        # for some reason this order is fastest??? I'll never understand Python
        self.pos_list.append(self._pos)
        self.date_list.append(self._t)
        self.vec_list.append(self._vec)

        maybe_apply(self.verbose, lambda: print(f"COORDS: {self._pos}"))
        return tuple(self._pos)

    def _lookup_vector(self, xy, t) -> np.array:
        vector = self.dataset.sel(x=xy[0], y=xy[1], time=t, method="nearest")
        # conversion: (1 cm/s x 86,400 s/day) / 100cm/m = 864 m/day
        u = np.nan_to_num(vector.u.values.item() * 864)
        v = np.nan_to_num(vector.v.values.item() * 864)
        maybe_apply(self.verbose, lambda: print(f"PHYSICS: vector pulls the object: ({u}, {v}) m"))
        return np.array([u,v])

    # TODO: these _conv methods probably should be static, but I can't be bothered to fix it atp

    def _conv_latlon(self, xy, t) -> np.array:
        latlon = self.dataset.sel(x=xy[0], y=xy[1], time=t, method="nearest")
        lat = latlon.latitude.values.item()
        lon = latlon.longitude.values.item()
        maybe_apply(self.verbose, lambda: print(f"LOOKUP: ({xy[0]},{xy[1]}) [x,y] is ({lat},{lon}) in [lat,lon]"))
        return np.array([lat,lon])

    def _conv_xy(self, latlon) -> np.array:
        x, y = self._inv.transform(latlon[0], latlon[1])
        maybe_apply(self.verbose, lambda: print(f"LOOKUP: ({latlon[0]},{latlon[1]}) [lat,lon] is ({x},{y}) in [x,y]"))
        return np.array([x,y])

    def _end_iter(self):
        maybe_apply(self.verbose, lambda: print(f"SIM TERMINATED"))
        # since we are now done, we can compute the position list fast, in km of course.
        xv, yv = self.poslist[:-1], self.poslist[1:]
        try:
            self.dist_list = haversine.haversine_vector(xv, yv, unit=haversine.Unit.KILOMETERS) 
        except Exception as err:
            # TODO: fix this later something's a bit fucked
            pass
            #print(f"({type(self)}, {self.id}): unexpected {err=}, {type(err)=} when haversine-calculating")
        self._is_consumed = True
        raise StopIteration

    # TODO: implement
    def plot(self) -> plt.Axes:
        raise NotImplementedError

    # TODO: implement
    def curried_plot(self, curry: plt.Axes) -> plt.Axes:
        raise NotImplementedError
