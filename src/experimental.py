import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium", app_title="")


@app.cell
def _():
    # libraries that exist that I want to use frequently
    import xarray as xr
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import cartopy.crs as ccrs
    import marimo as mo
    import numpy as np
    # standard library things
    from glob import glob
    from enum import Enum, auto
    from typing import NamedTuple
    from dataclasses import dataclass, field
    # typing nonsense
    from typing import Protocol, assert_never

    # libraries for the shape reader
    import cartopy.io.shapereader as shpreader
    from shapely.geometry import Point
    from shapely.prepared import prep
    from shapely.ops import unary_union
    import pyproj
    import cftime

    return (
        Enum,
        Point,
        auto,
        ccrs,
        cftime,
        dataclass,
        glob,
        mo,
        mpl,
        np,
        plt,
        prep,
        pyproj,
        shpreader,
        unary_union,
        xr,
    )


@app.cell
def _(glob, xr):
    # open all the datasets in one set
    data = xr.open_mfdataset(sorted(glob("/Users/nsf/Documents/Datasets/icemotion/*.nc")), data_vars='all', combine='by_coords')
    return (data,)


@app.cell
def _(data):
    data.time.encoding.get('calendar')
    return


@app.cell
def _(cftime, data):
    data.sel(time=slice(cftime.DatetimeJulian(2000,1,1), cftime.DatetimeJulian(2020,1,1)))
    return


@app.cell
def _(data):
    # somehow this works?!
    data.sel(time=slice("2000-01-01", "2020-01-01"))
    return


@app.cell
def _(data):
    # number of days in the time period
    len(data.sel(time=slice("2000-01-01", "2020-01-01")).time)
    return


@app.cell
def _(ccrs, mpl, plt, xr):
    mpl.rcParams['figure.dpi'] = 800
    ds = xr.open_dataset("/Users/nsf/Documents/Datasets/icemotion/icemotion_daily_nh_25km_20160101_20161231_v4.1.nc")
    var = ds.isel(time=0)
    u = ds["u"].isel(time=0)
    v = ds["v"].isel(time=0)

    # this is equivalent to EPSG:3408, I think
    # some bug exists in CartoPy's CRS rep where EPSG pole stuff is fucked 
    # due to issues with determining proper bounds on them? out of scope.
    # https://github.com/SciTools/cartopy/issues/1911
    proj = ccrs.LambertAzimuthalEqualArea(central_longitude=0, central_latitude=90)

    fig, ax = plt.subplots(subplot_kw={"projection": proj})
    stride = 8  # tune to get it al dente (just right)
    ax.quiver(
        var.x.values[::stride],
        var.y.values[::stride],
        u.values[::stride, ::stride],
        v.values[::stride, ::stride],
        transform=proj,
    )
    ax.coastlines()
    plt.show()
    return ds, proj


@app.cell
def _(ds, plt, proj):
    just_u = ds["u"].isel(time=0)
    _fig, _ax = plt.subplots(subplot_kw={"projection": proj})
    just_u.plot(ax=_ax, transform=proj, x="x", y="y", add_colorbar=True)
    _ax.coastlines()
    plt.show()
    return


@app.cell
def _(ds, plt, proj):
    just_v = ds["v"].isel(time=0)
    _fig, _ax = plt.subplots(subplot_kw={"projection": proj})
    just_v.plot(ax=_ax, transform=proj, x="x", y="y", add_colorbar=True)
    _ax.coastlines()
    plt.show()
    return


@app.cell
def _(Enum, auto, ccrs, ds, plt, proj, pyproj, xr):
    # some helper functions to try and automate the processes

    # TODO: would be cool to add a saving mechanism to this,
    # but I'm lazy and will do it later when I need it

    # TODO: better to compose on plt.Axes, since that's the only mutator
    # in the base matplotlib types.
    def plot_basemap() -> plt.Axes:
        """Generates a base Arctic basemap that can then be mutated as needed."""
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
        Y_VELOCITY = auto()
        X_VELOCITY = auto()
        VECTORS = auto()

    def plot_quickmap(ax: plt.Axes, type: MapType, data: xr.Dataset, day: int=0, **kwargs) -> plt.Axes:
        """A tool for quickly plotting a map of the whole Arctic at a specific day (default first day)."""
        match type:
            case MapType.Y_VELOCITY:
                just_v = ds["v"].isel(time=day)
                just_v.plot(ax=ax, transform=proj, x="x", y="y", add_colorbar=True, **kwargs)
            case MapType.X_VELOCITY:
                just_u = ds["u"].isel(time=day)
                just_u.plot(ax=ax, transform=proj, x="x", y="y", add_colorbar=True, **kwargs)
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
                    **kwargs
                )
        return ax

    # TODO: make scattering really simple. to my knowledge
    # that is basically just getting an array of points and putting them on.
    # make a function which wraps plot_quickmap and adds them...    
    def plot_quickpoints(ax: plt.Axes, points: list, **kwargs) -> plt.Axes:
        """A tool for quickly adding scatter points to a map without thinking too hard."""
        # **kwargs lets you pass forward args to the plotter.
        for dex in range(len(points)):
            ax.scatter(points[dex][0], points[dex][1], **kwargs)
        return ax

    def plot_quickline(ax: plt.Axes, points: list, **kwargs) -> plt.Axes:
        xs, ys = zip(*points)
        ax.scatter(points[0][0], points[0][1], c='g')
        ax.scatter(points[-1][0], points[-1][1], c='r')
        ax.scatter(0, 0, marker='*',c='gold')
        ax.plot(xs, ys, **kwargs)
        return ax

    # TODO: write a tool that converts latitude to longitude and vice versa
    # this should be as simple as an index into the dataset, then a conversion

    # TODO: not sure if these functions actually make more sense as a method on IceCoordinates
    # or something like that. requires meditation on the OOP-y ness of this problem.

    # this is expensive, which is why it's a global object
    _fwd = pyproj.Transformer.from_crs("EPSG:3408", "EPSG:4326", always_xy=True)
    _inv = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3408", always_xy=True)

    def meters_to_degrees(x: float, y: float) -> tuple[float, float]:
        lon, lat = _fwd.transform(x, y)
        return (lat, lon)

    def degrees_to_meters(lat: float, lon: float) -> tuple[float, float]:
        x, y = _inv.transform(lon, lat)
        return (x, y)

    # this is a cheap function since it's just indexing
    def nearest_grid_point(ds: xr.Dataset, x: float, y: float) -> tuple[float, float]:
        x_snap = ds.x.sel(x=x, method='nearest').values.item()
        y_snap = ds.y.sel(y=y, method='nearest').values.item()
        return (x_snap, y_snap)


    return (
        MapType,
        degrees_to_meters,
        meters_to_degrees,
        plot_basemap,
        plot_quickline,
        plot_quickmap,
    )


@app.cell
def _(dataclass, np, xr):
    # TODO: we want to represent the bounding coords of our system.
    # it should be impossible to move a buoy outside of the ice, or something like that,
    # so the goal is to have the coordinate system handle this.
    class IceCoordinates:
        def __init__(self, lat: float, lon: float):
            # so we only use the getters and setters
            self._lat = lat
            self._lon = lon

        @property
        def lat(self) -> float:
            return self._lat

        @property
        def lon(self) -> float:
            return self._lon

        @lat.setter
        def lat(self, value):
            # TODO: enforce checks
            self._lat = value

        @lon.setter 
        def lon(self, value):
            # TODO: enforce checks
            self._lon = value

    # TODO: make a class for sea ice data years, with an iter method
    # that always returns the next day's coordinates given a set of
    # starting coordinates. makes the parallel execution very elegant.
    @dataclass
    class IceTrajectory:
        # in a @dataclass, these are instance vars, not class vars.
        velocity_field: xr.Dataset
        start: tuple[float, float]
        start_day: int

        def __post_init__(self):
            self._pos = self.start
            self._t = self.start_day
            self._poslist = []

        # the default one is too verbose
        def __repr__(self):
            return self._repr()

        # easier to just have one representation
        __str__ = __repr__

        def __iter__(self):
            return self

        def __next__(self) -> tuple[float, float]:
            # TODO: we may never need more than one year, but if we do,
            # this is eventually going to be a problem.
            if self._t >= 365:
                raise StopIteration
            #print(f"DAY {self._t + 1}:")
            vector = self._lookup_vector(self._pos, self._t)
            self._pos = self._pos + np.array(vector)
            self._t += 1
            self._poslist.append(self._pos)
            return tuple(self._pos)

        def _repr(self):
            return f"IceTrajectory(start: {self.start}, pos: {self._pos})"

        def _lookup_vector(self, pos, t) -> tuple[float, float]:
            vector = self.velocity_field.isel(time=t).sel(x=pos[0], y=pos[1], method='nearest')
            # conversion: (1 cm/s x 86,400 s/day) / 100cm/m = 864 m/day
            u = np.nan_to_num(vector.u.values.item() * 864)
            v = np.nan_to_num(vector.v.values.item() * 864)
            #print(f"vector pulls the object: ({u}, {v})")
            return (u, v)

        # getter for pos to avoid mutation
        @property
        def pos(self):
            return self._pos

        @property
        def poslist(self):
            return self._poslist

        # subclasses should implement this!
        def plot(self):
            raise NotImplementedError

    # TODO: make a class with methods that represents our buoy,
    # so that we can keep track of its state. we need methods for rendering it,
    # for manipulating it, etc. this probably needs more stuff.
    class Buoy: 
        def __init__(self, icetraj: IceTrajectory, color: str):
            self._icetraj = icetraj
            self.color = color

        def __repr__(self):
            return self._repr()

        # easier to just have one representation
        __str__ = __repr__

        def _repr(self):
            return f"Buoy(start: {self._icetraj.start}, pos: {self._icetraj.pos}, color: {self.color})"

        @property
        def pos(self):
            return self._icetraj.pos

        # TODO: implement this, depends on getting a scatter plot tool
        def plot(self):
            return NotImplementedError

    # TODO: then use joblib for MASSIVE parallel execution of stuff.
    # Monte Carlo this. we spawn in millions of possible locations,
    # and let the data speak for itself as to where ice tracks go.
    return Buoy, IceTrajectory


@app.cell
def _(Point, prep, pyproj, shpreader, unary_union):
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

    return


@app.cell
def _(MapType, ds, plot_basemap, plot_quickmap):
    testthing = plot_quickmap(plot_basemap(), MapType.VECTORS, ds, day=365)
    testthing
    return


@app.cell
def _():
    #test = IceTrajectory(ds, start=degrees_to_meters(80, -178), start_day=0)
    #for x in test:
    #    pass
        #print(test)
        #print(f"coordinates: {meters_to_degrees(test.pos[0], test.pos[1])}")

    #print(test.poslist)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Experimental Stuff
    This notebook's work will obviously not end up in the final version of the code verbatim. It's just for testing.

    TODO:
    - handle more than one year of runtime, by autoloading the next year and restarting the count
    - use NSIDC dataset for coordinate calculations to lower runtime cost
    - find a nicer way to move the maps around, and a way to export as GeoJSON (for visualization elsewhere)
    - Monte Carlo method: find some way to drop a bunch of buoys and let them run in parallel
    - compare against real Arctic buoy datasets (probably next week)
    - get more NSIDC datasets for trackers to read from
    """)
    return


@app.cell
def _():
    # default extents.
    # these cover most of the arctic ocean
    lon_min = -180
    lon_max = 180
    lat_min = 70
    lat_max = 90
    return


@app.cell
def _(mo):
    lat_min_slider = mo.ui.slider(start=-90, stop=90, label="Lat Min", value=70)
    lat_max_slider = mo.ui.slider(start=-90, stop=90, label="Lat Max", value=90)
    lon_min_slider = mo.ui.slider(start=-180, stop=180, label="Lon Min", value=-180)
    lon_max_slider = mo.ui.slider(start=-180, stop=180, label="Lon Max", value=180)
    buoy_lat_number = mo.ui.number(start=-90, stop=90, label="Buoy Lat")
    buoy_lon_number = mo.ui.number(start=-180, stop=180, label="Buoy Lon")
    buoy_run_button = mo.ui.run_button(label="Deploy the Buoy!")
    mo.vstack([
        mo.hstack([lat_min_slider, lat_max_slider, lon_min_slider, lon_max_slider]),
        mo.hstack([buoy_lat_number, buoy_lon_number, buoy_run_button])
    ])
    return (
        buoy_lat_number,
        buoy_lon_number,
        buoy_run_button,
        lat_max_slider,
        lat_min_slider,
        lon_max_slider,
        lon_min_slider,
    )


@app.cell
def _(
    IceTrajectory,
    buoy_lat_number,
    buoy_lon_number,
    buoy_run_button,
    ccrs,
    degrees_to_meters,
    ds,
    lat_max_slider,
    lat_min_slider,
    lon_max_slider,
    lon_min_slider,
    plot_basemap,
    plot_quickline,
):
    # creates a weak reference needed to rerun this cell by pushing button
    buoy_run_button.value

    buoy = IceTrajectory(ds, start=degrees_to_meters(buoy_lat_number.value, buoy_lon_number.value), start_day=0)
    for x in buoy:
        pass

    base = plot_quickline(plot_basemap(), buoy.poslist)
    base.set_extent([lon_min_slider.value, lon_max_slider.value, lat_min_slider.value, lat_max_slider.value],
                    crs=ccrs.PlateCarree())

    # All data below are from 2016 unless the loaded dataset was changed.
    base
    return (buoy,)


@app.cell
def _(mo):
    vector_day_number = mo.ui.number(start=0, stop=365, label="Vectors for a Day")
    vector_day_number
    return (vector_day_number,)


@app.cell
def _(MapType, ds, plot_basemap, plot_quickmap, vector_day_number):
    testthingamajig = plot_quickmap(plot_basemap(), MapType.VECTORS, ds, day=vector_day_number.value)
    testthingamajig
    return


@app.cell
def _(buoy):
    print(len(buoy.poslist))
    for _y in range(len(buoy.poslist)):
        print(f"{buoy.poslist[_y][0]}, {buoy.poslist[_y][1]}")
    return


@app.cell
def _(Buoy, buoy, meters_to_degrees):
    test_buoy = Buoy(buoy, "blue")
    print(test_buoy.pos)
    print(test_buoy)
    print(meters_to_degrees(test_buoy.pos[0], test_buoy.pos[1]))
    return


@app.cell
def _(ds):
    ds.latitude.sel(x=0, y=0, method='nearest').values
    return


@app.cell
def _(ds):
    ds.longitude.sel(x=0, y=0, method='nearest').values
    return


@app.cell
def _(ds):
    ds.isel(time=0).sel(x=0, y=0, method='nearest').u.values
    return


@app.cell
def _(meters_to_degrees):
    meters_to_degrees(400000, -12800)
    return


@app.cell
def _(degrees_to_meters):
    degrees_to_meters(86.4004090896884, 88.16716049405794)
    return


@app.cell
def _(ds):
    ds.longitude.sel(x=1000000, y=0, method='nearest').values
    return


@app.cell
def _(ds):
    ds.longitude.sel(x=1000000, y=-1000000, method='nearest').values
    return


@app.cell
def _(ds):
    ds.u.sel(x=0, y=0, method='nearest').values
    return


@app.cell
def _(ds):
    for _x in range(365):
        print(ds.u.isel(time=_x).sel(x=0, y=0).values, ds.v.isel(time=_x).sel(x=0, y=0).values)
    return


@app.cell
def _(ds):
    ds
    return


if __name__ == "__main__":
    app.run()
