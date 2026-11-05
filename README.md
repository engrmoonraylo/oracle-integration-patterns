# Oracle Integration Patterns

Hands-on build walkthroughs, setup guides and reusable patterns for Oracle Integration 3 (OIC)
and Oracle Fusion Cloud Applications, based on real integration work. Walkthroughs show a
complete build from design to end-to-end testing; guides take you step by step through a
setup you can repeat in your own environments.

**Author:** Moon Ray Lo, Oracle ACE Apprentice  
**Products:** Oracle Integration 3 · Oracle Fusion Cloud Applications  
**Connect:** [LinkedIn](https://www.linkedin.com/in/moonraylo) ·
[Oracle ACE Directory](https://ace.oracle.com/ords/ace/oapt/profile/moonraylo) ·
[Real-World Oracle Integration newsletter](https://www.linkedin.com/newsletters/real-world-oracle-integration-7513260462159888384)

---

## Guides

Step-by-step setup guides with commands, settings, screenshots and troubleshooting.

|Guide|What it covers|Link|Updated|
|---|---|---|---|
|Oracle Fusion OAuth Setup Guide: Moving Off Basic Authentication|Moving Oracle Integration connections (ERP, HCM, REST, SOAP, BI Publisher) and external systems that call Fusion REST and SOAP APIs from username and password to OAuth 2.0 JWT User Assertion, before Oracle's March 31, 2027 deadline|[Open guide](guides/fusion-oauth/README.md)|Nov 2026|

---

## Build walkthroughs

Product usage walkthroughs, one build per document (PDF).

|#|Pattern|What it covers|Document|Date|
|-|---|---|---|---|
|01|Schedule integration invoking an app-driven integration|REST trigger connection, app-driven integration with GET and POST operations, scheduled integration calling it through the Local Integration adapter, mappings from runtime metadata, activation and end-to-end testing|[View PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage01_MoonRayLo_BuildSchedIntegrationAndInvokeAppDrivenIntegration.pdf)|Oct 24, 2026|
|02|JWT signing key with OCI Cloud Shell and OCI Vault|RSA key pair and certificate in Cloud Shell, private key stored and verified as an OCI Vault secret, signing key uploaded to Oracle Integration for OAuth JWT User Assertion|[View PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage02_MoonRayLo_JWTSigningKeyCloudShellAndVaultForOIC.pdf)|Oct 29, 2026|
|03|Fusion identity domain trust and JWT token test|Signing certificate imported as a trusted partner certificate, confidential application for JWT User Assertion with the Fusion scope, token and Fusion REST call proven from Cloud Shell|[View PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage03_MoonRayLo_FusionIdentityDomainJWTTokenTest.pdf)|Oct 29, 2026|
|04|Fusion connections on OAuth JWT User Assertion|REST, SOAP, BI Publisher, ERP Cloud and HCM Cloud adapter connections moved from password authentication to JWT User Assertion, BI Publisher proven with a run, ERP and HCM adapter Save-before-Test behavior|[View PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage04_MoonRayLo_OICFusionConnectionsJWTUserAssertion.pdf)|Oct 29, 2026|
|05|REST connection from Basic Auth to OAuth Client Credentials|Internal confidential application with consumer::all and /ic/api/ scopes and the ServiceDeveloper role, client secret in OCI Vault, Postman token and call tests, connection switched and tested|[View PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage05_MoonRayLo_OICRESTConnectionOAuthClientCredentials.pdf)|Oct 30, 2026|

Walkthroughs 02 to 04 show the build behind the Fusion OAuth guide in detail; walkthrough 05 covers callers into Oracle Integration with OAuth Client Credentials.

---

## Repository structure

```
oracle-integration-patterns/
├── docs/                 Build walkthroughs (PDF)
├── guides/
│   └── fusion-oauth/     Oracle Fusion OAuth setup guide (Markdown, images, scripts)
└── README.md
```

---

## About these documents

* Built in Oracle Integration and Oracle Fusion development environments.
* Environment identifiers are masked in all screenshots.
* To download a PDF, open it and use the download button at the top right.
* Guides render directly on GitHub; scripts are in each guide's `scripts` folder.
* Hardcoded values in the demos are for illustration; the patterns are meant
to be adapted to your own integrations.
* Oracle features change between releases: confirm each step against Oracle's
current documentation and test in non-production first.

---

## Feedback

Questions or suggestions are welcome. Open an issue in this repository or
connect with me on LinkedIn.

---

*Views and content are my own and do not represent my employer or Oracle.*

