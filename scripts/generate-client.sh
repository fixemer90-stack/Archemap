#!/usr/bin/env bash
set -euo pipefail

# Generate TypeScript API client from OpenAPI spec
# Usage: ./scripts/generate-client.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SPEC="$ROOT_DIR/contracts/openapi.yaml"
OUTPUT_DIR="$ROOT_DIR/frontend/src/lib/api/client"

if [[ ! -f "$SPEC" ]]; then
  echo "Error: OpenAPI spec not found at $SPEC"
  exit 1
fi

echo "Generating TypeScript client from $SPEC..."
echo "Output directory: $OUTPUT_DIR"

# Clean previous generated files
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Generate using openapi-typescript (types) + openapi-fetch (runtime client)
npx openapi-typescript "$SPEC" -o "$OUTPUT_DIR/types.ts"
npx openapi-typescript-codegen \
  --input "$SPEC" \
  --output "$OUTPUT_DIR" \
  --client fetch \
  --name ApiClient

echo ""
echo "Generated files:"
ls -la "$OUTPUT_DIR"
echo ""
echo "Done. Import the client from '@/lib/api/client'."
