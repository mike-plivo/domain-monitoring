FROM debian:bullseye-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
	openssl \
	git \
	g++ \
	curl \
	ca-certificates \
	redis-server \
	python3 \
	python3-dev \
	python3-pip
RUN rm -rf /var/lib/apt/lists/* || true

WORKDIR /app
# Install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir  -r requirements.txt
COPY *.py .
COPY entrypoint.sh .
RUN openssl req -newkey rsa:2048 -nodes -keyout /app/key.pem -x509 -days 365 -out /app/certificate.pem -subj "/C=US/ST=California/L=San Francisco/O=My Company Name/OU=My Division/CN=www.dummy.dummy/emailAddress=email@dummy.dummy"

RUN chmod 755 ./entrypoint.sh

#EXPOSE 50505

ENTRYPOINT ["/bin/bash", "-c", "./entrypoint.sh"]
