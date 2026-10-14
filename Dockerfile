FROM alpine

# Install dependencies
RUN apk add --no-cache \
	bash git \
	openssl curl \
	linux-headers \
	perl perl-ipc-run \
	build-base make musl-dev gcc bison flex coreutils \
	zlib-dev libedit-dev \
	python3 python3-dev

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /usr/local/bin/

# Environment
ENV LANG=C.UTF-8 PGDATA=/pg/data \
	UV_PYTHON_PREFERENCE=only-system \
	UV_PROJECT_ENVIRONMENT=/tmp/venv \
	UV_CACHE_DIR=/tmp/uv-cache

# Make directories
RUN mkdir -p ${PGDATA} /pg/testdir

# Add new user
RUN adduser postgres 2>&1 >/dev/null || true

# Grant privileges
RUN chown postgres:postgres ${PGDATA} && \
	chown postgres:postgres /pg/testdir

COPY run_tests.sh /run.sh
RUN chmod 755 /run.sh

COPY --chown=postgres:postgres . /pg/testdir
WORKDIR /pg/testdir

USER postgres
ENTRYPOINT /run.sh
