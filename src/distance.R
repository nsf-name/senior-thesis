### distance.R
## DATA PROCESSING
# load all required libraries
suppressPackageStartupMessages({
  library(rlang)
  library(dplyr)
  library(tidyverse)
  library(ggplot2)
  library(optparse)
})

# parse command-line options
option_list <- list(
  make_option(c("-i", "--input"), type = "character",
              help = "input path", required = TRUE),
  make_option(c("-f", "--file"), type = "character",
              help = "simulator name", required = TRUE),
  make_option(c("-o", "--output"), type = "character",
              help = "output path", required = TRUE),
  make_option(c("-h", "--height"), type = "integer",
              help = "height of saved image", default = 8),
  make_option(c("-w", "--width"), type = "integer",
              help = "width of saved image", default = 8)
)
# our -h conflicts with that of the default help option
opt <- parse_args(OptionParser(option_list = option_list,
                               add_help_option = FALSE))
cat("\033[32m[INFO]\033[0m Loading data for plotting... \n")
df <- read.csv(
  paste(opt$input, sprintf("%s-InterSimDist.csv", opt$file), sep = "")
)
df$time <- as.Date(df$time)
cat("\033[32m[INFO]\033[0m Loading is now complete. Plotting... \n")
## PLOTTING
fit <- lm(distances ~ time, data=df)
r2 <- summary(fit)$r.squared
slope <- coef(fit)["time"]
subtitle <- sprintf("distance = %.4f * time + %.2f, R² = %.3f", slope, coef(fit)[1], r2)

ggplot(df, aes(x=time, y=distances)) +
  geom_line() +
  geom_point() +
  geom_smooth(method="lm") +
  theme(axis.text.x=element_text(angle=45, hjust=1)) + 
  scale_x_date(date_labels="%Y-%m-%d") +
  scale_y_continuous(limits=c(0, NA)) +
  labs(
    title=sprintf("Buoy vs Ice: Distance (Simulator #%s)", name), 
    subtitle=subtitle,
    x="Time (days)",
    y="Distance (km)"
  )

cat("\033[32m[INFO]\033[0m Plotting complete. Writing... \n")
# save to user-specified path.
ggsave(sprintf("%s/%s-Distance.png", opt$output, opt$file),
       width = opt$width, height = opt$height, dpi = 600)
cat("\033[32m[INFO]\033[0m Written successfully. Complete! \n")

