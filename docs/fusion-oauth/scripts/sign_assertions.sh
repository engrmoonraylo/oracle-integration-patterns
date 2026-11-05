#!/usr/bin/env bash
# Build a JWT user assertion and client assertion for Fusion with OpenSSL only.
# Usage: ALIAS=<alias> CLIENT_ID=<client id> FUSION_USER=<integration user> \
#        KEY=private_key.pem ./sign_assertions.sh
# Prints export lines for USER_ASSERTION and CLIENT_ASSERTION. Never log them.
set -euo pipefail
: "${ALIAS:?}" "${CLIENT_ID:?}" "${FUSION_USER:?}" "${KEY:=private_key.pem}"

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
now=$(date +%s); exp=$((now + 1800))
hdr=$(printf '{"alg":"RS256","typ":"JWT","kid":"%s"}' "$ALIAS" | b64url)

mk() {
  local pl sig
  pl=$(printf '{"iss":"%s","sub":"%s","aud":"https://identity.oraclecloud.com/","iat":%d,"exp":%d,"jti":"%s"}' \
        "$CLIENT_ID" "$1" "$now" "$exp" "$(openssl rand -hex 16)" | b64url)
  sig=$(printf '%s.%s' "$hdr" "$pl" | openssl dgst -sha256 -sign "$KEY" | b64url)
  echo "$hdr.$pl.$sig"
}

echo "export USER_ASSERTION='$(mk "$FUSION_USER")'"
echo "export CLIENT_ASSERTION='$(mk "$CLIENT_ID")'"
