#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Re-sync the vendored ung220z.py with upstream Hut-hzf/ung220z-tool.
# Usage: bash scripts/sync-upstream.sh [<commit>]
#   <commit> defaults to upstream main HEAD.
# The script fetches the pristine file, applies ung220z-luci.patch, and
# shows the diff against the current vendored copy. If the patch does not
# apply cleanly (upstream drifted), it stops and reports the rejected
# hunks -- rebase the patch by hand, do not force it.
set -eu
REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMMIT=${1:-main}
UPSTREAM=https://raw.githubusercontent.com/Hut-hzf/ung220z-tool

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM
echo "fetching ung220z.py @ $COMMIT ..."
curl -fsSL "$UPSTREAM/$COMMIT/ung220z.py" -o "$tmp/ung220z.py"
echo "applying ung220z-luci.patch ..."
if ! patch -p1 -d "$tmp" --dry-run < "$REPO_DIR/scripts/ung220z-luci.patch" > "$tmp/dryrun.log" 2>&1; then
	echo "PATCH DOES NOT APPLY CLEANLY -- upstream drifted. See:"
	cat "$tmp/dryrun.log"
	echo "Rebase scripts/ung220z-luci.patch by hand; do not force it."
	exit 1
fi
patch -p1 -d "$tmp" < "$REPO_DIR/scripts/ung220z-luci.patch" > /dev/null
cp "$tmp/ung220z.py" "$REPO_DIR/ung220z-tool/files/usr/bin/ung220z"
chmod 755 "$REPO_DIR/ung220z-tool/files/usr/bin/ung220z"
echo "vendored copy updated. Diff vs previous version:"
cd "$REPO_DIR" && git diff -- ung220z-tool/files/usr/bin/ung220z || true
echo "Verify with: python3 -m py_compile ung220z-tool/files/usr/bin/ung220z"
echo "and the mock end-to-end test in scripts/mock-ont/."
