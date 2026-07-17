#!/usr/bin/env bash

set -euo pipefail

sdk_dir="$(git -C "${1:-.}" rev-parse --show-toplevel)"
remote="${LINPHONE_REMOTE:-origin}"
commits=(
  b089673eb2dc7467622098168ea0aa3455b2a367
  28d4ed9d750decbb4edbb6f23875a306ba7f750c
  9bfce4d5ac2755e64be76abcb01e7354c73f13df
)

resolve_backport_conflict() {
  local commit="$1"
  local conflicts

  conflicts="$(git -C "$sdk_dir" diff --name-only --diff-filter=U | sort)"

  if [[ "$commit" == "b089673eb2dc7467622098168ea0aa3455b2a367" ]] &&
    [[ "$conflicts" == $'CHANGELOG.md\nliblinphone/tester/audio-quality-tester.cpp' ]]; then
    git -C "$sdk_dir" checkout --ours -- CHANGELOG.md
    git -C "$sdk_dir" checkout --theirs -- liblinphone/tester/audio-quality-tester.cpp
    python3 - "$sdk_dir/liblinphone/tester/audio-quality-tester.cpp" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
content = path.read_text()
replacements = (
    (
        'TEST_NO_TAG("Audio bandwidth estimation", audio_bandwidth_estimation),',
        'TEST_ONE_TAG("Audio bandwidth estimation", audio_bandwidth_estimation, "shaky"),',
    ),
    (
        'TEST_NO_TAG("Audio bandwidth estimation on secure call", audio_bandwidth_estimation_on_secure_call),',
        'TEST_ONE_TAG("Audio bandwidth estimation on secure call", audio_bandwidth_estimation_on_secure_call, "shaky"),',
    ),
    (
        "                                         1010,\n"
        "                                         1};",
        "                                         1010,\n"
        "                                         4};",
    ),
)

for old, new in replacements:
    if content.count(old) != 1:
        raise SystemExit(f"Expected one occurrence in {path}: {old!r}")
    content = content.replace(old, new)

path.write_text(content)
PY
    git -C "$sdk_dir" add \
      CHANGELOG.md \
      liblinphone/tester/audio-quality-tester.cpp
  elif [[ "$commit" == "9bfce4d5ac2755e64be76abcb01e7354c73f13df" ]] &&
    [[ "$conflicts" == "external/opus" ]]; then
    local opus_commit
    opus_commit="$(git -C "$sdk_dir" rev-parse "$commit:external/opus")"
    if ! git -C "$sdk_dir/external/opus" cat-file -e "$opus_commit^{commit}" 2>/dev/null; then
      git -C "$sdk_dir/external/opus" fetch origin "$opus_commit"
    fi
    git -C "$sdk_dir/external/opus" checkout "$opus_commit"
    git -C "$sdk_dir" add external/opus
  else
    return 1
  fi

  if ! GIT_EDITOR=true git -C "$sdk_dir" cherry-pick --continue; then
    if git -C "$sdk_dir" diff --quiet &&
      git -C "$sdk_dir" diff --cached --quiet; then
      git -C "$sdk_dir" cherry-pick --skip
    else
      return 1
    fi
  fi
}

missing_commits=()
for commit in "${commits[@]}"; do
  if ! git -C "$sdk_dir" cat-file -e "$commit^{commit}" 2>/dev/null; then
    missing_commits+=("$commit")
  fi
done

if ((${#missing_commits[@]})); then
  git -C "$sdk_dir" fetch "$remote" "${missing_commits[@]}"
fi

if [[ -n "$(git -C "$sdk_dir" status --porcelain)" ]]; then
  echo "Refusing to cherry-pick into a dirty Linphone SDK checkout" >&2
  exit 1
fi

for commit in "${commits[@]}"; do
  if git -C "$sdk_dir" merge-base --is-ancestor "$commit" HEAD; then
    echo "Skipping $commit: already upstream"
    continue
  fi

  if [[ -n "$(git -C "$sdk_dir" log \
    --fixed-strings \
    --grep="cherry picked from commit $commit" \
    --format=%H \
    -1 HEAD)" ]]; then
    echo "Skipping $commit: already cherry-picked"
    continue
  fi

  if ! git -C "$sdk_dir" cherry-pick -x "$commit"; then
    if ! resolve_backport_conflict "$commit"; then
      echo "Unrecognized conflict while cherry-picking $commit" >&2
      exit 1
    fi
  fi

  if [[ "$commit" == "28d4ed9d750decbb4edbb6f23875a306ba7f750c" ]]; then
    git -C "$sdk_dir" submodule update --init external/opus
  fi
done
