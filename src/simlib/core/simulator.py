import xarray as xr
import pandas as pd
import numpy as np
import cartopy.crs as ccrs
import cartopy
from glob import glob
from typing import Callable
import datetime
from dataclasses import dataclass, InitVar, field

from simlib.tools import *

@dataclass(repr=False)
class Simulator():
    """Holds, creates, manages, and runs simulations."""
    buoy_data: xr.Dataset
    ice_data: xr.Dataset
    verbose: Optional[bool] = False
    
    def __post_init__(self):
        maybe_apply(self.verbose, lambda: print("[ INIT ] Starting initialization..."))
        # this is where the dataset containing date splits is made
        self._sim_dict = Simulator._split_buoy(self.buoy_data, 
                                               lambda a, b: (pd.Timestamp(b) - pd.Timestamp(a)) <= pd.Timedelta(days=7))
        maybe_apply(self.verbose, lambda: print("[ INIT ] Done creating run splits."))
        # then this one contains a dictionary of the actual simulator objects to run
        self._obj_dict = dict()
        maybe_apply(self.verbose, lambda: print("[ INIT ] Starting simulator object creation..."))
        for key in self._sim_dict:
            for num in range(len(self._sim_dict[key])):
                buoy_sim = BuoyTrajectory(dataset=self.buoy_data,
                                          start_day=self._sim_dict[key][num][0],
                                          end_day=self._sim_dict[key][num][-1],
                                          id=key)
                # peek the FIRST one so we can run in parallel
                start_pos = buoy_sim.peek
                ice_sim = IceTrajectory(dataset=self.ice_data,
                                        start_day=self._sim_dict[key][num][0],
                                        end_day=self._sim_dict[key][num][-1],
                                        id=key,
                                        init_pos=start_pos)
                maybe_apply(self.verbose, lambda: print(f"[ INIT ] Creating simulators for {key}_{num}..."))
                self._obj_dict[f"{key}_{num}"] = (buoy_sim, ice_sim)
        maybe_apply(self.verbose, lambda: print("[ INIT ] Done with initialization."))

    @staticmethod
    def plot_sim(key: str, path: Path, simpair: list[BuoyTrajectory, IceTrajectory]):
        """Save an image of the two simulators to disk."""
        buoysim, icesim = simpair
        plotbase, plotthing = plotting.plot_basemap(title=f"Sim No. {key}", 
                                           subtitle=f"{buoysim.start_day}-{buoysim.end_day}")
        plot = plotting.plot_quickline(plotting.plot_quickline(plotthing, buoysim.poslist), icesim.poslist)
        plot.set_extent([-180, 180, 65, 90], crs=ccrs.PlateCarree())
        plotbase.savefig(path)

    @staticmethod
    def dump_sim(simpair: list[BuoyTrajectory, IceTrajectory]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Dump a pair of simulators into a DataFrame."""
        buoy_poslist, buoy_timelist = simpair[0].poslist, simpair[0].timelist 
        ice_poslist, ice_timelist = simpair[1].poslist, simpair[1].timelist 
        buoy_zipper = [(*pos, t) for pos, t in zip(buoy_poslist, buoy_timelist)]
        ice_zipper = [(*pos, t) for pos, t in zip(ice_poslist, ice_timelist)]
        return (pd.DataFrame(buoy_zipper, columns=["lat", "lon", "time"]),
                pd.DataFrame(ice_zipper, columns=["lat", "lon", "time"]))

    @staticmethod
    def _split_runs(items: np.ndarray, pred: Callable) -> list:
        """pred(prev, curr) -> True if curr continues the run with prev."""
        if not items.any():
            return []
        if len(items) == 1:
            return [[items[0]]]
        # this is hard to read but it's vectorized recursion
        breaks = np.fromiter(
            (not pred(p, c) for p, c in zip(items[:-1], items[1:])),
            dtype=bool, count=len(items) - 1
        )
        split_points = np.where(breaks)[0] + 1
        return [list(run) for run in np.split(items, split_points)]

    @staticmethod
    def _split_buoy(buoys: xr.Dataset, pred: Callable) -> dict:
        """Sort all buoys into a dictionary by BuoyID, after calling split_runs(buoys.items, pred) on them."""
        return {
            k: Simulator._split_runs(
        # TODO: dropping dupes here seems fine... I assume the different time results come from the netcdf-ization of this data
                v.drop_duplicates("index").unstack("index").dropna(dim='time', how='all', subset=['Lat', 'Lon']).time.values, 
                pred
            )
            for k, v in buoys.groupby('BuoyID')
        }

    @property
    def simulators(self) -> list[int]:
        return list(self._sim_dict.keys())

    @property
    def simdict(self) -> dict:
        return self._sim_dict

    @property
    def objects(self) -> dict:
        return self._obj_dict

    @property
    def objdict(self) -> dict:
        return self._obj_dict
