#!/usr/bin/env bash
# Three independent Xvfb/NeXium processes using ONE previously built native NRO.
# This captures evidence; the separate Python audit makes acceptance decisions.
set -euo pipefail
root="$(pwd -P)"
: "${NEXIUM_BIN:?NeXium executable must already be downloaded}"
test -s "$root/nros/vh_saturn_demo.nro"
test -s "$root/runtime-evidence/nexium-window.png"
test -s "$root/runtime-evidence/nexium.log"
folder="$root/runtime-evidence/repeat-trials"
mkdir -p "$folder/trial-01"
# Only copy top-level data from the earlier verified first run; no recursive
# copying of repeat-trials into itself and no recoding of screenshots.
find "$root/runtime-evidence" -maxdepth 1 -type f -exec cp -- '{}' "$folder/trial-01/" ';'
printf '%s\n' 0 >"$folder/trial-01/launcher-exit.txt"
printf '%s\n' 'origin=original_neXium_launch_step' >"$folder/trial-01/origin.txt"
for number in 02 03; do
  trial="$folder/trial-$number"
  workspace="$trial/workspace"
  mkdir -p "$workspace"
  ln -s "$root/nros" "$workspace/nros"
  ln -s "$root/scripts" "$workspace/scripts"
  # Each run has a separate working directory, Openbox and Xvfb display.
  # Keep all failed-run evidence and the exit status, then continue to trial 3.
  code=0
  (
    cd "$workspace"
    timeout --kill-after=5s 110s xvfb-run -a -s '-screen 0 1280x720x24' \
      bash scripts/nexium_xvfb_session.sh
  ) >"$trial/launch-output.log" 2>&1 || code=$?
  printf '%s\n' "$code" >"$trial/launcher-exit.txt"
  if [[ -d "$workspace/runtime-evidence" ]]; then
    cp -a "$workspace/runtime-evidence/." "$trial/"
  fi
  rm -rf -- "$workspace"
  printf 'VH_REPEAT_TRIAL number=%s exit=%s\n' "$number" "$code"
done
