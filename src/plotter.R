### plotter.R
## DATA PROCESSING
# load all required libraries
library(rlang)
library(dplyr)
library(sf)
library(ggplot2)
library(ggspatial)
library(rnaturalearth)
library(rnaturalearthdata)
library(optparse)

# function definition we will use a lot later.
optional_layer <- function(data, ...) {
  if (!is.null(data))
    list(geom_sf(data = data, ...))
  else
    list()
}

# parse command-line options
option_list <- list(
  make_option(c("-i", "--input"), type="character",
              help="input path", required=TRUE),
  make_option(c("-f", "--file"), type="character",
              help="simulator name", required=TRUE),
  make_option(c("-o", "--output"), type="character",
              help="output path", required=TRUE),
  make_option(c("-h", "--height"), type="integer",
              help="height of saved image", default=8),
  make_option(c("-w", "--width"), type="integer",
              help="width of saved image", default=8)
)
# our -h conflicts with that of the default help option
opt <- parse_args(OptionParser(option_list=option_list,
                               add_help_option=FALSE))

# read in the buoy simulation
buoy_result <- tryCatch({
  buoy <- read.csv(paste(opt$input, sprintf("%s-BuoyTrajectory.csv", opt$file), sep=""))
  buoy_sf <- st_as_sf(buoy, coords=c("lon", "lat"), crs=4326)
  list(
    data = buoy,
    headtail = buoy_sf[c(1, nrow(buoy_sf)), ] |> mutate(position = c("Start", "End")),
    line     = st_combine(buoy_sf) |> st_cast("LINESTRING")
  )
}, error = function(e) {
  message("Warning: could not load buoy data: ", e$message)
  NULL
})

# now read in the cooresponding ice simulation
ice_result <- tryCatch({
  ice <- read.csv(paste(opt$input, sprintf("%s-IceTrajectory.csv", opt$file), sep=""))
  ice_sf <- st_as_sf(ice, coords=c("lon", "lat"), crs=4326)
  list(
    data = ice,
    headtail = ice_sf[c(1, nrow(ice_sf)), ] |> mutate(position = c("Start", "End")),
    line     = st_combine(ice_sf) |> st_cast("LINESTRING")
  )
}, error = function(e) {
  message("Warning: could not load ice data: ", e$message)
  NULL
})

# load critical data from somewhere. tidyverse null-coalescing.
meta_source <- buoy_result$data %||% ice_result$data
name       <- meta_source[1, ]$id
start_time <- meta_source[1, ]$time
end_time   <- meta_source[nrow(meta_source), ]$time

## PLOTTING
# load a basic theme and prepare natural earth data.
theme_set(theme_bw())
world <- ne_countries(scale = "medium", returnclass = "sf")
coast <- ne_coastline(scale = "medium")

# set bounds for our plot.
disp_win <- st_sfc(
  st_point(c(-135.0, 60.0)), # sw corner lon, lat
  st_point(c(45.0, 60.0)),   # ne corner lon, lat
  crs = 4326
)
# transform into the correct coordinate reference system (Arctic-centered).
disp_win_trans <- st_transform(disp_win, crs=st_crs(3408))
disp_win_coord <- st_coordinates(disp_win_trans)

# render the plot.
ggplot(data = world) +
  geom_sf() +
  # buoys are red, ice is blue,
  # is this code bug free? I feel negatively about that too.
  optional_layer(data = buoy_result$line,     aes(color = "Buoy Path"),     linewidth = 0.8) +
  optional_layer(data = ice_result$line,      aes(color = "Ice Vectors"),   linewidth = 0.8) +
  optional_layer(data = buoy_result$headtail, aes(color = position),        size = 2) +
  optional_layer(data = ice_result$headtail,  aes(color = position),        size = 2) +
  scale_color_manual(
    name   = "Legend",
    values = c(
      "Buoy Path"   = "#e74c3c",
      "Ice Vectors" = "#3498db",
      "Start"       = "#2ecc71",
      "End"         = "#f39c12"
    )
  ) +
  labs(
    title    = paste("Simulator #", name),
    subtitle = paste("Start time: ", start_time, "\nEnd time: ", end_time),
    x = "Longitude (degrees)",
    y = "Latitude (degrees)"
  ) +
  coord_sf(
    xlim = disp_win_coord[, "X"],
    ylim = disp_win_coord[, "Y"],
    crs  = st_crs(3408)
  ) +
  theme(panel.background = element_rect(fill = "aliceblue"))

# save to user-specified path.
ggsave(sprintf("%s/%s.png", opt$output, opt$file),
       width = opt$width, height = opt$height, dpi = 600)
