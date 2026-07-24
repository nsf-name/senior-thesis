from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import xarray as xr

from simlib.tools.logging import conf_interactive_logger, LogLevel
from simlib.tools.utilities import DataExportType, UnfinishedSimulatorError

@dataclass(kw_only=True)
class Trajectory(ABC):
    """Base class for all simulator trajectory objects.

    Attributes:
        dataset: Source xarray dataset for this trajectory.
        id: Unique trajectory identifier.
        start_day: First day of simulation window. If None, uses start of dataset range.
        end_day: Last day of simulation window. If None, uses end of dataset.
        pos_list: Accumulated position arrays, one per timestep. For external capture.
        date_list: Timestamps corresponding to each entry in pos_list.
        dist_list: Haversine distances between positions (len = len(pos_list) - 1).
        loglevel: The amount of logs to be emitted. If None, uses LogLevel.WARNING.
        timestep: Duration between simulation steps. Not stored as a field (InitVar).
    """
    dataset: xr.Dataset
    # TODO: this should be a string since that's what it is in the cleaned buoys
    id: int
    start_day: Optional[datetime] = None
    end_day: Optional[datetime] = None
    pos_list: Optional[list[np.ndarray]] = field(default_factory=list)
    date_list: Optional[list[np.ndarray]] = field(default_factory=list)
    dist_list: Optional[list[np.ndarray]] = field(default_factory=list)
    loglevel: Optional[LogLevel] = None
    timestep: InitVar[Optional[timedelta]] = timedelta(days=1)

    def __post_init__(self, timestep):
        # this affects downstream logic with stepping.
        # default behavior is to just increment by each timestamp; a specific timedelta
        # should advance to the nearest date that fits the time stepping code.

        # TODO: that's not what this ACTUALLY does in practice.
        if timestep is not None:
            self.timestep = timestep
 
        self._t = self.start_day
        self._is_consumed = False
        self._pos = np.zeros(2, dtype=np.float64)

        self._filename = f"{self.id}-{type(self).__name__}"
        if self.loglevel is not None:
            self._log = conf_interactive_logger(self._filename, self.loglevel)
        else:
            self._log = conf_interactive_logger(self._filename, LogLevel.WARNING)

    def __repr__(self) -> str:
        return f"{type(self).__name__}[{self.id}](consumed: {self.consumed})"

    __str__ = __repr__
 
    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self) -> tuple[np.ndarray]:
        ...
    
    def __len__(self) -> int:
        if self.pos_list is not None:
            return len(self.pos_list)
        return 0

    def runsim(self):
        """Exhaust the internal iterator."""
        for _ in self:
            pass
        return (self.pos_list, self.date_list)

    def step(self):
        """Step the simulator by exactly one tick."""
        return next(self)

    def export(self, type: DataExportType, path: Path):
        """Export the simulator data to the specified type."""
        match type:
            case DataExportType.GEOJSON:
                xs, ys = zip(*self.poslist)
                record = dict(x=xs, y=ys)
                try:
                    import geopandas as gpd
                    gpd.GeoDataFrame(
                        # for more types of data, add more entries to this dict
                        {'geometry': gpd.gpd.points_from_xy(
                            record['x'], record['y'], crs="EPSG:4326"
                        )}
                    ).to_file(path / f"{self._filename}.geojson", driver='GeoJSON')
                except Exception as err:
                    self._log.exception(f"unexpected {err=} on export")
            case DataExportType.CSV:
                # timestamp list and the position list are always the same length
                zipper = [(*pos, t, self.id) for pos, t in zip(self.poslist, self.timelist)]
                try:
                    import pandas as pd
                    with open(path / self._filename, 'w') as f:
                         pd.DataFrame(
                             zipper,
                             columns=["lat", "lon", "time", "id"]
                         ).to_csv(f)
                except Exception as err:
                    self._log.exception(f"unexpected {err=} on export")
            case DataExportType.NETCDF:
                raise NotImplementedError

    @property
    def consumed(self) -> bool:
        return self._is_consumed

    @property
    def poslist(self) -> list[np.ndarray]:
        """Returns the list of positions (in (lat, lon) coordinates)."""
        if not self.consumed:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
        return self.pos_list

    @property
    def timelist(self) -> list[datetime]:
        """Returns the list of times (in datetimes) positions were visited."""
        if not self.consumed:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
        return self.date_list

    @property
    def distlist(self) -> list[np.float64]:
        """Returns a list of distances (in meters) between pairs of positions."""
        if not self.consumed:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
        return self.dist_list

    @property
    def start_time(self) -> datetime:
        """Returns the start time if defined; otherwise, returns first day in the data."""
        if self.start_day == None:
            if len(self.timelist) >= 2:
                return self.timelist[0]
            else:
                raise UnfinishedSimulatorError("Simulator must be consumed first")       
        else:
            return self.start_day

    @property
    def end_time(self) -> datetime:
        """Returns the end time if defined; otherwise, returns last day in the data."""
        if self.end_day == None:
            if len(self.timelist) >= 2:
                return self.timelist[-1]
            else:
                raise UnfinishedSimulatorError("Simulator must be consumed first")       
        else:
            return self.end_day

    @property
    def start_pos(self) -> np.ndarray:
        """Returns the first position from the simulation data safely."""
        if len(self.poslist) >= 2:
            return self.poslist[0]
        else:
            raise UnfinishedSimulatorError("Simulator must be consumed first")

    @property
    def end_pos(self) -> np.ndarray:
        """Returns the first position from the simulation data safely."""
        if len(self.poslist) >= 2:
            return self.poslist[-1]
        else:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
