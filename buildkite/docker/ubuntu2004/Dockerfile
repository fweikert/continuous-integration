FROM ubuntu:20.04 AS ubuntu2004-bazel-nojdk
ARG TARGETARCH

ENV DEBIAN_FRONTEND="noninteractive"
ENV LANG "C.UTF-8"
ENV LANGUAGE "C.UTF-8"
ENV LC_ALL "C.UTF-8"

### Install packages required by Bazel and its tests
RUN apt-get -y update && \
    apt-get -y install --no-install-recommends \
    apt-utils \
    bind9-host \
    build-essential \
    clang \
    coreutils \
    curl \
    dnsutils \
    ed \
    expect \
    file \
    git \
    gnupg2 \
    iproute2 \
    iputils-ping \
    lcov \
    less \
    libc++-dev \
    libncurses5 \
    libssl-dev \
    llvm \
    llvm-dev \
    lsb-release \
    locales \
    netcat-openbsd \
    python-is-python3 \
    python2 \
    python2-dev \
    python3 \
    python3-dev \
    python3-pip \
    python3-requests \
    python3-setuptools \
    python3-six \
    python3-wheel \
    python3-yaml \
    software-properties-common \
    sudo \
    unzip \
    vim \
    wget \
    zip \
    zlib1g-dev \
    && \
    apt-get -y purge apport && \
    rm -rf /var/lib/apt/lists/*

# Workaround https://bugs.launchpad.net/ubuntu/+source/gcc-9/+bug/2029910
# TODO: remove when the latest ubuntu:20.04 image has the fix.
WORKDIR /tempdir
RUN ARCH="$(uname -m)" && \
    apt-get -y update && apt-get download libgcc-10-dev && \
    dpkg -x "libgcc-10-dev_10.5.0-1ubuntu1~20.04_${TARGETARCH}.deb" . && \
    cp "usr/lib/gcc/${ARCH}-linux-gnu/10/libtsan_preinit.o" "/usr/lib/gcc/${ARCH}-linux-gnu/9/" && \
    rm -rf /tempdir
WORKDIR /

# Allow using sudo inside the container.
RUN echo "ALL ALL=(ALL:ALL) NOPASSWD: ALL" >> /etc/sudoers

# Ensure that Bazel can use its beloved ISO-8859-1 locale.
RUN localedef -i en_US -f ISO-8859-1 en_US.ISO-8859-1

FROM ubuntu2004-bazel-nojdk AS ubuntu2004-nojdk

### Install Google Cloud SDK.
### https://cloud.google.com/sdk/docs/quickstart-debian-ubuntu
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
    apt-get update -y && apt-get install google-cloud-sdk -y && \
    rm -rf /var/lib/apt/lists/*

### Docker (for legacy rbe_autoconfig)
RUN apt-get -y update && \
    apt-get -y install apt-transport-https ca-certificates && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && \
    add-apt-repository "deb [arch=$TARGETARCH] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
    apt-get -y update && \
    apt-get -y install docker-ce && \
    rm -rf /var/lib/apt/lists/*

# Bazelisk
RUN LATEST_BAZELISK=$(curl -sSI https://github.com/bazelbuild/bazelisk/releases/latest | grep -i '^location: ' | sed 's|.*/||' | sed $'s/\r//') && \
    curl -Lo /usr/local/bin/bazel https://github.com/bazelbuild/bazelisk/releases/download/${LATEST_BAZELISK}/bazelisk-linux-${TARGETARCH} && \
    chown root:root /usr/local/bin/bazel && \
    chmod 0755 /usr/local/bin/bazel

# Buildifier
RUN LATEST_BUILDIFIER=$(curl -sSI https://github.com/bazelbuild/buildtools/releases/latest | grep -i '^location: ' | sed 's|.*/||' | sed $'s/\r//') && \
    curl -Lo /usr/local/bin/buildifier https://github.com/bazelbuild/buildtools/releases/download/${LATEST_BUILDIFIER}/buildifier-linux-${TARGETARCH} && \
    chown root:root /usr/local/bin/buildifier && \
    chmod 0755 /usr/local/bin/buildifier

FROM ubuntu2004-bazel-nojdk AS ubuntu2004-bazel-java11

RUN apt-get -y update && \
    apt-get -y install openjdk-11-jdk-headless && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME /usr/lib/jvm/java-11-openjdk-${TARGETARCH}

FROM ubuntu2004-nojdk AS ubuntu2004-java11

RUN apt-get -y update && \
    apt-get -y install openjdk-11-jdk-headless && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME /usr/lib/jvm/java-11-openjdk-${TARGETARCH}

FROM ubuntu2004-nojdk AS ubuntu2004

RUN apt-get -y update && \
    apt-get -y install openjdk-21-jdk-headless && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME /usr/lib/jvm/java-21-openjdk-${TARGETARCH}

FROM ubuntu2004 AS ubuntu2004-kythe

RUN LATEST_KYTHE=v0.0.68 && \
    mkdir /usr/local/kythe && \
    curl -fsSL https://github.com/kythe/kythe/releases/download/${LATEST_KYTHE}/kythe-{$LATEST_KYTHE}.tar.gz | \
    tar xvz --no-same-owner --strip-components 1 --directory /usr/local/kythe && \
    chmod -R a+r /usr/local/kythe && \
    test -f /usr/local/kythe/WORKSPACE

