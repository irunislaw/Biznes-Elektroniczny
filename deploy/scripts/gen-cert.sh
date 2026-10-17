#!/bin/sh
# Genetuje self-signed certyfikat dla localhost, jeśli jeszcze go nie ma.
set -eu 

DIR=deploy/certs
[ -f "$DIR/localhost.crt" ] && [ -f "$DIR/localhost.key" ] && exit 0

mkdir -p "$DIR"
# MSYS_NO_PATHCONV: bez tego Git Bash zamienia "/CN=localhost" na "C:/Program Files/Git/CN=localhost"
MSYS_NO_PATHCONV=1 openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout "$DIR/localhost.key" -out "$DIR/localhost.crt" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
echo "Wygenerowano certyfikat w $DIR"
