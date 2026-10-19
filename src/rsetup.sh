#!/bin/sh
# Note that you will need Rscript installed on your $PATH,
# and will need to run the simulator with the same user
# that runs this script. Otherwise R won't find these packages.
Rscript -e "install.packages(c('rlang', 'dplyr', 'sf', 'ggplot2', 'ggspatial', 'rnaturalearth', 'rnaturalearthdata', 'optparse), repos='https://cran.rstudio.com')"
