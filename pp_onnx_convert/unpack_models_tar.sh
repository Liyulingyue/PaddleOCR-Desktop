#!/bin/bash

set -euo pipefail

SRC_DIR="models_tar"
DEST_BASE="models_pp"

# allow globs that don't match
shopt -s nullglob

if [ ! -d "$SRC_DIR" ]; then
    echo "Source directory $SRC_DIR does not exist."
    exit 1
fi

mkdir -p "$DEST_BASE"

found=false
for tarfile in "$SRC_DIR"/*.{tar,tar.gz,tgz}; do
    if [ ! -f "$tarfile" ]; then
        continue
    fi
    found=true
    filename=$(basename -- "$tarfile")
    model_name="${filename%%.tar.gz}"
    model_name="${model_name%%.tgz}"
    model_name="${model_name%%.tar}"
    dest="$DEST_BASE/$model_name"

    if [ -d "$dest" ] && [ "$(ls -A "$dest")" ]; then
        echo "Skipping $filename — $dest already exists and is non-empty"
        continue
    fi

    # extract into temporary dir first to detect single-top-level-dir case
    tmpdir=$(mktemp -d)
    echo "Extracting $filename -> temporary $tmpdir"
    if [[ "$tarfile" == *.tar.gz || "$tarfile" == *.tgz ]]; then
        tar -xzf "$tarfile" -C "$tmpdir"
    else
        tar -xf "$tarfile" -C "$tmpdir"
    fi

    # find top-level non-dot entries inside tempdir
    mapfile -t entries < <(find "$tmpdir" -mindepth 1 -maxdepth 1 -printf "%P\n")

    mkdir -p "$dest"
    if [ ${#entries[@]} -eq 1 ] && [ -d "$tmpdir/${entries[0]}" ]; then
        echo "Archive contains single top-level directory '${entries[0]}', flattening into $dest"
        # move contents of that single dir into dest
        shopt -s dotglob
        mv "$tmpdir/${entries[0]}"/* "$dest/" 2>/dev/null || true
        mv "$tmpdir/${entries[0]}"/.[!.]* "$dest/" 2>/dev/null || true
        shopt -u dotglob
    else
        echo "Moving extracted files into $dest"
        shopt -s dotglob
        mv "$tmpdir"/* "$dest/" 2>/dev/null || true
        mv "$tmpdir"/.[!.]* "$dest/" 2>/dev/null || true
        shopt -u dotglob
    fi

    rm -rf "$tmpdir"
    echo "Done: $filename"
done

if ! $found; then
    echo "No tar files found in $SRC_DIR."
fi

exit 0
