# The outgoing v6 HAL2 driver cannot save the v7 mute setting. Preserve the
# last saved mixer file through its shutdown. The v7 driver exposes mute.
if test -z "$(/usr/bin/mixerctl -n outputs.master.mute 2>/dev/null)"; then
    mixerctl_mixers=
else
    (
        set -e
        config=/etc/rc.conf.d/mixerctl
        stamp=/var/db/xiri-install/created/.indy-audio-mixer
        test -f "$stamp" && test "$(sha256 -q "$config")" = "$(cat "$stamp")" || exit 0
        tmp=$(mktemp /etc/rc.conf.d/.xiri-mixer.XXXXXX)
        trap 'rm -f "$tmp"' EXIT
        sed '/^#/d' /usr/local/share/xiri/examples/rc.conf.d/mixerctl >"$tmp"
        chmod 644 "$tmp"
        mv -f "$tmp" "$config"
        rm "$stamp"
    )
fi
