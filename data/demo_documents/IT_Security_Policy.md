# IT Security Policy

Company: HarbourBridge Digital Finance Limited
Owner: Security Engineering
Effective date: 2026-01-01

## Objective

This policy defines baseline security controls for systems, data, devices, access, software delivery, and internal AI tools.

## Access Control

All production systems require single sign-on, multi-factor authentication, and role-based access. Privileged access must be approved by the system owner and reviewed quarterly. Shared accounts are prohibited unless an exception is approved and monitored.

## Device Security

Company devices must use disk encryption, endpoint detection, automatic screen lock, managed patching, and approved configuration profiles. Lost or stolen devices must be reported to Security Operations immediately.

## Data Classification

Data is classified as public, internal, confidential, or restricted. Customer identity data, transaction data, authentication secrets, security logs, and regulatory investigation records are restricted data. Restricted data must not be copied to unmanaged devices or unapproved SaaS tools.

## GenAI Tool Rules

Employees may use approved internal GenAI tools for summarization, drafting, code assistance, and knowledge search. Employees must not enter restricted data, customer personal data, production secrets, unreleased financial results, or confidential legal advice into public GenAI tools.

Approved GenAI use must follow these rules:

- Use the enterprise knowledge platform for internal policy questions.
- Verify generated answers against cited sources before taking action.
- Do not treat generated output as legal, compliance, or investment advice.
- Report unsafe, incorrect, or uncited answers using the feedback workflow.
- Do not use GenAI to make automated customer eligibility decisions without approved model governance.

## Software Delivery

Production changes require peer review, automated tests, and deployment approval. Secrets must be stored in the approved secrets manager, not in source code, tickets, chat, or local environment files.

## Logging and Monitoring

Security-relevant systems must log authentication, authorization, administrative actions, data export events, and security alerts. Logs must be protected from tampering and retained according to the retention schedule.

## Security Exceptions

Exceptions must include business justification, risk owner, compensating controls, and expiry date. Exceptions longer than 90 days require CISO approval.

