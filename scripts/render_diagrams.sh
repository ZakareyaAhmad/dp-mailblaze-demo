#!/usr/bin/env bash
set -euo pipefail

mkdir -p docs/diagrams/generated

for file in docs/diagrams/*.mmd; do
  name=$(basename "$file" .mmd)
  mmdc -i "$file" -o "docs/diagrams/generated/${name}.png"
done

echo "Diagrams rendered successfully."
