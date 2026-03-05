#!/bin/bash
set -euo pipefail

#bazel version

#bazel build //src/main/java/com/google/devtools/build/lib:gen_mdx_reference_docs

#unzip bazel-bin/src/main/java/com/google/devtools/build/lib/mdx-reference-docs.zip -d "$DOCS_DIR"

cd "$DOCS_DIR"

# Fetch the docs.json file at HEAD, otherwise mintlify fails.
curl -sS "$DOCS_JSON_URL" -o docs.json

# https://www.mintlify.com/docs/installation#validate-documentation-build
/usr/local/bin/mint validate

# TODO: call `mint broken-links``
