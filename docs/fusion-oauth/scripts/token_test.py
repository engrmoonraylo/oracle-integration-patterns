"""Prove a Fusion JWT User Assertion setup before changing a live connection.

Requests a token from the Fusion environment's identity domain, then calls one
read-only Fusion REST resource with it. Prints status codes and claims only,
never the token.

Usage:  pip install pyjwt cryptography requests
        python3 token_test.py
Run it where the private key is held (for example OCI Cloud Shell), then
delete the key file.
"""
import time
import uuid

import jwt
import requests

DOMAIN = "https://idcs-<id>.identity.oraclecloud.com"   # Fusion identity domain URL
CLIENT_ID = "<confidential app client ID>"              # JWT iss
ALIAS = "<ORG>_OIC_FusionJWT_<OIC_ENV>_CERT"            # certificate alias = JWT kid
USER = "<Fusion integration user>"                      # JWT sub
SCOPE = "<Fusion scope from the console>"
FUSION = "https://<fusion-host>"
GET_PATH = "/hcmRestApi/resources/latest/workers?limit=1"  # any read-only resource the user may call

key = open(ALIAS + "_private_key.pem").read()


def assertion(sub):
    now = int(time.time())
    claims = {"iss": CLIENT_ID, "sub": sub, "aud": "https://identity.oraclecloud.com/",
              "iat": now, "exp": now + 300, "jti": str(uuid.uuid4())}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": ALIAS, "typ": "JWT"})


r = requests.post(DOMAIN + "/oauth2/v1/token", timeout=30, data={
    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
    "assertion": assertion(USER),
    "scope": SCOPE,
    "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
    "client_assertion": assertion(CLIENT_ID)})
print("Token request:", r.status_code)
if r.status_code != 200:
    print(r.text)
    raise SystemExit(1)

tok = r.json()["access_token"]
claims = jwt.decode(tok, options={"verify_signature": False})
print("sub:", claims.get("sub"), "| expires in", claims["exp"] - int(time.time()), "s")

g = requests.get(FUSION + GET_PATH, headers={"Authorization": "Bearer " + tok}, timeout=60)
print("Fusion GET:", g.status_code)
