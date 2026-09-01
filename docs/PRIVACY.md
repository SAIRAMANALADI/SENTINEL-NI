# Privacy and Retention

The default live path follows a metadata-not-payload principle.

Collected in memory while live:

- packet metadata required by the event contract;
- bounded active/completed flow summaries;
- bounded 10-second state history;
- bounded source-activity summaries;
- the latest forecast and recommendation output.

Not retained by the live adapter:

- raw packet objects;
- payload bytes or payload contents;
- arbitrary uploaded files;
- secrets or bearer tokens in logs.

The current runtime is process-local. State is lost on process termination,
and the audit JSONL file is an application-level append log rather than a
tamper-evident enterprise store. Deployers must define filesystem permissions,
log rotation, retention, access review, and any legal basis for monitoring
before using live traffic in production.
