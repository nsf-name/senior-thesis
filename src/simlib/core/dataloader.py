import xarray as xr
import pandas as pd

from glob import glob
from enum import Enum, auto

# TODO: make it reproducible. this is all so grotesquely specific to my machine...

class SimDataType(Enum):
    """Valid simulation data types."""
    BUOY = auto()
    ICE = auto()

def load_buoy_data() -> xr.Dataset:
    xds = xr.open_dataset(
        "/Users/nsf/Documents/Code/senior-thesis/src/buoy.nc",
        engine="h5netcdf"
    )
    xds = xds.set_index(index=['BuoyID', 'time'])
    return xds

def load_ice_data() -> xr.Dataset:
  """Sets up the ice data."""
  xds = xr.open_mfdataset(
    sorted(glob("/Users/nsf/Documents/Datasets/icemotion/*.nc")),
    data_vars="all",
    combine="by_coords",
  )
  # non-standard calendar warning off, plus literally who cares about precision, we're working in days and weeks here
  xds["time"] = xds.indexes["time"].to_datetimeindex(unsafe=True, time_unit='ns')
  return xds

def load_grid_data() -> xr.Dataset:
    xds = xr.open_dataset(
        "/Users/nsf/Documents/Code/senior-thesis/src/NSIDC0772_LatLon_EASE_N25km_v1.1.nc",
        engine="h5netcdf"
    )
    return xds
