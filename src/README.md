# Simulator Code
This code simulates buoy tracks. It uses inputs from the [International Arctic Buoy Programme](https://iabp.apl.uw.edu) and the [Polar Pathfinder Sea Ice Vectors](https://nsidc.org/data/nsidc-0116) datasets, which you will need to fetch yourself (they're not vendored with this code for copyright reasons). The helper scripts in `modules/extra` can do this for you, assuming you have your development environment set up right.

How does it work? There's a `Simulator` class which does all the setup for you once you've made an instance of it. Internally, the dataset is contained as one very large dictionary. The keys are a unique buoy ID run (as made unique by [this dataset](https://arcticdata.io/catalog/view/doi%3A10.18739%2FA2WS8HP1V)), and they contain a list with two objects: a `BuoyTrajectory` and an `IceTrajectory` (subclasses of the more general-purpose `Trajectory` superclass). The methods exposed on them allow for simulating and running experiments with the datasets. For more information, read the method docstrings and the code itself.

## Development / Running
First install `uv` by running `brew install uv` (or equivalent on your OS; if you have Rust, `cargo install uv` should work too). Then run:
```
uv sync
```
From there, it will download all Python dependencies (and Fortran ones, since `uv` uses binary wheels). 
Next, to setup the R environment, run:
```
./rsetup.sh
```
Follow all prompts. You may need to install some native libraries, such as `proj` and `BLAS`. How to do so for your platform is outside the scope of this documentation, and is easily found elsewhere.
Once that wraps up, run:
```
uv run simulator run
```
This will start the parallel executor, which runs all the buoys in a thread pool. You are encouraged to tweak the exact setup to your needs. For help, run `uv run simulator --help`; you can use the `-h` or `--help` flag on any subcommand.

In [MATLAB R2026b](https://www.mathworks.com/support/requirements/python-compatibility.html?s_tid=srchtitle_site_search_1_python+compatibility) Python 3.14 code is callable in MATLAB (this tool uses Python 3.14). If you prefer, with your MATLAB's working directory set to wherever this code is located on your machine, run this at the Command Window:
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
It's between pretty good to middling, depending on the specific simulator you're running. I had initially considered [Parcels](https://docs.parcels-code.org/en/latest/) for this, but it had way too much overhead and complexity for my needs (this is a 2D problem and Parcels is a 3D simulator), so I'm rolling my own. This is way faster, although I didn't get far into my Parcels kernel-building to see for sure. 

It's mostly `IceTrajectory` that is slow because it actually has to do math; empirically, weekly ice motion datasets run 10x faster than daily in my testing, so if you want to iterate with the code I recommend using that first.

## Bugs / Future Work?
Yes. It's very much a work-in-progress. That said, most of them are design related:
- Plotting should be easier to do in notebooks
- Need to make it easier to Monte Carlo buoys
- Better plotting techniques
- A formal method of scoring simulator accuracy

I would also like to write a property-based test suite; that will arrive in the future.


