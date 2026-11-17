#!/usr/bin/env bash
# Build a JWT user assertion and client assertion for Fusion with OpenSSL only.
# Usage: export ALIAS=<alias> CLIENT_ID=<client id> FUSION_USER=<integration user> KEY=<private key file>
#        eval "$(bash sign_assertions.sh)"     # sets USER_ASSERTION and CLIENT_ASSERTION
# Without eval it only prints the export lines (useful for Postman). Never log them.
set -euo pipefail
: "${ALIAS:?}" "${CLIENT_ID:?}" "${FUSION_USER:?}" "${KEY:=private_key.pem}"
[ -r "$KEY" ] || { echo "Cannot read private key file: $KEY" >&2; exit 1; }

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
now=$(date +%s); exp=$((now + 1800))
hdr=$(printf '{"alg":"RS256","typ":"JWT","kid":"%s"}' "$ALIAS" | b64url)

mk() {
  local pl sig
  pl=$(printf '{"iss":"%s","sub":"%s","aud":"https://identity.oraclecloud.com/","iat":%d,"exp":%d,"jti":"%s"}' \
        "$CLIENT_ID" "$1" "$now" "$exp" "$(openssl rand -hex 16)" | b64url)
  sig=$(printf '%s.%s' "$hdr" "$pl" | openssl dgst -sha256 -sign "$KEY" | b64url)
  [ -n "$sig" ] || { echo "Signing failed. Check that $KEY is the private key." >&2; return 1; }
  echo "$hdr.$pl.$sig"
}

# Assign first so a signing failure stops the script instead of printing a broken assertion.
user_jwt=$(mk "$FUSION_USER")
client_jwt=$(mk "$CLIENT_ID")
echo "Signed for sub=$FUSION_USER, iss=$CLIENT_ID, kid=$ALIAS; valid for 30 minutes." >&2
echo "export USER_ASSERTION='$user_jwt'"
echo "export CLIENT_ASSERTION='$client_jwt'"
