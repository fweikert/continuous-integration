# Use the official Node.js LTS image as the base, which includes npm
FROM gcr.io/bazel-public/ubuntu2404:latest

##################################################################################################################
# Install nvm & node as per https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-in-docker

# Use bash for the shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Create a script file sourced by both interactive and non-interactive bash shells
ENV BASH_ENV=/root/.bash_env
RUN touch "${BASH_ENV}"
RUN echo '. "${BASH_ENV}"' >> ~/.bashrc

# Download and install nvm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | PROFILE="${BASH_ENV}" bash
RUN echo node > .nvmrc
RUN nvm install v24.14.0
##################################################################################################################

# Install the mint package globally
RUN npm i -g mint

RUN chmod 0755 /root/.nvm/versions/node/v24.14.0/bin/mint && ln -s /root/.nvm/versions/node/v24.14.0/bin/mint /usr/local/bin/mint

# Set default environment variables (optional, can be overridden at runtime)
ENV DOCS_DIR="docs"
ENV DOCS_JSON_URL="https://raw.githubusercontent.com/bazel-contrib/bazel-docs/refs/heads/main/docs.json"

COPY --chown=root:root check_docs.sh /usr/local/bin/check_docs.sh

RUN chmod 0755 /usr/local/bin/check_docs.sh

ENTRYPOINT [ "/usr/local/bin/check_docs.sh" ]
