#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
inputs_dir="$repo_root/.work/netbsd-11.0"
source_root="$inputs_dir/source-tree"
source_dir=${XIRI_NETBSD_SOURCE_DIR:-"$source_root/usr/src"}
build_dir=${XIRI_NETBSD_BUILD_DIR:-"$repo_root/.work/netbsd-build"}
kernel_config=${XIRI_NETBSD_CONFIG:-"$repo_root/lab/netbsd-11.0/XIRI_INDY"}
tftp_dir=${XIRI_NETBSD_TFTP_DIR:-"$inputs_dir/tftp"}
build_jobs=${XIRI_BUILD_JOBS:-8}
build_arch=${XIRI_NETBSD_ARCH:-mipseb}
operation=${1:-all}

if (( $# > 1 )) || [[ ! $operation =~ ^(all|tools|kernel|gdb)$ ]]; then
    printf 'Usage: %s [all|tools|kernel|gdb]\n' "$0" >&2
    exit 2
fi
if [[ ! $build_jobs =~ ^[1-9][0-9]*$ ]]; then
    printf 'XIRI_BUILD_JOBS must be a positive integer\n' >&2
    exit 2
fi
if [[ ! $build_arch =~ ^(mipseb|mips64eb)$ ]]; then
    printf 'XIRI_NETBSD_ARCH must be mipseb or mips64eb\n' >&2
    exit 2
fi
if [[ $build_arch != mipseb && -z ${XIRI_NETBSD_SOURCE_DIR:-} ]]; then
    printf 'The 64-bit experiment requires an isolated fork build.\n' >&2
    exit 2
fi
build_dir=$(realpath -m "$build_dir")
tftp_dir=$(realpath -m "$tftp_dir")
kernel_config=$(realpath "$kernel_config")
if [[ $operation == all || $operation == kernel ]] && ! command -v genisoimage >/dev/null; then
    printf 'genisoimage is required to package the matching guest kernel file.\n' >&2
    exit 1
fi

# Fork builds must have isolated outputs and may not replace the release kernel.
if [[ -n ${XIRI_NETBSD_SOURCE_DIR:-} ]]; then
    if [[ -z ${XIRI_NETBSD_BUILD_DIR:-} || -z ${XIRI_NETBSD_TFTP_DIR:-} ]]; then
        printf 'Fork builds require XIRI_NETBSD_BUILD_DIR and XIRI_NETBSD_TFTP_DIR.\n' >&2
        exit 2
    fi
    source_dir=$(realpath "$source_dir")
    if [[ $build_dir == "$repo_root/.work/netbsd-build" ||
          $build_dir == "$repo_root/.work/netbsd-build/"* ||
          $tftp_dir == "$inputs_dir/tftp" || $tftp_dir == "$inputs_dir/tftp/"* ]]; then
        printf 'Fork builds must not reuse release build or TFTP paths.\n' >&2
        exit 2
    fi
    test -f "$source_dir/build.sh"
else
    # Verify the downloaded release inputs before extracting or reusing the tree.
    source_manifest=$(awk '$2 ~ /^source\/sets\//' "$repo_root/lab/netbsd-11.0/SHA512SUMS")
    (cd "$inputs_dir" && printf '%s\n' "$source_manifest" | sha512sum -c -)
    source_stamp="$source_root/.xiri-source-sets.sha512"
    if [[ -f $source_stamp ]]; then
        if [[ $(cat "$source_stamp") != "$source_manifest" ]]; then
            printf 'Source input manifest changed; prepare a separate source tree.\n' >&2
            exit 1
        fi
    else
        if [[ -d $source_dir ]]; then
            printf 'Unmarked source tree exists at %s; preserve it before preparing a fresh tree.\n' "$source_dir" >&2
            exit 1
        fi
        mkdir -p "$source_root"
        for archive in src gnusrc sharesrc syssrc; do
            tar --no-same-owner -xzf "$inputs_dir/source/sets/$archive.tgz" -C "$source_root"
        done
        printf '%s\n' "$source_manifest" > "$source_stamp"
    fi
fi

mkdir -p "$build_dir"
if [[ -f $build_dir/source-path && $(cat "$build_dir/source-path") != "$source_dir" ]]; then
    printf 'Build directory belongs to a different source tree.\n' >&2
    exit 2
fi
if [[ -f $build_dir/build-arch ]]; then
    if [[ $(cat "$build_dir/build-arch") != "$build_arch" ]]; then
        printf 'Build directory belongs to a different target architecture.\n' >&2
        exit 2
    fi
elif [[ $build_arch != mipseb && -e $build_dir/tools/bin/nbmake-sgimips ]]; then
    printf 'Use a fresh build directory for the 64-bit toolchain.\n' >&2
    exit 2
fi
printf '%s\n' "$build_arch" > "$build_dir/build-arch"
printf '%s\n' "$source_dir" > "$build_dir/source-path"
if [[ -n ${XIRI_NETBSD_SOURCE_DIR:-} ]]; then
    git -C "$source_dir" rev-parse HEAD > "$build_dir/source-revision"
    git -C "$source_dir" diff HEAD > "$build_dir/source.patch"
    git -C "$source_dir" status --short > "$build_dir/source-status"
fi
build_args=(
    -m sgimips -a "$build_arch" -U -u -j "$build_jobs"
    -O "$build_dir/obj" -T "$build_dir/tools" -D "$build_dir/dest"
    -V MKX11=no
    # GCC 16 defaults to C23. Bundled tools need the older C function rules.
    # GMP removes CFLAGS during ABI detection, so put the dialect in CC too.
    -V 'HOST_CC=cc -std=gnu17' -V 'HOST_CFLAGS=-O2 -std=gnu17'
)

run_build() {
    local target=$1 log=$2
    toolbox run -c xiri-iris env LC_ALL=C TZ=UTC HOST_SH=/bin/bash \
        /bin/bash "$source_dir/build.sh" "${build_args[@]}" "$target" \
        2>&1 | tee "$log"
}

if [[ $operation == gdb ]]; then
    # Install expat-devel and texinfo in the Toolbox before the first build.
    # The release source set ships this directly invoked shell script as 0644.
    chmod u+x "$source_dir/external/gpl3/gdb/dist/gdb/make-init-c"
    build_args+=(-V MKCROSSGDB=yes)
    run_build tools "$build_dir/tools-gdb.log"
elif [[ $operation == all || $operation == tools ]]; then
    run_build tools "$build_dir/tools.log"
fi
if [[ $operation == all || $operation == kernel ]]; then
    run_build "kernel.gdb=$kernel_config" "$build_dir/kernel.log"
    kernel_dir="$build_dir/obj/sys/arch/sgimips/compile/$(basename "$kernel_config")"
    mkdir -p "$tftp_dir" "$build_dir/kernel-media"
    boot_image=netbsd
    if [[ $build_arch == mips64eb ]]; then
        # The Indy PROM needs ELF32 headers around the 64-bit kernel payload.
        boot_image=netbsd.elf32
    fi
    install -m 0644 "$kernel_dir/$boot_image" "$tftp_dir/netbsd-XIRI_INDY"
    # /netbsd must match the running kernel for tools such as savecore.
    # A virtual CD supplies this file without relying on guest TCP transfers.
    install -m 0644 "$kernel_dir/netbsd" "$build_dir/kernel-media/netbsd"
    genisoimage -quiet -R -J -V XIRI_KERNEL -o "$build_dir/kernel.iso" \
        "$build_dir/kernel-media"
    sha256sum "$tftp_dir/netbsd-XIRI_INDY" "$kernel_dir/netbsd" "$kernel_dir/netbsd.gdb" \
        "$build_dir/kernel.iso" \
        | tee "$build_dir/kernel.sha256"
fi
