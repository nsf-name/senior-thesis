import xarray as xr
import matplotlib.pyplot as plt
import matplotlib as mpl
import cartopy.crs as ccrs

from enum import Enum, auto

# set default dpi globally
mpl.rcParams["figure.dpi"] = 800

def plot_basemap() -> plt.Axes:
    """Plot a base Arctic basemap that can then be mutated as needed."""
    # this is equivalent to EPSG:3408, I think
    # some bug exists in CartoPy's CRS rep where EPSG pole stuff is fucked
    # due to issues with determining proper bounds on them? out of scope.
    # https://github.com/SciTools/cartopy/issues/1911

    proj = ccrs.LambertAzimuthalEqualArea(central_longitude=0, central_latitude=90)
    _, ax = plt.subplots(subplot_kw={"projection": proj})
    # I don't think there's a case where we wouldn't want this
    ax.coastlines()
    return ax

class MapType(Enum):
    """Valid map plot types."""
    Y_VELOCITY = auto()
    X_VELOCITY = auto()
    VECTORS = auto()

def plot_quickmap(
    ax: plt.Axes, type: MapType, data: xr.Dataset, day: int = 0, **kwargs
) -> plt.Axes:
    """Plot a map of the whole Arctic at a specific day."""
    # this is equivalent to EPSG:3408, I think
    # some bug exists in CartoPy's CRS rep where EPSG pole stuff is fucked
    # due to issues with determining proper bounds on them? out of scope.
    # https://github.com/SciTools/cartopy/issues/1911
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

# TODO: make scattering really simple. to my knowledge
# that is basically just getting an array of points and putting them on.
# make a function which wraps plot_quickmap and adds them...
def plot_quickpoints(ax: plt.Axes, points: list, **kwargs) -> plt.Axes:
    """Plot a series of points on the map."""
    # **kwargs lets you pass forward args to the plotter.
    for dex in range(len(points)):
        ax.scatter(points[dex][0], points[dex][1], **kwargs)
    return ax

def plot_quickline(ax: plt.Axes, points: list, **kwargs) -> plt.Axes:
    """Plot a line from a series of points."""
    xs, ys = zip(*points)
    # special markers for the start and end
    ax.scatter(points[0][0], points[0][1], c="g")
    ax.scatter(points[-1][0], points[-1][1], c="r")
    # special marker for the North Pole
    # TODO: only plot this as needed, or split off
    ax.scatter(0, 0, marker="*", c="gold")
    ax.plot(xs, ys, **kwargs)
    return ax
