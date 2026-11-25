FROM --platform=$BUILDPLATFORM debian:trixie-slim AS toolchain
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    gbdk_version=4.6.0; \
    case "$TARGETARCH" in \
      amd64) archive=gbdk-linux64.tar.gz; digest=c033dac026b99c080f07c2a659eb25976f65ca114cb15d1570bbb23c99c27e35 ;; \
      arm64) archive=gbdk-linux-arm64.tar.gz; digest=003bdb93b4a46702ec04cb9758be5032431deab024dff5637171183a7cea6f5b ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL --retry 3 -o "/tmp/$archive" \
      "https://github.com/gbdk-2020/gbdk-2020/releases/download/$gbdk_version/$archive"; \
    cd /tmp; \
    echo "$digest  $archive" | sha256sum -c -; \
    mkdir -p /opt/gbdk; \
    tar -xzf "$archive" --strip-components=1 -C /opt/gbdk \
      --exclude='*/examples' --exclude='*.pdf' --exclude='*/asmlnk_manual.txt'; \
    curl -fsSL --retry 3 -o /opt/gbdk/LICENSE \
      "https://raw.githubusercontent.com/gbdk-2020/gbdk-2020/$gbdk_version/LICENSE"; \
    echo '18095f7690d1565e267e51b2954bd59108231e0c5dd2d5837e226ddcb6f1c4f7  /opt/gbdk/LICENSE' | sha256sum -c -

FROM debian:trixie-slim
ARG DEV_UID=1000
ARG DEV_GID=1000

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git libstdc++6 libzstd1 make \
    && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libzstd1)" ge '1.5.7+dfsg-1+deb13u1' \
    && rm -rf /var/lib/apt/lists/* \
    && if ! getent group "$DEV_GID" >/dev/null; then groupadd --gid "$DEV_GID" dev; fi \
    && useradd --create-home --uid "$DEV_UID" --gid "$DEV_GID" --shell /bin/bash dev

COPY --from=toolchain /opt/gbdk /opt/gbdk
ENV GBDKDIR=/opt/gbdk/ PATH=/opt/gbdk/bin:$PATH

WORKDIR /workspace
USER dev
