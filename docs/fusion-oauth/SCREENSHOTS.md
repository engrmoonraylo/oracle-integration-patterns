# Screenshot List

[← Back to the overview](README.md)

Each step in the guides points to a screenshot in the `images` folder. This list shows what each one captures and what to mask before it's published.

## What to mask

- Environment identifiers: OCIDs, tenancy and compartment names, POD and host names, identity domain IDs (`idcs-<id>`), and instance URLs.
- Client IDs and any value that identifies an organization (for example an organization prefix in an alias or application name). Keep the generic part readable.
- Email addresses and personal usernames.
- Never capture a private key, an assertion, an access token or a client secret, even masked.

Mask with a solid block, not blur. Keep the clicked or selected element highlighted with one simple outline.

## Guide 1: OIC connections to Fusion

| File | Step | What it shows |
|---|---|---|
| `images/oic/01-identity-domain-home-region.png` | Overview | Fusion identity domain Details page with the Home region |
| `images/oic/02-fusion-scope.png` | 0.1 | Oracle Applications Cloud (Fusion) service, OAuth configuration, primary audience and scope |
| `images/oic/03-integration-user.png` | 1 | Integration user in the Fusion Security Console |
| `images/oic/04-integration-user-roles.png` | 1 | The user's roles, unchanged |
| `images/oic/05-cloudshell-keypair.png` | 2.1 | Cloud Shell: key pair created and the verification output, including "Key and certificate match" |
| `images/oic/06-cloudshell-download.png` | 2.1 | Cloud Shell Menu > Download with the relative file path |
| `images/oic/07-vault.png` | 3.1 | Vault created in its compartment |
| `images/oic/08-vault-tags.png` | 3.1 | Vault tags: Owner, Purpose |
| `images/oic/09-vault-master-key.png` | 3.1 | Master encryption key, software protection, AES 256 |
| `images/oic/10-vault-secret.png` | 3.3 | Secret listed, and the two matching hashes |
| `images/oic/11-cloudshell-shred.png` | 3.4 | `shred -u` and the remaining `.cer` file |
| `images/oic/12-oic-upload-signing-key.png` | 4 | OIC Upload certificate: alias, Signing key, Private |
| `images/oic/13-oic-certificate-list.png` | 4 | SIGNKEY listed as Configured with an empty Expiration column |
| `images/oic/14-trusted-partner-certificate.png` | 5.1 | Trusted partner certificate imported with the alias |
| `images/oic/15-confidential-app.png` | 5.2 | Confidential app OAuth configuration: JWT assertion, Trusted, certificate alias, Fusion resource |
| `images/oic/16-token-test.png` | 6 | Token test output: Token request 200, sub, Fusion GET 200 |
| `images/oic/17-bip-enable-oauth-property.png` | 7 | BI Publisher Runtime Configuration: Enable OAuth for SOAP Webservices = True |
| `images/oic/18-erp-adapter-jwt.png` | 8.2 | ERP Cloud adapter connection on OAuth using JWT User Assertion, Configured |
| `images/oic/19-bip-soap-connection.png` | 8.4 | SOAP adapter connection to ExternalReportWSSService on OAuth using JWT User Assertion |
| `images/oic/20-bip-runreport-response.png` | 8.4 | runReport response with reportBytes returned |
| `images/oic/21-all-connections-configured.png` | 8.4 | All Fusion connections switched and Configured |

## Guide 2: External systems to Fusion

| File | Step | What it shows |
|---|---|---|
| `images/external/01-trusted-partner-certificate.png` | 4.1 | The external system's certificate imported with its alias |
| `images/external/02-confidential-app.png` | 4.2 | The system's confidential app: JWT assertion only, Trusted, Fusion resource |
| `images/external/03-postman-token.png` | 6 | Postman token request returning 200 (token value hidden) |
| `images/external/04-postman-rest.png` | 6 | Postman REST GET with Bearer token returning 200 |
| `images/external/05-postman-soap.png` | 6 | Postman SOAP call with Bearer token returning a valid response |
