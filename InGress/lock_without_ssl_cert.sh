#!/bin/bash
# Temporarily unset SSL_CERT_FILE to fix certifi path issue
unset SSL_CERT_FILE
export REQUESTS_CA_BUNDLE=""
export CURL_CA_BUNDLE=""

cd "$(dirname "$0")"
poetry lock "$@"
