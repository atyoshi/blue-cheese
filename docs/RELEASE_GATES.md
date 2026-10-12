# Commercial release gates

Target: one customer's on-prem SOC with multiple analysts.

The current operational console ingests external Suricata alert/flow files,
preserves raw evidence, supports bounded investigations and exports, and persists
analyst actions and investigation work. It is still a localhost development release.

Before a commercial release:

- Implement and verify individual authentication, roles, session revocation and
  attributable actions. Current analyst names are entered manually.
- Verify the shared deployment, TLS, backup/recovery procedures and operational
  monitoring. Docker execution is currently unverified.
- Validate real model/server compatibility and detection quality on legally
  usable, labelled data. Rule outputs and synthetic fixtures are not accuracy evidence.
- Measure sustained ingestion, overload behaviour and retention capacity on the
  customer's target hardware. A finite-backlog benchmark is not a capacity guarantee.
- Validate source continuity and recovery against the deployed sensor's rotation
  policy. Missing archives and unsupported rotation patterns stop ingestion.
- Complete the remaining master-plan acceptance criteria in ROADMAP.md.

Native macOS testing and local Suricata integration have run successfully. No
commercial readiness or completed master-plan claim is made.
