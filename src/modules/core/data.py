import xarray as xr
import pandas as pd
import numpy as np
from glob import glob
from typing import Callable
import datetime

from modules.core.icemodel import IceTrajectory
from modules.core.buoymodel import BuoyTrajectory
from modules.core import utilities

def load_sim_data() -> dict:
  """Returns the data for the simulator. Top-level function."""
  buoy_data = load_buoy_data()
  ice_data = load_ice_data()
  
  # split the buoys up by day
  splits = split_buoy(buoy_data, lambda a, b: (pd.Timestamp(b) - pd.Timestamp(a)) <= pd.Timedelta(days=1))
  
  buoy_sims = dict()
  for key in splits:
    for num in range(len(splits[key])):
      # TODO: need to add a saveID to both of these,
      # because right now two runs of the same buoy with .export() will clobber stuff.
      buoy_sim = BuoyTrajectory(coordinate_field=buoy_data,
                                date_list=splits[key][num],
                                id=key)
      ice_sim = IceTrajectory(velocity_field=ice_data, 
                              start=buoy_sim.start_pos,
                              start_day=utilities.datetime_to_julian(
                                buoy_sim.start_day
                                .astype('datetime64[s]')
                                .astype(datetime.datetime)
                              ),
                              end_day=utilities.datetime_to_julian(
                                buoy_sim.end_day   
                                .astype('datetime64[s]')
                                .astype(datetime.datetime)
                              ),
                              id=key)
      buoy_sims[f"{key}_{num}"] = (buoy_sim, ice_sim)
  return buoy_sims

def load_ice_data() -> xr.Dataset:
  """Returns the ice data."""
  return xr.open_mfdataset(
    sorted(glob("/Users/nsf/Documents/Datasets/icemotion/*.nc")),
    data_vars="all",
    combine="by_coords",
  )

def load_buoy_data() -> xr.Dataset:
  """Returns the buoy data."""
  # PHASE 1: load data into Pandas
  buoydata = []
  # NOTE: buoy number 300434060729230 needed fixing from 4015 -> 2015
  # change this to your own path if you work on this
  for filename in sorted(
      glob("/Users/nsf/Documents/Code/senior-thesis/src/buoy-data/*.dat")
  ):
    df = pd.read_csv(filename, sep=r"\s+", engine="python")
    buoydata.append(df)
    buoyframe = pd.concat(buoydata, axis=0, ignore_index=True)
  # PHASE 2: get into xarray
  xds = xr.Dataset.from_dataframe(buoyframe)
  xds["time"] = xr.DataArray(
    pd.to_datetime(
      {
        "year": xds["Year"].values,
        "month": 1,
        "day": 1,
      }
    )
    + pd.to_timedelta(xds["DOY"].values - 1, unit="D"),
    dims="index",
  )
  # slim down the data a bit before processing
  xds = xds.set_coords(names=['BuoyID', 'time'])
  xds = xds.drop_duplicates(dim='index', keep='first')
  # PHASE 3: back to Pandas (for a bit), then xarray again
  dfnew = xds[['Lat', 'Lon']].reset_index(['index']).to_dataframe()
  dfnew['date'] = dfnew['time'].dt.floor('D')
  daily = dfnew.groupby(['BuoyID', 'date'])[['Lat', 'Lon']].mean()
  daily.index.names = ['BuoyID', 'time']
  xds_daily = xr.Dataset.from_dataframe(daily)
  xds_daily.attrs={
    'title': 'International Arctic Buoy Data',
    'summary': 'Data collected from buoys posted in the Arctic (daily mean).',
  }
  return xds_daily

# TODO: for day in buoy, get every non-NaN streak, organize in a list.
def split_runs(items: np.ndarray, pred: Callable) -> list:
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

# TODO: iter over buoys, take streams and assign them to a dict by buoy as key
def split_buoy(buoys: xr.Dataset, pred: Callable) -> dict:
  """Sort all buoys into a dictionary by BuoyID, after calling split_runs(buoys.items, pred) on them."""
  return {k: split_runs(v.dropna(dim='time', how='all', subset=['Lat', 'Lon']).time.values, pred)
          for k, v in buoys.groupby('BuoyID')}
