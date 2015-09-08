#!/bin/sh -ex
FROM="${1:-origin/master}"
TO="${2:-gerrit/master}"
CHANGE_ID="I9b01715ce955d695fe6334bdec62545d101f4f38"
git review -s
COMMIT="$(git commit-tree -p "$TO" -m "All-in-one from GitHub

Change-Id: $CHANGE_ID" "$FROM^{tree}")"
git push gerrit "$COMMIT":refs/for/master
