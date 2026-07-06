import xarray as xr
import pyproj
import cartopy.io.shapereader as shpreader
from shapely.geometry import Point
from shapely.prepared import prep
from shapely.ops import unary_union

# TODO: not sure if these functions actually make more sense as
# a method on IceCoordinates or something like that.
# requires meditation on the OOP-y ness of this problem.

# TODO: make this a lookup table

# this is expensive, which is why it's a global object
_fwd = pyproj.Transformer.from_crs("EPSG:3408", "EPSG:4326", always_xy=True)
_inv = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3408", always_xy=True)

def meters_to_degrees(x: float, y: float) -> tuple[float, float]:
    """Convert EPSG:3408 meters into degrees in WGS84."""
    lon, lat = _fwd.transform(x, y)
    return (lat, lon)

def degrees_to_meters(lat: float, lon: float) -> tuple[float, float]:
    """Convert WGS84 degrees into meters in EPSG:3408."""
    x, y = _inv.transform(lon, lat)
    return (x, y)

# this is a cheap function since it's just indexing
def nearest_grid_point(ds: xr.Dataset, x: float, y: float) -> tuple[float, float]:
    """Find the grid cell nearest to two coordinates (in meters)."""
    x_snap = ds.x.sel(x=x, method="nearest").values.item()
    y_snap = ds.y.sel(y=y, method="nearest").values.item()
    return (x_snap, y_snap)

# TODO: make a land clip checker to see if we drift into landfast ice
# useful to have these globally defined since they're expensive to make,
# but really cheap to use. ~3sec comp-time
land_shp = shpreader.natural_earth(resolution='10m', category='physical', name='land')
land_geom = unary_union(list(shpreader.Reader(land_shp).geometries()))
land = prep(land_geom)

# this could be used for transformations, but it's cheaper to just directly lookup.
# lookup is O(n), the runtime cost of a transform is at least O(n^3)!
# also note that natural earth shapefiles are in EPSG:4326.
to_lonlat_transform = pyproj.Transformer.from_crs("EPSG:3408", "EPSG:4326", always_xy=True)

def is_land(x: float, y: float) -> bool:
    """Determines if the current coordinates are on land."""
    lon, lat = to_lonlat_transform.transform(x, y)
    return land.contains(Point(lon, lat))

# mmm. delicious syntactical sugar
def is_ocean(x: float, y: float) -> bool:
    """Determines if the current coordinates are in the ocean."""
    return not is_land(x, y)
