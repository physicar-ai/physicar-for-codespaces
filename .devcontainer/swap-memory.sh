#!/bin/bash
set -Eeuo pipefail

SWAPFILE="/tmp/swapfile"

mem_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
mem_gib=$(( mem_kb / (1024*1024) ))

if (( mem_gib > 64 )); then
  echo "[swap] Mem=${mem_gib}GiB > 64GiB -> do nothing"
  exit 0
fi

target_total_gib=$(( mem_gib * 4 ))
if (( target_total_gib > 64 )); then
  target_total_gib=64
fi

desired_swap_gib=$(( target_total_gib - mem_gib ))
if (( desired_swap_gib < 0 )); then desired_swap_gib=0; fi
if (( desired_swap_gib > 16 )); then desired_swap_gib=16; fi
desired_swap_bytes=$(( desired_swap_gib * 1024 * 1024 * 1024 ))

current_swap_bytes=0
if swapon --show=NAME --noheadings | grep -qx "${SWAPFILE}"; then
  current_swap_bytes=$(swapon --show=NAME,SIZE --bytes --noheadings \
    | awk -v f="${SWAPFILE}" '$1==f {print $2}')
fi

echo "[swap] Mem=${mem_gib}GiB, target_total=${target_total_gib}GiB, desired_swap=${desired_swap_gib}GiB"

if (( desired_swap_gib == 0 )); then
  if swapon --show=NAME --noheadings | grep -qx "${SWAPFILE}"; then
    sudo swapoff "${SWAPFILE}" || true
  fi
  sudo rm -f "${SWAPFILE}" 2>/dev/null || true
  exit 0
fi

recreate=true
if (( current_swap_bytes == desired_swap_bytes )) && [[ -f "${SWAPFILE}" ]]; then
  recreate=false
fi

if $recreate; then
  if swapon --show=NAME --noheadings | grep -qx "${SWAPFILE}"; then
    sudo swapoff "${SWAPFILE}" || true
  fi
  sudo rm -f "${SWAPFILE}" 2>/dev/null || true

  avail_bytes=$(df --output=avail -B1 /tmp | tail -n1)
  needed_bytes=$(( desired_swap_bytes + 1024*1024*1024 ))
  if (( avail_bytes < needed_bytes )); then
    if command -v numfmt >/dev/null 2>&1; then
      echo "[swap] Not enough space on /tmp (avail=$(numfmt --to=iec ${avail_bytes}), need>=($(numfmt --to=iec ${needed_bytes})))"
    else
      echo "[swap] Not enough space on /tmp (avail=${avail_bytes}B, need>=${needed_bytes}B)"
    fi
    exit 1
  fi

  sudo dd if=/dev/zero of="${SWAPFILE}" bs=1M count=$(( desired_swap_gib * 1024 )) status=none
  sudo chmod 600 "${SWAPFILE}"
  sudo mkswap "${SWAPFILE}" >/dev/null
fi

if ! swapon --show=NAME --noheadings | grep -qx "${SWAPFILE}"; then
  sudo swapon "${SWAPFILE}"
fi
