FROM alpine:latest
RUN apk add --no-cache openssl python3 py3-pip
WORKDIR /app