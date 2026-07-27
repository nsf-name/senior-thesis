from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from logging import Logger

import polars as pl
from simlib.tools.logging import LogLevel, conf_interactive_logger
from simlib.tools.utilities import DataExportType, UnfinishedSimulatorError


@dataclass(kw_only=True)
class Trajectory(ABC):
    """Base class for all simulator trajectory objects.

    Attributes:
        id: Unique trajectory identifier.
        start_day: First day of simulation window. If None, uses start of dataset range.
        end_day: Last day of simulation window. If None, uses end of dataset.
        pos_list: Accumulated position arrays, one per timestep. For external capture.
        date_list: Timestamps corresponding to each entry in pos_list. For external capture.
        dist_list: Haversine distances between positions. For external capture.
        loglevel: The amount of logs to be emitted. If None, uses LogLevel.WARNING.
        logger: Log output. If None, creates one for interactive use.
        timestep: Duration between simulation steps. If None, iterates through everything.
    """

    id: str
    start_day: Optional[datetime] = None
    end_day: Optional[datetime] = None
    pos_list: list[tuple[float, float]] = field(default_factory=list)
    date_list: list[datetime] = field(default_factory=list)
    dist_list: list[float] = field(default_factory=list)
    loglevel: Optional[LogLevel] = None
    logger: Optional[Logger] = None
    timestep: Optional[timedelta] = None

    def __post_init__(self):
        self._t = self.start_day
        self._is_consumed = False

        self._filename = f"{self.id}-{type(self).__name__}"
        if self.loglevel is None:
            self.loglevel = LogLevel.WARNING

        if self.logger is None:
            self._log = conf_interactive_logger(self._filename, self.loglevel)
        else:
            self._log = self.logger

    def __repr__(self) -> str:
        return f"{type(self).__name__}[{self.id}](consumed: {self.consumed})"

    __str__ = __repr__

    @abstractmethod
    def __len__(self) -> int: ...

    def export(self, type: DataExportType, path: Path):
        """Export the simulator data to the specified type."""
        match type:
            case DataExportType.CSV:
                try:
                    lats, lons = zip(*self.poslist)
                    # TODO: export distlist
                    pl.DataFrame(
                        {
                            "lat": list(lats),
                            "lon": list(lons),
                            "time": self.timelist,
                            "id": self.id,
                        },
                        orient="row",
                    ).write_csv(path)
                except Exception as err:
                    self._log.exception(f"unexpected {err=} on export")
            case DataExportType.NETCDF:
                raise NotImplementedError

    @abstractmethod
    def plot(self): ...

    @property
    def consumed(self) -> bool:
        return self._is_consumed

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def poslist(self) -> list[tuple[float, float]]:
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
    def distlist(self) -> list[float]:
        """Returns a list of distances (in meters) between pairs of positions."""
        if not self.consumed:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
        return self.dist_list

    @property
    def poshead(self) -> tuple[float, float]:
        """Peek the first value of the poslist."""
        if not self.consumed:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
        return self.pos_list[0]

    @property
    def postail(self) -> tuple[float, float]:
        """Peek the last value of the poslist."""
        if not self.consumed:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
        return self.pos_list[-1]

    @property
    def timehead(self) -> datetime:
        """Peek the first value of the timelist."""
        if not self.consumed:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
        return self.date_list[0]

    @property
    def timetail(self) -> datetime:
        """Peek the last value of the timelist."""
        if not self.consumed:
            raise UnfinishedSimulatorError("Simulator must be consumed first")
        return self.date_list[-1]
