#!/bin/sh
# Note that you will need Rscript installed on your path,
# and will need to run the simulator with the same user
# that runs this script.
Rscript -e "install.packages(c('sf', 'ggplot2', 'ggspatial', 'rnaturalearth', 'rnaturalearthdata', 'optparse), repos='https://cran.rstudio.com')"
