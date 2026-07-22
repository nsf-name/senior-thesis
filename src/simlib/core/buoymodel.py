import xarray as xr
import numpy as np
import pandas as pd
import geopandas as gpd
import haversine
from shapely.geometry import Point

from dataclasses import dataclass, InitVar, field
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime, timedelta

from simlib.core import Trajectory
from simlib.tools import *

# BuoyTrajectory expects one list of date objects, and nothing else.
# the fundamental change here is that we simply need to specify an end and start date,
# it should work just like IceTrajectory in that sense.
# then, we'll also create a custom method to get any arbitrary time.

# also the filename and the id should be separate things. that was a big issue last time.

@dataclass(repr=False)
class BuoyTrajectory(Trajectory):
    def __post_init__(self, timestep):
        super().__post_init__(timestep)
        self.dataset = self.dataset.sel(BuoyID=self.id).sortby("time").drop_duplicates("time")
        self._buoy_t_index = 0

        begin_bound = pd.to_datetime(self.dataset.isel(time=0).time.item())
        end_bound = pd.to_datetime(self.dataset.isel(time=self.dataset.sizes["time"] - 1).time.item())

        self._buoy_time_unbounded = self.start_day is None and self.end_day is None

        if self.start_day is None:
            self.start_day = begin_bound
        elif self.start_day < begin_bound:
            self.start_day = begin_bound

        # now set the start day correctly if we updated it
        if type(self._t) != datetime:
            self._t = pd.to_datetime(self.start_day)
        else:
            self._t = self.start_day

        if self.end_day is None:
            self.end_day = end_bound
        elif self.end_day > end_bound:
            self.end_day = end_bound

        # clean up the ends, too, if needed
        if type(self.end_day) != datetime:
            self.end_day = pd.to_datetime(self.end_day)
        if type(self.start_day) != datetime: 
            self.start_day = pd.to_datetime(self.start_day)

    def __len__(self):
        return self.dataset.sizes["time"]

    def __next__(self) -> np.ndarray:
        # our vector dataset contains no entries beyond this, so stop
        if self._t >= datetime(2025, 1, 1):
            self._end_iter()
        # don't iter beyond our last date, but do include it
        if self._t > self.end_day:
            self._end_iter()
        # if we're at the end of our index if we're using it, also stop
        if (self._buoy_t_index + 1) >= len(self):
            self._end_iter()
            
        maybe_apply(self.verbose, lambda: print(f"TIME: {self._t}:"))

        # if we don't define a timestep at all, just use the next index
        if self._buoy_time_unbounded:
            self._t = pd.to_datetime(self.dataset.isel(time=self._buoy_t_index).time.item())

        new = self._lookup_vector(self._t)
        maybe_apply(self.verbose, lambda: print(f"DIFF: {new - self._pos}"))

        self._pos = new
        # either add the timestep, or pick the next time index if none is defined
        if self._buoy_time_unbounded:
            self._buoy_t_index += 1
        else:
            self._t += self.timestep

        self.pos_list.append(self._pos)
        self.date_list.append(self._t)

        maybe_apply(self.verbose, lambda: print(f"COORDS: {self._pos}"))
        return tuple(self._pos)

    def _lookup_vector(self, t) -> np.array:
        value = self.dataset.sel(time=t, method='nearest')
        return np.array([value.Lat.item(), value.Lon.item()])

    def _end_iter(self):
        maybe_apply(self.verbose, lambda: print(f"SIM TERMINATED"))
        # since we are now done, we can compute the position list fast, in km of course.
        xv, yv = self.pos_list[:-1], self.pos_list[1:]
        try:
            self.dist_list = haversine.haversine_vector(xv, yv, unit=haversine.Unit.KILOMETERS) 
        except Exception as err:
            # TODO: fix this later something's fucked up here
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

    @property
    def start_pos(self):
        if self.consumed:
            return self.poslist[0]
        else:
            raise UnpreparedSimulatorError("This object's iterator must be consumed first")

    @property
    def peek(self):
        """Returns the first one in this ID's position list, not necessarily the first for this sim."""
        begin_bound = pd.to_datetime(self.dataset.isel(time=0).time.item())
        return self._lookup_vector(begin_bound)
