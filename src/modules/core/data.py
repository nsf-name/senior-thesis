import xarray as xr
from glob import glob

# load the data
def load_data():
  return xr.open_mfdataset(
    sorted(glob("/Users/nsf/Documents/Datasets/icemotion/*.nc")),
    data_vars="all",
    combine="by_coords",
  )
