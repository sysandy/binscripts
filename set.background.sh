#!/bin/bash 
##############################################################################
# This is a quick and dirty little script to change backgrounds on each of my
# displays either statically or randomly.  Run from cron to change on a frequent
# schedule.
#
# Andy Malato
# March 2024
##############################################################################
WALLPAPER="${1:?You must specify full path to image or directory of images}"
SCREEN="${2:-0}"
ME=$(basename $0)

# places to look for backgrounds.  First valid directory in array wins!
IMGDIR=('/afs/malato/platform/local/wallpaper' '/home/andym/andy/backgrounds' '/home/andym/Pictures/Backgrounds')

# place to search for utilities 
UTIL_SEARCH_PATH=('/usr/local/bin' '/usr/bin')

##############################################################################
# bomb()
##############################################################################
bomb()
{
        MESG="$ME: BOMB!--${*}"
        echo "$MESG"
        exit 1
}

##############################################################################
# findutil() - returns full path for a given utility
##############################################################################
findutil() {

        local _U=${1}
        local _P=""

        if echo ${_U} | grep -q "^\/"
        then
                # full path specified to util
                if [[ -x ${_U} ]]; then
                        echo "${_U}"
                        return
                else
                        echo "${_U}"
                        return 1
                fi
        else
                for _P in ${UTIL_SEARCH_PATH[@]}
                do
                        if [[ -x ${_P}/${_U} ]]; then
                                echo "${_P}/${_U}"
                                return
                        fi
                done
        fi
        # if we get here, utility was not found
        echo "${_U}"
        return 1
}

##############################################################################
# getresofmonitor()
##############################################################################
getresofmonitor() {

	# First grab the name of the monitor
	local ACTIVEINPUT=$(${XRANDR} --listactivemonitors | grep ${SCREEN}: | awk '{print $NF}')
	# Now get current resolution for that activeinput
	local CURRENTRES=$(${XRANDR} --query --current | grep "${ACTIVEINPUT}" -A1 | tail -1 | awk '{print $1}')

	echo ${CURRENTRES}

}

##############################################################################
# setbackground() 
##############################################################################
setbackground() {

	local _wallpaperobj=${1}

	if [[ -d "${_wallpaperobj}" ]] 
	then
		# we set background for ${_screen} to random image given in directory
		${NITROGEN} --set-zoom --save --random ${_wallpaperobj} --head=${SCREEN}
	else
		# we assume background is an image
		${NITROGEN} --set-zoom --save ${_wallpaperobj} --head=${SCREEN}
	fi

}
######################
# Set our display
######################
export DISPLAY=:0



NITROGEN=$(findutil nitrogen) || bomb "Can't find nitrogen[$NITROGEN] in any of [${UTIL_SEARCH_PATH[@]}]"
XRANDR=$(findutil xrandr) || bomb "Can't find xrandr[$XRANDR] in any of [${UTIL_SEARCH_PATH[@]}]"

# Find an image directory that exists
for d in ${IMGDIR[@]}
do
	if [[ -d ${d} ]]
	then
		imgdir=${d}
		break
	fi
done
[[ -z ${imgdir} ]] && bomb "Unable to find a valid directory containing background images"

# Get current resolution 
display_resolution=$(getresofmonitor)

VALID_WALLPAPER=False

case $WALLPAPER in

	"winter")
		[[ -d ${imgdir}/winter.scenes/${display_resolution} ]] && 
			WALLPAPER=${imgdir}/winter.scenes/${display_resolution} 
	;;
	"spring")
		[[ -d ${imgdir}/Spring/${display_resolution} ]] && 
			WALLPAPER=${imgdir}/Spring/${display_resolution} 
	;;
	"summer")

		[[ -d ${imgdir}/Summer/${display_resolution} ]] && 
			WALLPAPER=${imgdir}/Summer/${display_resolution} 
	;;
	"fall")

		[[ -d ${imgdir}/Fall/${display_resolution} ]] && 
			WALLPAPER=${imgdir}/Fall/${display_resolution} 
	;;
	"easter")

		[[ -d ${imgdir}/Easter/${display_resolution} ]] && 
			WALLPAPER=${imgdir}/Easter/${display_resolution} 
	;;
	"christmas")

		[[ -d ${imgdir}/Christmas/${display_resolution} ]] && 
			WALLPAPER=${imgdir}/Christmas/${display_resolution} 
	;;

	*)
		[[ -d ${WALLPAPER} ]] && VALID_WALLPAPER=True
		[[ -f ${WALLPAPER} ]] && VALID_WALLPAPER=True

		if [[ "$VALID_WALLPAPER" == "False" ]]
		then
			bomb "Invalid file or directory given for background image"
		fi
	;;
esac

setbackground $WALLPAPER
