# MFA design for financial roles

MFA is mandatory when an organization owner changes or activates a bank account. Bank-finance users must also complete MFA before the second-person authorization of a payment or financing decision. The API must issue a short-lived, operation-bound challenge and record actor, organization, correlation ID, timestamp, and result in the audit log. Recovery cannot bypass maker-checker rules. Full enrollment, WebAuthn/TOTP, recovery, and step-up token implementation is deferred to weeks 13–14.
