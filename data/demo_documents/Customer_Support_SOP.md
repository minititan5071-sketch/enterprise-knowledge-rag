# Customer Support SOP

Company: HarbourBridge Digital Finance Limited
Team: Customer Operations
Version: 2026.1

## Purpose

This standard operating procedure tells support agents how to respond to customer questions, operational incidents, failed payments, account access issues, and complaints.

## Support Principles

Support agents must be accurate, courteous, and careful with customer data. Agents may verify account status and operational events in approved systems, but must not disclose internal risk scores, security controls, or other customers' information.

## Failed Transfer Handling

When a customer reports a failed transfer, the agent must:

1. Verify the customer's identity using the approved authentication workflow.
2. Confirm the transfer reference, amount, currency, timestamp, recipient bank, and payment rail.
3. Check the payment status in the payments operations dashboard.
4. Determine whether the transfer is pending, rejected, returned, under compliance review, or affected by a known incident.
5. Provide a plain-language status update without exposing internal screening details.
6. Create a support ticket with the payment reference and customer-visible explanation.
7. Escalate to Payments Operations if funds are debited but no final status is visible after 30 minutes.
8. Escalate to Compliance if the transfer is blocked for sanctions, fraud, suspicious activity, or customer due diligence reasons.

Agents must not promise a completion time unless Payments Operations has confirmed it. For suspected duplicate debit, agents must mark the ticket as urgent.

## Complaint Handling

A complaint is any expression of dissatisfaction involving service quality, financial loss, unfair treatment, privacy concern, or regulatory issue. Complaints must be logged on the same business day and acknowledged within two business days. Complaints involving potential customer harm must be escalated to the Complaints Manager.

## Account Access Issues

For login lockouts, agents may trigger the approved recovery flow after identity verification. Agents must never ask for passwords, one-time passcodes, private keys, or full card numbers. Suspected account takeover must be escalated to Security Operations immediately.

## Data Privacy

Support notes must contain only information needed to resolve the case. Do not paste full identity document numbers, bank account numbers, or screenshots containing unnecessary personal data into tickets.

## Knowledge Base Updates

If an answer is missing or outdated, agents should tag the ticket with `kb-gap` and propose an update. The Knowledge Owner reviews `kb-gap` tags weekly.

