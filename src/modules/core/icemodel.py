import xarray as xr
import numpy as np
import cftime
import geopandas as gpd
from shapely.geometry import Point

from dataclasses import dataclass
from datetime import timedelta

from modules.core import utilities

# TODO: make a class for sea ice data years, with an iter method
# that always returns the next day's coordinates given a set of
# starting coordinates. makes the parallel execution very elegant.
@dataclass
class IceTrajectory:
    # in a @dataclass, these are instance vars, not class vars.
    velocity_field: xr.Dataset
    start: tuple[float, float]
    start_day: cftime.DatetimeJulian
    end_day: cftime.DatetimeJulian
    id: int

    def __post_init__(self):
        self._pos = self.start
        self._t = self.start_day
        self._poslist = []
        self._timlist = []

    # the default one is too verbose
    def __repr__(self):
        return self._repr()

    # easier to just have one representation
    __str__ = __repr__

    def __iter__(self):
        return self

    def __next__(self) -> tuple[float, float]:
        if self._t > self.end_day:
            raise StopIteration
        # our vector dataset contains no entries beyond this,
        # so iteration beyond this point makes no sense
        if self._t >= cftime.DatetimeJulian(2025, 1, 1, calendar="julian"):
            raise StopIteration
        #print(f"DAY {self._t}:")
        vector = self._lookup_vector(self._pos, self._t)
        self._pos = self._pos + np.array(vector)
        self._t += timedelta(days=1)
        # convert before we use it
        conv = utilities.meters_to_degrees(self._pos[0], self._pos[1])
        self._timlist.append(self._t)
        self._poslist.append(np.array(conv))
        #print(f"COORDS: {conv}:")
        return tuple(self._pos)

    def _repr(self):
        conv = utilities.meters_to_degrees(self._pos[0], self._pos[1])
        return f"IceTrajectory(id: {self.id}, start: {self.start_day}, end: {self.end_day}, pos: {conv})"

    def _lookup_vector(self, pos, t) -> tuple[float, float]:
        vector = self.velocity_field.sel(x=pos[0], y=pos[1], time=t, method="nearest")
        # conversion: (1 cm/s x 86,400 s/day) / 100cm/m = 864 m/day
        u = np.nan_to_num(vector.u.values.item() * 864)
        v = np.nan_to_num(vector.v.values.item() * 864)
        # print(f"vector pulls the object: ({u}, {v})")
        return (u, v)

    def export(self):
        xs, ys = zip(*self._poslist)
        record = dict(x=xs, y=ys)
        gpd.GeoDataFrame(
            # for more types of data, add more entries to this dict
            {
                "geometry": gpd.gpd.points_from_xy(
                    record["x"], record["y"], crs="EPSG:3408"
                )
            }
        ).to_file(f"icetraj_{self.id}.geojson", driver="GeoJSON")

    # getter for pos to avoid mutation
    @property
    def pos(self):
        return self._pos

    @property
    def poslist(self):
        return self._poslist

    @property
    def timlist(self):
        return self._timlist
