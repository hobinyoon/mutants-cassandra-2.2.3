# Tested with gnuplot 4.6 patchlevel 6

FN_IN = system("echo $FN_IN")
FN_OUT = system("echo $FN_OUT")

# Get min and max values
set terminal unknown
plot \
FN_IN every 31 u 0:1 w points not

set terminal pdfcairo enhanced size 3in, 2in
set output FN_OUT

#set tmargin at screen 0.975
#set bmargin at screen 0.152
#set lmargin at screen 0.185
#set rmargin at screen 0.940

set xlabel "Operation order (normalized)" offset 0,0.3
set ylabel "Key (sequantially reassigned)" offset 1.6,0

set border (1 + 2) lc rgb "#808080"
set ytics nomirror scale 0.5,0 tc rgb "#808080"
set xtics nomirror scale 0.5,0 tc rgb "#808080"

#set xdata time
#set timefmt "%H:%M:%S"
#set format x "%.1S"

set pointsize 0.02

plot \
FN_IN every 31 u ($0/GPVAL_DATA_X_MAX):($1/GPVAL_DATA_Y_MAX) w points pt 7 not
