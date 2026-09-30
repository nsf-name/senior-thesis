### plotter.R
## DATA PROCESSING
# load all required libraries
library(sf)
library(ggplot2)
library(ggspatial)
library(rnaturalearth)
library(rnaturalearthdata)
library(optparse)

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
buoy <- read.csv(paste(opt$input, 
                       sprintf("%s-BuoyTrajectory.csv", opt$file), sep=""))
buoy_sf <- st_as_sf(buoy, coords=c("lon", "lat"), crs=4326)
buoy_headtail <- buoy_sf[c(1, nrow(buoy)), ]
buoy_line <- st_combine(buoy_sf) |> st_cast("LINESTRING")

# now read in the cooresponding ice simulation
ice <- read.csv(paste(opt$input, 
                      sprintf("%s-IceTrajectory.csv", opt$file), sep=""))
ice_sf <- st_as_sf(ice, coords=c("lon", "lat"), crs=4326)
ice_headtail <- ice_sf[c(1, nrow(ice)), ]
ice_line <- st_combine(ice_sf) |> st_cast("LINESTRING")

# prepare data we will want for our plot.
name <- buoy[1, ]$id
start_time <- buoy[1, ]$time
end_time <- buoy[nrow(buoy), ]$time

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
ggplot(data=world)+
  geom_sf()+
  # buoys are red, ice is blue,
  # is this code bug free? I feel negatively about that too. 
  geom_sf(data=buoy_line, linewidth=0.8, color = "red")+
  geom_sf(data=ice_line, linewidth=0.8, color = "blue")+
  geom_sf(data = buoy_headtail, aes(color = c("Start", "End")), size = 2)+
  geom_sf(data = ice_headtail, aes(color = c("Start", "End")), size = 2)+
  scale_color_manual(values = c("Start" = "gold", "End" = "purple"),
                     name="Points")+
  scale_color_manual(values = c("Buoy Path" = "red", "Ice Vectors" = "blue"),
                     name="Trajectories")+
  labs(title=paste("Simulator #", name),
       subtitle=paste("Start time: ", start_time, "\nEnd time: ", end_time),
       x="Longitude (degrees)", y="Latitude (degrees)")+
  coord_sf(xlim = disp_win_coord[,'X'], 
           ylim = disp_win_coord[,'Y'], 
           crs = st_crs(3408))+
  theme(panel.background = element_rect(fill="aliceblue"))

# save to user-specified path.
ggsave(sprintf("%s/%s.png", opt$output, opt$file),
       width = opt$width, height = opt$height, dpi = 600)
