FROM alpine:3.7

MAINTAINER Rishat Sharafiev <rishatsharafiev@ya.ru>

# apk install
# USER root
RUN apk add --update --no-cache --virtual .build-deps \
	shadow python3-dev libc-dev libc6-compat zlib-dev libffi-dev ca-certificates && \
	python3 -m ensurepip && \
	rm -r /usr/lib/python*/ensurepip && \
	pip3 install --upgrade pipenv

RUN apk add --update --no-cache python3 postgresql-dev gcc musl-dev libxslt-dev

# add user
# ARG PUID=1000
# ENV PUID ${PUID}
# ARG PGID=1000
# ENV PGID ${PGID}

# RUN addgroup -g ${PGID} user && \
#	adduser -u ${PUID} -h /app -D  -G user user && \
#	usermod -p "*" user

# install application
# USER root
ADD app /app
WORKDIR /app
RUN pipenv install --deploy --system --skip-lock

# apk del
# USER root
RUN apk del .build-deps && \
	rm -rf /var/cache/apk/* /root/.cache /tmp/*

### supervisor
EXPOSE 9001
RUN apk update && apk add git
RUN pip install git+https://github.com/Supervisor/supervisor # supervisor with support python 3
ADD supervisor /etc/supervisor
RUN mkdir /var/log/supervisor

ENTRYPOINT ["supervisord", "--nodaemon", "--configuration", "/etc/supervisor/supervisord.conf"]
