#!/bin/bash
#Take screenshot with Flameshot 
# Wrapper because flameshot causes picom to crash on Debian 12.
# Not sure what causes this, but this is the workaround.

flameshot gui 
pkill picom
picom --config "$HOME/.config/bspwm/picom.conf" &
