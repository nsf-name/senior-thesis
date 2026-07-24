from enum import Enum, auto
from typing import Callable, TypeVar

# TODO: banned until I need them for speed reasons
#import cartopy.io.shapereader as shpreader
#import pyproj
#from shapely.geometry import Point
#from shapely.ops import unary_union
#from shapely.prepared import prep
import xarray as xr

# defines a generic function return
T = TypeVar('T')

class DataExportType(Enum):
    """Valid simulator data export types."""
    CSV = auto()
    GEOJSON = auto()
    # TODO: go back and implement later, might be useful
    NETCDF = auto()

class UnpreparedSimulatorError(Exception):
    """Error if the simulator isn't done setting up at request time."""
    def __init__(self, message):            
        super().__init__(message)

class UnfinishedSimulatorError(Exception):
    """Error if the simulator isn't done executing at request time."""
    def __init__(self, message):            
        super().__init__(message)

class MissingDatesError(Exception):
    """Error if the simulator is missing dates needed to handle the request."""
    def __init__(self, message):            
        super().__init__(message)

def maybe_apply(pred: bool, func: Callable[[], T]) -> T | None:
    """Evaluate func if pred is True else None."""
    return func() if pred else None

# this is a cheap function since it's just indexing
def nearest_grid_point(ds: xr.Dataset, x: float, y: float) -> tuple[float, float]:
    """Find the grid cell nearest to two coordinates (in meters)."""
    x_snap = ds.x.sel(x=x, method="nearest").values.item()
    y_snap = ds.y.sel(y=y, method="nearest").values.item()
    return (x_snap, y_snap)

# TODO: make a land clip checker to see if we drift into landfast ice
# useful to have these globally defined since they're expensive to make,
# but really cheap to use. ~3sec comp-time

# TODO: crazy expensive and banned until I need them
#land_shp = shpreader.natural_earth(resolution='10m', category='physical', name='land')
#land_geom = unary_union(list(shpreader.Reader(land_shp).geometries()))
#land = prep(land_geom)

# this could be used for transformations, but it's cheaper to just directly lookup.
# lookup is O(n), the runtime cost of a transform is at least O(n^3)!
# also note that natural earth shapefiles are in EPSG:4326.

# TODO: crazy expensive and banned until I need them
#to_lonlat_transform = pyproj.Transformer.from_crs("EPSG:3408", "EPSG:4326", always_xy=True)

def is_land(x: float, y: float) -> bool:
    """Determines if the current coordinates are on land."""
    lon, lat = to_lonlat_transform.transform(x, y)
    return land.contains(Point(lon, lat))

# mmm. delicious syntactical sugar
def is_ocean(x: float, y: float) -> bool:
    """Determines if the current coordinates are in the ocean."""
    return not is_land(x, y)
