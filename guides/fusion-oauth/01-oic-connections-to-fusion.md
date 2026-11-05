# Guide 1: Oracle Integration Connections to Oracle Fusion with OAuth JWT User Assertion

**Oracle Integration 3 · ERP Cloud adapter · HCM Cloud adapter · REST adapter · SOAP adapter · BI Publisher**

[← Back to the overview](README.md)

This guide moves every Oracle Integration 3 (OIC) connection that calls Oracle Fusion Cloud Applications from a username and password to **OAuth using JWT User Assertion**. Do the whole sequence once per pairing (one OIC instance and the Fusion environment it calls), lowest environment first. Plan about half a day per pairing, plus a quiet window for switching the connections.

## Contents

- [How it works](#how-it-works)
- [At a glance](#at-a-glance)
- [Step 0: Prepare the pairing](#step-0-prepare-the-pairing)
- [Step 1: Confirm the Fusion integration user](#step-1-confirm-the-fusion-integration-user)
- [Step 2: Create the signing key pair](#step-2-create-the-signing-key-pair)
- [Step 3: Store the private key in a vault](#step-3-store-the-private-key-in-a-vault)
- [Step 4: Upload the private key to OIC](#step-4-upload-the-private-key-to-oic)
- [Step 5: Trust the certificate and create the confidential application](#step-5-trust-the-certificate-and-create-the-confidential-application)
- [Step 6: Prove the token before touching OIC](#step-6-prove-the-token-before-touching-oic)
- [Step 7: Check the BI Publisher OAuth property](#step-7-check-the-bi-publisher-oauth-property)
- [Step 8: Reconfigure the OIC connections](#step-8-reconfigure-the-oic-connections)
- [Step 9: Validate, promote and maintain](#step-9-validate-promote-and-maintain)
- [Alternative: Authorization Code](#alternative-authorization-code)
- [Troubleshooting](#troubleshooting)

## How it works

1. OIC signs a short JWT with its own private key. The JWT names the Fusion integration user (`sub`) and the confidential application (`iss`).
2. The Fusion environment's identity domain checks the signature against the certificate you trusted, and returns a short-lived access token for the Fusion scope.
3. OIC calls Fusion with `Authorization: Bearer <token>`.
4. Fusion runs the call as the integration user, with the same roles, data access and audit trail it has today.

What changes for you:

- Each Fusion connection changes its **security policy**. The integrations, mappings and schedules that use it don't change.
- The integration user and its roles stay. Only its password stops being used.
- You now look after two new things: the **private key** (in a vault) and the **certificate's expiry date**.

## At a glance

| # | Step | Where | Result |
|---|---|---|---|
| 0 | Identify the Fusion domain, home region, scope; inventory connections | OCI Console, OIC Connections | Pairing register |
| 1 | Confirm the integration user | Fusion Security Console | Active user, roles unchanged |
| 2 | Create the signing key pair | OCI Cloud Shell | Certificate (.cer) and private key |
| 3 | Store the private key | OCI Vault (or your approved vault) | Verified secret, local copies deleted |
| 4 | Upload the private key to OIC | OIC > Settings > Certificates | Signing key with the alias |
| 5 | Trust the certificate, create the app | Fusion identity domain, home region | Client ID |
| 6 | Prove the token outside OIC | Cloud Shell token script | Token 200, Fusion GET 200 |
| 7 | Check the BI Publisher OAuth property | BI Publisher Administration | Property True, or not listed on your release |
| 8 | Switch the connections one at a time | OIC Connections | All on JWT User Assertion, Configured |
| 9 | Validate, promote, maintain | OIC runs, next environment | Runtime proof, renewal owner |

> **Rules that matter**
>
> - Create everything in the **Fusion environment's identity domain**, with the console set to its **home region**.
> - One alias is used three times and must match everywhere: the OIC signing key alias, the certificate alias in the identity domain, and the `kid` in the JWT header.
> - **Prove the token before touching OIC**, then switch one connection at a time with the old settings recorded.
> - **ERP Cloud and HCM Cloud adapters: Save, Test, then Save again.** Testing before saving fails with CASDK-0005.
> - Your organization owns the key, the vault, the application and the certificate renewal. If a partner does the setup, hand these over before they leave.

## Step 0: Prepare the pairing

### 0.1 Find the domain, region and scope

Follow [Three facts to establish first](README.md#three-facts-to-establish-first) in the overview. The OIC instance's own identity domain doesn't matter for JWT User Assertion; only the Fusion environment's domain does.

![Fusion scope on the Oracle Applications Cloud (Fusion) service](images/oic/02-fusion-scope.png)

> **Don't reuse an OIC scope.** Scopes for calling OIC also end in `consumer::all`, but they start with the OIC audience host. A Fusion connection needs the Fusion audience. A token requested with the wrong one fails with `invalid_scope` or is rejected by Fusion with 401.

### 0.2 Record the pairing

Keep one row per pairing with the environment's setup record. It's your checklist for the rest of this guide.

| Field | Example |
|---|---|
| Pairing | OIC `<OIC ENV>` calls Fusion `<FUSION ENV>` |
| Fusion domain, URL, home region | `fa-<pod>-<env>-<suffix>`, `https://idcs-<id>.identity.oraclecloud.com`, US West (Phoenix) |
| Fusion host | `https://<pod>.fa.<dc>.oraclecloud.com` (copy from the sign-in URL) |
| Fusion scope | Copied from the console |
| Integration user | `SVC_OIC_<ENV>` |
| Certificate alias and expiry | `<ORG>_OIC_FusionJWT_<OIC ENV>_CERT`, expires `<date>` |
| Confidential app and client ID | `<ORG>_FusionJWTClient_<OIC ENV>_APP`, client ID |
| Tests passed | Token test, each connection test, smoke tests, with date and tester |

### 0.3 Inventory the connections

1. In OIC, open **Design > Connections** (and each project's Connections section) and filter on the ERP Cloud, HCM Cloud, REST and SOAP adapters.
2. List every connection whose URL points to the Fusion host and whose security policy is **Username Password Token**, **Username Password Token With PGP Key Support** or **Basic Authentication**.
3. For each one, record the integrations that use it, the owning project, whether it's shared across projects, and whether it calls BI Publisher (`/xmlpserver/services/...`).
4. Flag ERP or HCM connections used for business event subscriptions. Those subscribed integrations get retested after the switch.

### 0.4 Access you need

| Where | Access |
|---|---|
| OCI Console, Fusion identity domain | Identity domain administrator |
| Oracle Integration | ServiceAdministrator (or ServiceDeveloper for connections) |
| Fusion Security Console | IT Security Manager, only if the user or its roles must change |
| BI Publisher | BI Administrator, for Step 7 |
| Vault | Write access to your approved vault |

## Step 1: Confirm the Fusion integration user

1. Confirm a dedicated integration user exists in Fusion, named for its purpose, never a person's account. Give it only the roles the interfaces need.
2. In the Fusion identity domain, open **User management** and confirm the same user is listed. Fusion users are synchronized to this domain automatically.
3. Keep the username exactly as it is, including case. It becomes the JWT `sub` claim.

No roles are added for OAuth. The user keeps the access its integrations need today.

![Integration user in the Fusion Security Console](images/oic/03-integration-user.png)

## Step 2: Create the signing key pair

Create one key pair per OIC instance and never reuse it across instances. Name the alias with a pattern such as `<ORG>_OIC_FusionJWT_<OIC ENV>_CERT` (50 characters at most).

You need two files: an RSA 2048 private key in PEM format (PKCS#8) for OIC, and a self-signed X.509 certificate for the identity domain.

### 2.1 Option A: OCI Cloud Shell (recommended)

Cloud Shell runs in the browser from the OCI Console with OpenSSL preinstalled. Nothing is installed, and the key is created inside your own tenancy rather than on a laptop. If the Cloud Shell icon doesn't open, your group needs an IAM policy that allows `use cloud-shell in tenancy`.

1. Sign in to the OCI Console and select **Developer tools > Cloud Shell** (the **>_** icon at the top right).
2. Generate the key pair in a folder only you can read:

```bash
umask 077
mkdir -p ~/fusion-oauth && cd ~/fusion-oauth
ALIAS=<ORG>_OIC_FusionJWT_<OIC_ENV>_CERT
openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes \
  -keyout ${ALIAS}_private_key.pem -out ${ALIAS}.cer -subj "/CN=${ALIAS}"
```

3. Verify the files without displaying the key:

```bash
openssl x509 -in ${ALIAS}.cer -noout -subject -enddate -fingerprint -sha256
head -1 ${ALIAS}_private_key.pem
[ "$(openssl x509 -in ${ALIAS}.cer -noout -modulus)" = \
  "$(openssl rsa -in ${ALIAS}_private_key.pem -noout -modulus)" ] && echo "Key and certificate match"
```

| Check | Pass when |
|---|---|
| Subject | `CN=` followed by the alias |
| Expiry | About 365 days from today. Record it in the certificate register now. |
| Key format | First line is `-----BEGIN PRIVATE KEY-----` (PKCS#8) |
| Pair | The last command prints `Key and certificate match` |

![Key pair created and verified in Cloud Shell](images/oic/05-cloudshell-keypair.png)

4. In the Cloud Shell pane, open **Menu > Download**. Enter one path at a time, relative to the home directory: `fusion-oauth/<alias>.cer`, then `fusion-oauth/<alias>_private_key.pem`. If a relative path is rejected, use `/home/<cloud-shell-user>/fusion-oauth/<file name>`. Confirm both downloads match the sizes `ls -l` shows.

![Downloading the certificate from Cloud Shell](images/oic/06-cloudshell-download.png)

5. Delete the private key from Cloud Shell and your Downloads folder only after Step 3 passes and Step 4 is done (see [Clean up](#34-clean-up)).

> Never `cat` the private key or screenshot its contents. A screenshot of the verification output is safe evidence for the setup record.

### 2.2 Option B: other free tools

| Tool | Notes |
|---|---|
| OpenSSL on a workstation | Git Bash on Windows, or macOS, Linux and WSL. Same command as Cloud Shell. |
| PowerShell 7.4 or later | .NET can create the key and certificate without touching the Windows certificate store. Not available in Windows PowerShell 5.1. |
| KeyStore Explorer | Free GUI (needs Java). Generate RSA 2048, SHA-256, 365 days, alias as CN, then export the private key as PKCS#8 PEM and the certificate as PEM. |

Rules for any option:

- Never use an online key generator.
- Keep validity at 12 months or less, and record the expiry with an owner and a 30-day alert the day you create it.
- The key must be unencrypted, or you'll enter its password when uploading to OIC. OIC accepts PKCS#1 and PKCS#8.
- Never email the private key, paste it into chat or a ticket, or leave it on a shared drive.

## Step 3: Store the private key in a vault

If you run OCI, OCI Vault is a sound, free home for signing keys: the key stays in your tenancy and your administrators control access. Agree the vault with your security team first.

### 3.1 Decisions

| Decision | Guidance |
|---|---|
| Vault type | Default virtual vault (leave **Make it a virtual private vault** unchecked). Secrets are free; a virtual private vault is a dedicated HSM partition billed by the hour. |
| Master key | Software protection, AES 256. |
| Compartment | Not root. A dedicated compartment, or one owned by your security team. Don't add secrets to a vault another team built for its own purpose. |
| Names | Vault `<org>-integration-vault-<region>`, key `<org>-integration-mek`, secret `<alias>_PRIVATE_KEY` |
| Tags | `Owner` = the team accountable after go-live, `Purpose`, and optionally `ImplementedBy` |
| Access | Policies name groups, never individuals, and are limited to the vault |

![Integration vault created](images/oic/07-vault.png)

![Vault tags showing the owning team](images/oic/08-vault-tags.png)

![Master encryption key](images/oic/09-vault-master-key.png)

### 3.2 Create the secret from Cloud Shell

Run this in the folder holding the key:

```bash
VAULT=<vault OCID>
KEY=<master key OCID>
COMP=$(oci kms management vault get --vault-id $VAULT --query 'data."compartment-id"' --raw-output)
SECRET=$(oci vault secret create-base64 \
  --compartment-id $COMP --vault-id $VAULT --key-id $KEY \
  --secret-name ${ALIAS}_PRIVATE_KEY \
  --description "<OIC env> JWT signing key for <Fusion env>; expires <date>" \
  --freeform-tags '{"Owner":"<owning team>","Purpose":"OIC to Fusion OAuth signing keys"}' \
  --secret-content-content "$(base64 -w0 ${ALIAS}_private_key.pem)" \
  --query 'data.id' --raw-output)
echo "Secret: $SECRET"
```

### 3.3 Verify the stored copy

After about a minute, both hashes must match:

```bash
oci secrets secret-bundle get --secret-id $SECRET \
  --query 'data."secret-bundle-content".content' --raw-output | base64 -d | \
  openssl rsa -noout -modulus | sha256sum
openssl rsa -in ${ALIAS}_private_key.pem -noout -modulus | sha256sum
```

If the first command prints `e3b0c442...b855` with `base64: invalid input`, `$SECRET` is empty and the secret was never created. Run the create step again and check that it prints an `ocid1.vaultsecret` value.

![Secret stored in the vault](images/oic/10-vault-secret.png)

### 3.4 Clean up

Only after the hashes match and Step 4 is done, delete the private key from Cloud Shell (its home directory persists between sessions) and from your local Downloads folder. The certificate is public and can stay.

```bash
shred -u ~/fusion-oauth/*_private_key.pem && ls -l ~/fusion-oauth
```

![Private key shredded in Cloud Shell](images/oic/11-cloudshell-shred.png)

## Step 4: Upload the private key to OIC

1. In OIC, open **Settings > Certificates** and select **Upload**.
2. Enter the alias, set **Type** to **Signing key**, select **Private**, and upload `<alias>_private_key.pem`. Enter a password only if the key is encrypted.
3. Select **Upload** and confirm the key is listed with the alias you expect.

![Uploading the signing key in OIC](images/oic/12-oic-upload-signing-key.png)

- The list shows the key as type SIGNKEY, category Private, status Configured, with an empty **Expiration** column. OIC holds only the private key, and the expiry date lives in the certificate, so **OIC's certificate expiry warnings don't cover JWT signing keys**. Track the renewal yourself.
- Put the expiry date, the vault location and the owning team in the **Description**, so whoever maintains the instance later can find them.

![Signing key listed in OIC Certificates](images/oic/13-oic-certificate-list.png)

## Step 5: Trust the certificate and create the confidential application

Set the OCI Console region to the Fusion domain's **home region** and open that domain.

### 5.1 Import the trusted partner certificate

1. Open **Security > Trusted partner certificates > Import certificate**.
2. Upload `<alias>.cer` and set the alias to the same `<alias>`.

![Trusted partner certificate imported](images/oic/14-trusted-partner-certificate.png)

### 5.2 Create the confidential application

1. Open **Integrated applications > Add application**, select **Confidential Application**, then **Launch workflow**.
2. Name it, for example `<ORG>_FusionJWTClient_<OIC ENV>_APP`, and record the OIC instance and Fusion environment in **Description**. Select **Submit**.
3. On **OAuth configuration**, select **Edit OAuth configuration** and **Configure this application as a client now**.
4. Under **Authorization**, select **JWT assertion**.
5. Set **Client type** to **Trusted**, select **Import certificate**, upload `<alias>.cer`, and set the certificate alias to `<alias>`. It must equal the JWT `kid`.
6. In **Token issuance policy**, set **Authorized resources** to **Specific**, turn on **Add resources**, select **Add scope**, select the Fusion Applications resource and select **Add**. Depending on the domain it's listed as **Oracle Applications Cloud (Fusion)** or **Fusion Applications Cloud Service**. Confirm the scope matches your pairing register.
7. Under **Client IP address**, select **Anywhere**, or a network perimeter with OIC's outbound IP addresses. The form won't save with neither selected.
8. Select **Submit**, then **Actions > Activate > Activate application**.
9. Record the **Client ID**. The page also shows a client secret, because identity domains create one for every confidential application. JWT User Assertion never uses it, so don't copy or store it.

![Confidential application OAuth configuration](images/oic/15-confidential-app.png)

- A banner may suggest configuring a web tier policy. It doesn't apply here.
- If the Fusion resource isn't offered under **Add scope**, create a resource application as described in Oracle's ERP Cloud adapter documentation (primary audience `https://<fusion-host>:443`, scope `/`) and add its scope instead.

> **If a key is ever exposed** in a screenshot, chat, ticket or email, treat it as compromised. Create a new key pair and alias, update the vault and every OIC connection that uses it, and retest.

## Step 6: Prove the token before touching OIC

A connection is shared by every integration that uses it, so prove the identity setup on its own first. [`scripts/token_test.py`](scripts/token_test.py) builds the user assertion and client assertion the way Oracle documents for the JWT User Assertion grant, requests a token from the Fusion domain, and calls one Fusion REST resource with it. It prints status codes and claims, never the token.

Run it where the private key is held, for example Cloud Shell:

```bash
pip install --user pyjwt cryptography requests
python3 token_test.py
```

| Check | Pass when | If it fails |
|---|---|---|
| Token request | 200, and `sub` is the integration user | `invalid_grant`, `invalid_client` or `invalid_scope` point to the assertion, the trust setup or the scope. See [Troubleshooting](#troubleshooting). |
| Fusion GET | 200 | 401: token from another domain, or the user is missing in that Fusion environment. 403: the user lacks the role for that resource. |

![Token test passing](images/oic/16-token-test.png)

- Never paste a token into an online decoder. The script decodes it locally.
- If you've already deleted the working copy of the key, read it from the vault into a temporary file with `umask 077`, run the script, then `shred -u` the file.
- The access token's lifetime follows the `exp` in the user assertion (300 seconds in the script). OIC recalculates `exp` on every token request, so connections aren't affected.

## Step 7: Check the BI Publisher OAuth property

Oracle's Analytics Publisher Developer's Guide (October 2026) documents a BI administrator property, **Enable OAuth for SOAP Webservices**, alongside JWT User Assertion support for the BI Publisher SOAP web services. Whether you see it depends on your Fusion release, so check before you switch any BI Publisher connection.

1. Sign in to Fusion as a BI administrator and open the BI Publisher **Administration** page: from the analytics catalog (`https://<fusion-host>/analytics`), select **Administration > Manage Publisher**, or go straight to `https://<fusion-host>/xmlpserver/servlet/admin`.
2. Under **Runtime Configuration**, select **Properties**.
3. Scroll to **All Outputs**.
   - **If Enable OAuth for SOAP Webservices is listed**, set it to **True** and select **Apply**, as Oracle documents. Record who changed it and when, and repeat in every environment along the promotion path.
   - **If it isn't listed**, leave the page as it is. On a 26C pod (11.13.26.07.0) the property wasn't there, and BI Publisher still accepted the JWT User Assertion token: from the OIC SOAP adapter and from a direct SOAP call (Guide 2, Step 6).

![All Outputs on a 26C pod: no Enable OAuth for SOAP Webservices property](images/oic/17-bip-enable-oauth-property.png)

*All Outputs on a 26C pod. The Enable OAuth for SOAP Webservices property isn't listed, and runReport still accepted the OAuth token.*

## Step 8: Reconfigure the OIC connections

> **Change one connection at a time, in a quiet window.** Edit the connection, test it, save it, then smoke-test each dependent integration before moving to the next. Keep the old settings recorded until the environment is signed off.

### 8.1 Prepare the JWT files

One pair of files per pairing. The same files serve the ERP, HCM, REST and SOAP connections.

`jwt_header.json`

```json
{ "alg": "RS256", "typ": "JWT", "kid": "<alias>" }
```

`jwt_payload.json`

```json
{ "iss": "<confidential app client ID>",
  "sub": "<Fusion integration user>",
  "aud": "https://identity.oraclecloud.com/",
  "iat": 1, "exp": 1, "jti": "1" }
```

- OIC requires `iss`, `sub`, `aud` and `exp`, and recalculates `iat`, `exp`, `nbf` and `jti` at runtime, so the placeholder numbers are fine.
- `aud` must be exactly `https://identity.oraclecloud.com/`, including the trailing slash.
- `sub` is the identity for Test and at runtime. Leave the subject unmapped in integrations unless you deliberately use identity propagation.

### 8.2 Oracle ERP Cloud and Oracle HCM Cloud adapters

| Field | Value |
|---|---|
| Security policy | OAuth using JWT User Assertion |
| Access Token URI | `https://<fusion-domain-host>/oauth2/v1/token` (the **Fusion** domain URL, not OIC's) |
| JWT headers in JSON format | Upload `jwt_header.json` |
| JWT payload in JSON format | Upload `jwt_payload.json` |
| JWT private key alias | `<alias>` |
| Scope | The Fusion scope from the pairing register |
| Host / service catalog URL | Unchanged |

For these two adapters the order matters: enter the JWT values, select **Save** (status becomes Draft), then **Test** (**Validate and Test** where offered), then **Save** again so the status returns to Configured.

> **Save before you Test on the ERP and HCM adapters.** They test against the saved connection, not the values on screen. Testing before saving fails with `CASDK-0005 Valid JWT access token is not available ... Cannot invoke String.length() because text is null`, even when every value is right. Because the first Save switches a live connection, do it in a quiet window and roll back if the Test after it fails. Never leave the connection in Draft.

![ERP Cloud adapter connection on JWT User Assertion](images/oic/18-erp-adapter-jwt.png)

### 8.3 REST adapter calling Fusion REST APIs

| Field | Value |
|---|---|
| Connection type and URL | REST API Base URL, for example `https://<fusion-host>` (no trailing slash) |
| Security policy | OAuth using JWT User Assertion |
| Access Token URI, JWT files, private key alias, scope | Same as 8.2 |
| Access token request | Leave blank unless the token request fails (see Troubleshooting) |

Test against a read-only GET resource, then **Save**. The REST and SOAP adapters can test before saving.

### 8.4 SOAP adapter calling Fusion SOAP services, including BI Publisher

The SOAP adapter's invoke security now includes **OAuth using JWT User Assertion** (Oracle Integration 26.10). If you don't see it in the **Security policy** list on your instance, use the Authorization Code alternative below.

| Field | Value |
|---|---|
| WSDL URL | Unchanged, for example `https://<fusion-host>/xmlpserver/services/ExternalReportWSSService?WSDL` |
| Security policy | OAuth using JWT User Assertion |
| Access Token URI, JWT files, private key alias | Same as 8.2 |
| Optional security > Scope | The Fusion scope from the pairing register |

Select **Validate and Test**, then **Save**. For BI Publisher, a passing Test proves only the WSDL and the token request. The real proof is a `runReport` call that returns `reportBytes` with real data.

![BI Publisher SOAP connection on JWT User Assertion](images/oic/19-bip-soap-connection.png)

![runReport response with report data](images/oic/20-bip-runreport-response.png)

![All Fusion connections Configured](images/oic/21-all-connections-configured.png)

## Step 9: Validate, promote and maintain

### 9.1 Validation checklist

| # | Check | Pass when |
|---|---|---|
| 1 | Placement | Certificate and app are in the Fusion domain, created in its home region |
| 2 | Token test | Step 6 returns 200 for the token and for the Fusion GET |
| 3 | Connection tests | Every changed connection tests successfully and shows Configured |
| 4 | Smoke tests | One representative run each: a REST flow, a SOAP flow, a bulk (FBDI or HDL) flow |
| 5 | BI Publisher | `runReport` returns output under OAuth; scheduled reports submit and complete |
| 6 | Business events | One subscribed integration per event connection is reactivated and receives an event |
| 7 | Audit | Fusion shows the integration user, not a person |
| 8 | No passwords left | No Fusion connection still uses Username Password Token or Basic Authentication |
| 9 | Secrets | The private key exists only in OIC and the vault |
| 10 | Lifecycle | Certificate expiry recorded with an owner and a 30-day alert |

### 9.2 Promote to the next environment

Repeat Steps 0 to 9.1 for each pairing along the promotion path, finishing production before March 31, 2027. Each pairing has its own Fusion domain values, client ID and key pair. After importing integrations into another OIC instance, open each Fusion connection, confirm its security values belong to that instance's pairing, and test before activating.

### 9.3 Rotate the certificate before it expires

1. At the 30-day alert, create a new key pair with a new alias.
2. Import the new certificate on the confidential app and under Trusted partner certificates, keeping the old one in place.
3. Upload the new private key in OIC under the new alias.
4. Update `kid` in `jwt_header.json`, upload it, and set the new **JWT private key alias** on each connection. Test and smoke-test.
5. Remove the old certificate from the app, Trusted partner certificates and OIC.

After any Fusion environment refresh, rerun the token test and the connection tests for every pairing that calls it.

### 9.4 Ownership

Certificates last a year, so the first renewal usually lands long after the project team has moved on. Before go-live support ends, make sure a named owner in your organization holds the certificate register and the renewal alert, the vault access, the integration user's notifications, and the confidential application.

## Alternative: Authorization Code

Use Authorization Code only when JWT User Assertion isn't an option for a pairing, for example when a signing key can't be managed or your security policy requires a consented sign-in. Don't mix the two on one connection.

1. Create a second confidential application with **Authorization code** and **Refresh token**, the OIC callback as **Redirect URL**, client type **Confidential**, and the Fusion scope. Activate it and put the client secret straight into the vault.

   | OIC instance | Redirect URL |
   |---|---|
   | Created new on Oracle Integration 3 | `https://<instance-URL>.<region>.ocp.oraclecloud.com/icsapis/agent/oauth/callback` |
   | Upgraded from Oracle Integration Generation 2 | `https://<instance-URL>.ocp.oraclecloud.com/icsapis/agent/oauth/callback` |

2. On the connection, select **OAuth Authorization Code Credentials** with Authorization Code URI `https://<fusion-domain-host>/oauth2/v1/authorize`, Access Token URI `https://<fusion-domain-host>/oauth2/v1/token`, scope `<Fusion scope> offline_access` (one space before `offline_access`), and **Send client credentials as basic auth header**.
3. Select **Provide Consent** and sign in **as the integration user**, in a private browser window so your own session isn't reused. If OIC and Fusion share an identity domain, consent is given by whoever is signed in to OIC, so sign in to OIC as the integration user for that step.
4. Test, Save, and run one integration. Record the consent date and a named owner for re-consent.

If a connection starts failing with 401 after weeks of working, the refresh token has lapsed: give consent again as the integration user.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `invalid_grant: invalid user assertion` | Assertion doesn't match the trust setup | Check `aud` (trailing slash), `kid` = certificate alias on the app and in Trusted partner certificates, `iss` = client ID, `sub` exists in the Fusion domain, and the clock is correct |
| `invalid_client` on a JWT connection | Client authentication not accepted | Fill **Access token request** with: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=<user_assertion>&scope=<scope>&client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer&client_assertion=<client_assertion>`. Raise an SR if it still fails. |
| `invalid_scope` | Scope typed, split by a space, or copied from OIC | Copy the Fusion scope from the console |
| Token rejected straight away, or client not found | Access Token URI points to OIC's domain, or the app was created in the wrong domain | Use the Fusion domain URL; recreate the app in the domain that lists the Fusion service |
| New app or certificate seems missing | Created or viewed in a replica region | Switch to the home region and retry after a few minutes |
| 401 from Fusion with a valid token | Token from another domain (for example DEV1's domain calling the DEV2 host), or the user doesn't exist there | Match the domain to the Fusion host; confirm the user in that environment |
| 403 from Fusion | Integration user lacks the role | Add the role and retest |
| BI Publisher call rejected under OAuth | OAuth property listed but not set to True, or report or data access missing | Check Step 7, then the user's access to the report path |
| ERP/HCM adapter: `CASDK-0005 ... text is null` at Test | Tested before saving | Save, Test, Save again (8.2) |
| Authorization Code: consent works, Test returns 401 | Consent given by an account not in Fusion | Give consent again as the integration user |
| Events stop after the switch | Subscription created under the old security | Reactivate the subscribed integration in non-production first |

---

[← Back to the overview](README.md) · [Guide 2: External systems to Fusion →](02-external-systems-to-fusion.md)

*Moon Ray Lo, Oracle ACE Apprentice. The postings on this site are my own and do not represent Huron's positions, strategies or opinions. Confirm each step against Oracle's current documentation for your release.*
