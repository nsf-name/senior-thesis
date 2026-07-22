import xarray as xr
import logging
import warnings
import matplotlib as mpl
# TODO: to prevent OOM situation, we need to .close() plots

# for noninteractive use
mpl.use('Agg')
# make the logs less annoying
logging.getLogger('matplotlib').setLevel(logging.ERROR)
warnings.filterwarnings('ignore', module='matplotlib')
warnings.filterwarnings('ignore', module='cartopy')

# now we can import the rest
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import cartopy.crs as ccrs
import cartopy

from enum import Enum, auto

# set default dpi globally
mpl.rcParams["figure.dpi"] = 800

class MapType(Enum):
    """Valid map plot types."""
    Y_VELOCITY = auto()
    X_VELOCITY = auto()
    VECTORS = auto()

def plot_basemap(title: str, 
                 subtitle: str, 
                 figsize: float = 8.0,
                 data_bounds: tuple[float, float, float, float] = None
                ) -> (plt.Plot, plt.Axes):
    """Plot a base Arctic basemap that can then be mutated as needed."""
    # this is equivalent to EPSG:3408, I think
    # some bug exists in CartoPy's CRS rep where EPSG pole stuff is fucked
    # due to issues with determining proper bounds on them? out of scope.
    # https://github.com/SciTools/cartopy/issues/1911

    proj = ccrs.LambertAzimuthalEqualArea(central_longitude=0, central_latitude=90)
    fig, ax = plt.subplots(
        figsize=(figsize, figsize),
        subplot_kw={"projection": proj},
    )
    if data_bounds is not None:
        lon_min, lon_max, lat_min, lat_max = data_bounds
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # coastlines, land, ocean, borders
    ax.coastlines(linewidth=0.8, color="#444444")
    ax.add_feature(cartopy.feature.OCEAN, color="#cde4f0", zorder=0)
    ax.add_feature(cartopy.feature.LAND,  color="#e8e0d5", zorder=1)
    ax.add_feature(cartopy.feature.BORDERS, linewidth=0.4, color="#888888", zorder=2)

    # TODO: gridlines

    # title, subtitle
    fig.text(
        0.5, 0.96, title,
        ha="center", va="top",
        fontsize=13, fontweight="bold", color="#1a1a1a",
    )
    fig.text(
        0.5, 0.92, subtitle,
        ha="center", va="top",
        fontsize=9, color="#555555", style="italic",
    )

    return (fig, ax)

def plot_quickline(ax: plt.Axes, points: list, **kwargs) -> plt.Axes:
    """Plot a line from a series of points."""
    xs, ys = zip(*points)  # xs is actually lats, ys is actually lons
    pc = ccrs.PlateCarree()
    ax.scatter(ys[0], xs[0], c="g", transform=pc, zorder=5)  # (lon, lat)
    ax.scatter(ys[-1], xs[-1], c="r", transform=pc, zorder=5)
    ax.plot(ys, xs, transform=pc, **kwargs)  # (lons, lats)
    return ax

# TODO: dead code, probably clip at some point
def plot_quickmap(
    ax: plt.Axes, type: MapType, data: xr.Dataset, day: int = 0, **kwargs
) -> plt.Axes:
    """Plot a map of the whole Arctic at a specific day."""
    proj = ccrs.LambertAzimuthalEqualArea(central_longitude=0, central_latitude=90)
    match type:
        case MapType.Y_VELOCITY:
            just_v = data["v"].isel(time=day)
            just_v.plot(
                ax=ax, transform=proj, x="x", y="y", add_colorbar=True, **kwargs
            )
        case MapType.X_VELOCITY:
            just_u = data["u"].isel(time=day)
            just_u.plot(
                ax=ax, transform=proj, x="x", y="y", add_colorbar=True, **kwargs
            )
        case MapType.VECTORS:
            var = data.isel(time=day)
            u = data["u"].isel(time=day)
            v = data["v"].isel(time=day)
            stride = 8  # tune to get it al dente (just right)
            ax.quiver(
                var.x.values[::stride],
                var.y.values[::stride],
                u.values[::stride, ::stride],
                v.values[::stride, ::stride],
                transform=proj,
                **kwargs,
            )
    return ax

