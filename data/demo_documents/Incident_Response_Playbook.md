# Incident Response Playbook

Company: HarbourBridge Digital Finance Limited
Owner: Security Operations
Version: 2026.1

## Purpose

This playbook defines the response process for security incidents, privacy incidents, service outages, and suspected data leakage.

## Severity Levels

Severity 1 incidents involve active data leakage, confirmed compromise of production systems, customer funds at risk, widespread outage, or regulatory notification risk. Severity 2 incidents involve limited compromise, high-risk vulnerability exposure, or material customer impact. Severity 3 incidents involve contained issues with no evidence of customer harm.

## Suspected Data Leakage Process

For suspected data leakage, responders must:

1. Open an incident record and assign an incident commander.
2. Preserve evidence, including relevant logs, alerts, file paths, timestamps, and access records.
3. Contain exposure by disabling affected accounts, revoking tokens, removing public links, or isolating systems.
4. Identify data types involved and whether customer personal data, restricted data, or regulated records are affected.
5. Notify the Data Protection Lead and Legal if personal data may be involved.
6. Notify Compliance if regulatory reporting may be required.
7. Prepare customer and regulator communications only through approved Legal and Compliance channels.
8. Complete root cause analysis and remediation tracking after containment.

## Communications

Incident updates must be posted in the incident channel every 30 minutes for Severity 1 incidents and every 2 hours for Severity 2 incidents. External communications require Legal and Compliance approval.

## Evidence Handling

Do not paste restricted data into chat channels. Store evidence in the approved incident repository with access limited to the response team.

## Post-Incident Review

A post-incident review is required within five business days for Severity 1 and Severity 2 incidents. The review must document timeline, root cause, customer impact, control gaps, corrective actions, and owners.

## Closure Criteria

An incident can close only after containment is confirmed, customer impact is assessed, required notifications are complete, and remediation actions are tracked.

