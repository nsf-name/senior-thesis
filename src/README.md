# Simulator Code
This code simulates buoy tracks. It uses inputs from the [International Arctic Buoy Programme](https://iabp.apl.uw.edu) and the [Polar Pathfinder Sea Ice Vectors](https://nsidc.org/data/nsidc-0116) datasets, which you will need to fetch yourself (they're not vendored with this code for copyright reasons). The helper scripts in `modules/extra` can do this for you, assuming you have your development environment set up right.

How does it work? There's a `Simulator` class which does all the setup for you once you've made an instance of it. Internally, the dataset is contained as one very large dictionary. The keys are a unique buoy ID run (as made unique by [this dataset](https://arcticdata.io/catalog/view/doi%3A10.18739%2FA2WS8HP1V)), and they contain a list with two objects: a `BuoyTrajectory` and an `IceTrajectory` (subclasses of the more general-purpose `Trajectory` superclass). The methods exposed on them allow for simulating and running experiments with the datasets. For more information, read the method docstrings and the code itself.

## Development / Running
First install `uv` by running `brew install uv` (or equivalent on your OS; if you have Rust, `cargo install uv` should work too). Then run:
```
uv sync
```
From there, it will download all Python dependencies (and Fortran ones, since `uv` uses binary wheels). Once that wraps up, run:
```
uv run simulator run
```
This will start the parallel executor, which runs all the buoys in a thread pool. You are encouraged to tweak the exact setup to your needs. For help, run `uv run simulator --help`; you can use the `-h` or `--help` flag on any subcommand.

## Performance?
Pretty good. I had initially considered [Parcels](https://docs.parcels-code.org/en/latest/) for this, but it had way too much overhead and complexity for my needs, so I'm rolling my own. This is way faster, although I didn't get far into my Parcels kernel-building to see for myself.  

Internally, the workload is executed per-key in the dictionary. It's mostly `IceTrajectory` that is slow because it actually has to do math. It can take a really long time on long runs, but assuming you set up the dataset cleanly, this should almost never happen. Most jobs should complete all non-plotting tasks within a couple of seconds.

When `Simulator` is created, it can take a long time to load all data and construct simulator objects, depending on the speed of your hard drive. I've considered implementing a caching feature to make it easier for debugging and reruns.

## Bugs?
Many, unfortunately. So far:
- Cartopy and other plotting software has a variety of issues with the Arctic for so many reasons. In the future, there will probably be a different plotting mechanism used instead of it (probably done through R, or QGIS). Should be done after the fact.
- Haversine calculation is sometimes a bit buggy. I am working on making this more reliable, but probably is caused by underlying dataset issues.
- The classes could be better-designed, and not everything is type-labeled, although this is getting there. 
- Need support for both the week and daily version of the sea ice vectors dataset to do an adequate comparison on them.
- There aren't enough high-quality docstrings in my code yet, so it might be a bit difficult to understand.
- Must swap to using the clean buoy dataset rather than the messy one.



