import xarray as xr
import numpy as np
import geopandas as gpd
from shapely.geometry import Point

from dataclasses import dataclass

from modules.core import utilities

# BuoyTrajectory expects one list of date objects, and nothing else.
@dataclass
class BuoyTrajectory:
    # in a @dataclass, these are instance vars, not class vars.
    coordinate_field: xr.Dataset
    date_list: list
    id: int

    def __post_init__(self):
        self._pos = self._lookup_vector(self.date_list[0])
        # why not just self._pos? because self._pos can mutate.
        self._start_pos = self._pos 
        self._start_day = self.date_list[0]
        self._end_day = self.date_list[-1]
        # in this implementation, self._t is an index into self.date_list
        self._t = 0
        self._poslist = []

    # the default one is too verbose
    def __repr__(self):
        return self._repr()

    # easier to just have one representation
    __str__ = __repr__

    def __iter__(self):
        return self

    def __next__(self) -> tuple[float, float]:
        if self._t >= len(self.date_list):
            raise StopIteration
        current_day = self.date_list[self._t]
        #print(f"DAY {current_day}:")
        self._pos = self._lookup_vector(self.date_list[self._t])
        self._poslist.append(np.array(self._pos))
        self._t += 1
        #print(f"COORDS: {self._pos}")
        return tuple(self._pos)

    def _repr(self):
        return f"BuoyTrajectory(id: {self.id}, start: {self._start_day}, end: {self._end_day}, pos: {self._pos})"

    def _lookup_vector(self, t) -> tuple[float, float]:
        value = self.coordinate_field.sel(BuoyID=self.id, time=t)
        return (value.Lat.item(), value.Lon.item())

    def export(self):
        # TODO: what CRS are we in?
        # assuming EPSG:4326 (WGS84) until further notice.
        xs, ys = zip(*self._poslist)
        record = dict(x=xs, y=ys)
        gpd.GeoDataFrame(
            # for more types of data, add more entries to this dict
            {'geometry': gpd.gpd.points_from_xy(
                record['x'], record['y'], crs="EPSG:4326"
            )}
        ).to_file(f"buoytraj_{self.id}.geojson", driver='GeoJSON')

    # getter for pos to avoid mutation
    @property
    def pos(self):
        return self._pos

    @property
    def poslist(self):
        return self._poslist

    @property
    def timlist(self):
        return self.date_list

    # unlike IceTrajectory, we need to know where we start since we only have
    # a list of dates, and it's expensive to iterate.
    @property
    def start_pos(self):
        return self._start_pos
    
    @property
    def start_day(self):
        return self._start_day

    @property
    def end_day(self):
        return self._end_day
