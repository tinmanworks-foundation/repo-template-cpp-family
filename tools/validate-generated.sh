#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

models=(lib exe engine-app workspace plugin-shared plugin-addon)
langs=(c cpp)
offline_mode="${VALIDATE_OFFLINE:-0}"

for model in "${models[@]}"; do
  for lang in "${langs[@]}"; do
    out="$TMP_ROOT/${model}-${lang}"
    echo "== scaffold ${model}/${lang} =="
    python3 "$ROOT_DIR/tools/scaffold.py" \
      --model "$model" \
      --lang "$lang" \
      --project-name "demo_${model}_${lang}" \
      --output-dir "$out" \
      --setup

    echo "== build/test ${model}/${lang} =="
    if [[ "$offline_mode" == "1" ]]; then
      cmake -S "$out" --preset native-debug -DBUILD_TESTING=OFF
      cmake --build "$out/build/native-debug"
      continue
    fi

    cmake --preset native-debug -S "$out"
    cmake --build --preset native-debug -S "$out"
    ctest --test-dir "$out/build/native-debug" --output-on-failure
  done
done

echo "Validation complete."
