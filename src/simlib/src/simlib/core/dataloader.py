import pathlib
from glob import glob

import xarray as xr


def load_ice_data(path: pathlib.Path) -> xr.Dataset:
    """Sets up the ice data."""
    xds = xr.open_mfdataset(
        sorted(glob(str(path) + "/*.nc")),
        data_vars="all",
        combine="by_coords",
    )
    # correct from Julian to Gregorian to make the math easier
    # we're ignoring all the errors because they're very small relatively
    xds["time"] = xds.indexes["time"].to_datetimeindex(unsafe=True, time_unit="ns")
    return xds
