library(sf)
library(ggplot2)
library(ggspatial)
library(rnaturalearth)
library(rnaturalearthdata)

# TODO: when this is a function, we need to change R's working dir
# to be that of where the CSV data is held.

# function signature should probably be something like:
# function plot_sim(path, id)
# for single plots, and
# function plot_sim_all(path)
# that one will just do all the ones in $path.
# anything more than that is likely too complex

# so we take in some filename. get "20081228_35238_d-BuoyTrajectory.csv":
# truename <- str_split_1(string, "-")[1]
# now we can create our filename:
# filename <- paste(truename, "-Plot.png", sep="")
# save to that filename in ggplot!

buoy <- read.csv("test.csv")
buoy_sf <- st_as_sf(buoy, coords=c("lon", "lat"), crs=4326)
buoy_headtail <- buoy_sf[c(1, nrow(buoy)), ]
buoy_line <- st_combine(buoy_sf) |> st_cast("LINESTRING")

ice <- read.csv("icy.csv")
ice_sf <- st_as_sf(ice, coords=c("lon", "lat"), crs=4326)
ice_headtail <- ice_sf[c(1, nrow(ice)), ]
ice_line <- st_combine(ice_sf) |> st_cast("LINESTRING")

# this could work anywhere but it's just convenient to head it
name <- buoy[1, ]$id
start_time <- buoy[1, ]$time
end_time <- buoy[nrow(buoy), ]$time

theme_set(theme_bw())
world <- ne_countries(scale = "medium", returnclass = "sf")
coast <- ne_coastline(scale = "medium")

disp_win <- st_sfc(
  st_point(c(-135.0, 60.0)), # sw corner lon, lat
  st_point(c(45.0, 60.0)),   # ne corner lon, lat
  crs = 4326
)
disp_win_trans <- st_transform(disp_win, crs=st_crs(3408))
disp_win_coord <- st_coordinates(disp_win_trans)

# TODO: make this all a function
ggplot(data=world)+
  geom_sf()+
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

