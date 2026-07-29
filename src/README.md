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

In some [future version of MATLAB](https://www.mathworks.com/support/requirements/python-compatibility.html?s_tid=srchtitle_site_search_1_python+compatibility) (probably R2026b), Python 3.14 code will be callable in MATLAB (this tool uses Python 3.14). When that time comes, with your MATLAB's working directory set to wherever this code is located, run this at the Command Window:
```matlab
>> pyenv('Version', ...
         pwd + "/.venv/bin/python", ...
         'ExecutionMode', 'OutOfProcess')
% try InProcess for better speed
```
This will load the Python interpreter into MATLAB. Then run:
```matlab
>> py.importlib.import_module('simlib')
```
Now you are ready to access the library. Since there's no MATLAB wrapper, you may find that it's a bit cumbersome to work with, and NumPy types will need conversion. 

## Performance?
Pretty good. I had initially considered [Parcels](https://docs.parcels-code.org/en/latest/) for this, but it had way too much overhead and complexity for my needs (this is a 2D problem and Parcels is a 3D simulator), so I'm rolling my own. This is way faster, although I didn't get far into my Parcels kernel-building to see for myself.

Internally, the workload is executed per-key in the dictionary. It's mostly `IceTrajectory` that is slow because it actually has to do math. It can take a really long time on long runs, but assuming you set up the dataset cleanly, this should almost never happen. Most jobs should complete all non-plotting tasks within a couple of seconds.

When `Simulator` is created, it can take a long time to load all data and construct simulator objects, depending on the speed of your hard drive. I've considered implementing a caching feature to make it easier for debugging and reruns.

## Bugs?
Yes. It's very much a work in progress.


