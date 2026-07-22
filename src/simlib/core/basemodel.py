import xarray as xr
import numpy as np
import geopandas as gpd

from dataclasses import dataclass, InitVar, field
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime, timedelta

from simlib.tools import *

@dataclass(kw_only=True)
class Trajectory():
    """Methods and variables for all simulator trajectory objects."""
    # in a @dataclass, these are instance vars, not class vars.
    dataset: xr.Dataset
    id: int
    # optional; no argument assumes you want all days
    start_day: Optional[datetime] = None
    end_day: Optional[datetime] = None
    # optional for debug reasons. lets you capture into state outside the class, if so desired.
    pos_list: Optional[list[np.ndarray]] = field(default_factory=list)
    date_list: Optional[list[np.ndarray]] = field(default_factory=list)
    # note that distlist contains the haversine-calculated diffs between list elements, ignoring the first.
    dist_list: Optional[list[np.ndarray]] = field(default_factory=list)
    verbose: Optional[bool] = False
    # TODO: means are very computationally expensive. do we want them anyways...?
    # optional; by default we use a 1-day timestep
    timestep: InitVar[Optional[timedelta]] = timedelta(days=1)

    def __post_init__(self, timestep):
        # this affects downstream logic with stepping.
        # default behavior is to just increment by each timestamp; a specific timedelta
        # should advance to the nearest date that fits the time stepping code.
        if timestep is not None:
            self.timestep = timestep
        self._t = self.start_day
        # TODO: fix filenames
        #self._filename = f"{self.id}_buoy"
        self._is_consumed = False
        self._pos = np.zeros(2, dtype=np.float64)

    def __repr__(self):
        return self._repr()

    # probably no good reason to have custom behavior here. __next__ is where it's at 
    def __iter__(self):
        return self

    # easier to just have one representation
    __str__ = __repr__

    def _repr(self):
        return f"{type(self)}(id: {self.id}, start: {self.start_day}, end: {self.end_day})"

    def runsim(self):
        """Exhaust the internal iterator."""
        for tick in self:
            pass
        return (self.pos_list, self.date_list)

    def export(self, type: DataExportType, path: Path):
        """Export the simulator data to the specified type."""
        match type:
            case DataExportType.GEOJSON:
                xs, ys = zip(*self.poslist)
                record = dict(x=xs, y=ys)
                try:
                    gpd.GeoDataFrame(
                        # for more types of data, add more entries to this dict
                        {'geometry': gpd.gpd.points_from_xy(
                            record['x'], record['y'], crs="EPSG:4326"
                        )}
                    ).to_file(path / f"{self._filename}.geojson", driver='GeoJSON')
                except Exception as err:
                    print(f"({type(self)}, {self.id}): unexpected {err=}, {type(err)=} when exporting")
            case DataExportType.CSV:
                # An invariant is that the timestamp list and the position list are always the same length.
                zipper = [(*pos, t, self.id) for pos, t in zip(self.poslist, self.timelist)]
                try:
                    with open(path, 'w') as f:
                         pd.DataFrame(zipper, columns=["lat", "lon", "time", "id"]).to_csv(f)
                except Exception as err:
                    # TODO: this isn't very DRY
                    print(f"({type(self)}, {self.id}): unexpected {err=}, {type(err)=} when exporting")
            case DataExportType.NETCDF:
                raise NotImplementedError

    @property
    def poslist(self) -> list[np.ndarray]:
        return self.pos_list

    @property
    def timelist(self) -> list[datetime]:
        return self.date_list

    @property
    def distlist(self) -> list[np.float64]:
        return self.dist_list

    @property
    def consumed(self) -> bool:
        return self._is_consumed

    # These are named slightly differently to prevent ambiguity.

    @property
    def start_time(self) -> datetime:
        """Returns the start time if defined; otherwise, returns first day in the data."""
        if self.start_day == None:
            if len(self.date_list) >= 2 and self.consumed:
                return self.date_list[0]
            else:
                raise UnfinishedSimulatorError("Simulator must be consumed first")       
        else:
            return self.start_day

    @property
    def end_time(self) -> datetime:
        """Returns the end time if defined; otherwise, returns last day in the data."""
        if self.end_day == None:
            if len(self.date_list) >= 2 and self.consumed:
                return self.date_list[-1]
            else:
                raise UnfinishedSimulatorError("Simulator must be consumed first")       
        else:
            return self.end_day

    @property
    def start_pos(self) -> np.ndarray:
        """Returns the first position from the simulation data safely."""
        if len(self.pos_list) >= 2 and self.consumed:
            return self.pos_list[0]
        else:
            raise UnfinishedSimulatorError("Simulator must be consumed first")

    @property
    def end_pos(self) -> np.ndarray:
        """Returns the first position from the simulation data safely."""
        if len(self.pos_list) >= 2 and self.consumed:
            return self.pos_list[-1]
        else:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
