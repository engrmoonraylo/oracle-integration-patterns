# Oracle Integration Patterns

Hands-on build walkthroughs and reusable patterns for Oracle Integration 3 (OIC),
based on real integration work. Each document shows a complete build from
design to end-to-end testing, with screenshots, mappings and runtime results.

**Author:** Moon Ray Lo, Oracle ACE Apprentice  
**Product:** Oracle Integration 3  
**Connect:** [LinkedIn](https://www.linkedin.com/in/moonraylo) ·
[Oracle ACE Directory](https://ace.oracle.com/ords/ace/oapt/profile/moonraylo) ·
[Real-World Oracle Integration newsletter](https://www.linkedin.com/newsletters/real-world-oracle-integration-7513260462159888384)

---

## Contents

| # | Pattern | What it covers | Document | Date |
|---|---------|----------------|----------|------|
| 01 | Schedule integration invoking an app-driven integration | REST trigger connection, app-driven integration with GET and POST operations, scheduled integration calling it through the Local Integration adapter, mappings from runtime metadata, activation and end-to-end testing | [Download PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage01_MoonRayLo_BuildSchedIntegrationAndInvokeAppDrivenIntegration.pdf?raw=true) | Oct 24, 2026 |
| 02 | JWT signing key with OCI Cloud Shell and OCI Vault | RSA key pair and certificate in Cloud Shell, private key stored and verified as an OCI Vault secret, signing key uploaded to Oracle Integration for OAuth JWT User Assertion | [Download PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage02_MoonRayLo_JWTSigningKeyCloudShellAndVaultForOIC.pdf?raw=true) | Oct 29, 2026 |
| 03 | Fusion identity domain trust and JWT token test | Signing certificate imported as a trusted partner certificate, confidential application for JWT User Assertion with the Fusion scope, token and Fusion REST call proven from Cloud Shell | [Download PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage03_MoonRayLo_FusionIdentityDomainJWTTokenTest.pdf?raw=true) | Oct 29, 2026 |
| 04 | Fusion connections on OAuth JWT User Assertion | REST, SOAP, BI Publisher, ERP Cloud and HCM Cloud adapter connections moved from password authentication to JWT User Assertion, BI Publisher proven with a run, ERP and HCM adapter Save-before-Test behavior | [Download PDF](https://github.com/engrmoonraylo/oracle-integration-patterns/blob/main/docs/OICProductUsage04_MoonRayLo_OICFusionConnectionsJWTUserAssertion.pdf?raw=true) | Oct 29, 2026 |

---

## Repository structure

```
oracle-integration-patterns/
├── docs/        Build walkthroughs (PDF)
└── README.md
```

---

## About these documents

- Built in Oracle Integration development environments.
- Environment identifiers are masked in all screenshots.
- Hardcoded values in the demos are for illustration; the patterns are meant
  to be adapted to your own integrations.

---

## Feedback

Questions or suggestions are welcome. Open an issue in this repository or
connect with me on LinkedIn.

---

*Views and content are my own and do not represent my employer or Oracle.*
