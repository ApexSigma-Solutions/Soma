---
created: Thu, 29th January 2026 23:47
modified: Thu, 29th January 2026 23:48
---

# Spec: MAR Protocol (Mandatory Agent Review) v2.0

## Overview

The MAR Protocol is the mandatory quality gate and control step within the ApexSigma implementation workflow. No task is "Done" until it passes this gate.

## Standards

- **Strategic Alignment**: Does the implementation meet the "Why" defined in the TNP?
- **Technical Accuracy**: Is the code performant, idiomatic (Python 3.12.10/Poetry), and type-safe?
- **Forensic Integrity**: Are all state changes, errors, and resolutions logged for OmegaKG?

## Verification Steps

1. **Agent Submission**: Agent provides a summary of changes and verification evidence.
2. **Reviewer Validation**: SigmaDev11 or a Senior Oracle Agent validates the logic.
3. **Gate Approval**: Only after validation can the `uid` status be moved to `done`.

## Consequences

Any task marked `done` without a verified MAR review is considered a Protocol Breach and must be rolled back for forensic analysis.
