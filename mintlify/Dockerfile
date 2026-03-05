# Use the official Node.js LTS image as the base, which includes npm
FROM node:lts-alpine

# Install the mint package globally
RUN npm i -g mint

RUN apk --no-cache add curl

# Set default environment variables (optional, can be overridden at runtime)
ENV DOCS_DIR="docs"
ENV DOCS_JSON_URL="https://raw.githubusercontent.com/bazel-contrib/bazel-docs/refs/heads/main/docs.json"

RUN curl -sS https://github.com/bazelbuild/bazelisk/releases/download/v1.28.1/bazelisk-linux-amd64 -o /usr/local/bin/bazelisk
RUn chmod 0755 /usr/local/bin/bazelisk

COPY --chown=root:root check_docs.sh /usr/local/bin/check_docs.sh

RUN chmod 0755 /usr/local/bin/check_docs.sh

ENTRYPOINT [ "/usr/local/bin/check_docs.sh" ]
