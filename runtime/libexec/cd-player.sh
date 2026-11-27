#!/rescue/sh
# SGI File Manager resolves /bin/sh to the donor's Bourne shell.
# Select an audio track from the desktop and send it to NetBSD's sound device.
PATH=/bin:/usr/bin
export PATH
LC_ALL=C
export LC_ALL
device=/dev/rcd0c
message=/usr/X11R7/bin/xmessage
dialog() { "$message" -center -name XiriCDPlayer -title 'Audio CD' "$@"; }

player=
stop_player() {
    if [ -n "$player" ]; then
        kill "$player" 2>/dev/null
        wait "$player" 2>/dev/null
        player=
    fi
}
trap stop_player EXIT
trap 'exit 1' HUP INT TERM

page=1
label='Choose a track to play.'
while :; do
    if ! toc=$(cdplay -f "$device" info 2>&1); then
        dialog -buttons OK "${toc:-Could not read the audio CD.}"
        exit 1
    fi
    tracks=$(printf '%s\n' "$toc" | awk '$1 ~ /^[0-9]+$/ && $1 >= 1 && $1 <= 99 && $NF == "audio" { print $1 }')
    if [ -z "$tracks" ]; then
        dialog -buttons OK 'No audio tracks are available.'
        exit 1
    fi
    # Keep the buttons within the desktop even on a 99-track disc.
    set -- $tracks
    [ "$page" -le "$#" ] || page=1
    shift "$((page - 1))"
    buttons=
    count=0
    for track do
        [ "$count" -lt 6 ] || break
        buttons="${buttons}Track $track:0,"
        count=$((count + 1))
    done
    [ "$page" -eq 1 ] || buttons="${buttons}Back:0,"
    [ "$#" -le "$count" ] || buttons="${buttons}More:0,"
    choice=$(dialog -print -buttons "${buttons}Stop:0,Close:0" "$label") || exit 0
    case "$choice" in
        Back) page=$((page - 6)) ;;
        More) page=$((page + 6)) ;;
        Stop) stop_player; label='Playback stopped.' ;;
        'Track '*)
            track=${choice#Track }
            stop_player
            cdplay -a /dev/sound -f "$device" play "$track" "$track" &
            player=$!
            label="Selected track $track."
            ;;
        *) exit 0 ;;
    esac
done
