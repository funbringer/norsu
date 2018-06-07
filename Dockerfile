FROM alpine

# Install dependencies
RUN apk add --no-cache \
	bash git \
	openssl curl \
	linux-headers \
	perl perl-ipc-run \
	build-base make musl-dev gcc bison flex coreutils \
	zlib-dev libedit-dev \
	python3 python3-dev py-virtualenv

# Environment
ENV LANG=C.UTF-8 PGDATA=/pg/data

# Make directories
RUN mkdir -p ${PGDATA} \
	mkdir -p /pg/testdir

# Add new user
RUN adduser postgres 2>&1 >/dev/null || true

# Grant privileges
RUN chown postgres:postgres ${PGDATA} && \
	chown postgres:postgres /pg/testdir

COPY run_tests.sh /run.sh
RUN chmod 755 /run.sh

ADD . /pg/testdir
WORKDIR /pg/testdir

USER postgres
ENTRYPOINT /run.sh
