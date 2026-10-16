# Security Review Checklist

Use for changes to identity, authorization, input handling, storage, networking,
secrets, dependencies, or deployment. Select relevant checks and trace a plausible
abuse case. Checklist coverage alone does not establish security.

## Trace the boundary

- Identify the actor, entry point, attacker-controlled values, protected resource,
  and privileged operation. Include background jobs and indirect callers.
- Check authentication and server-side authorization for the action, object, and
  tenant. Inspect alternative paths, cache keys, defaults, and failure behavior;
  a client-side control does not establish access enforcement.
- Follow untrusted data to database queries, shell commands, file paths, network
  destinations, deserialization, templates, or rendered output. Check the control
  appropriate to each sink, such as parameterization or context-aware encoding.
- Check malformed, oversized, repeated, concurrent, or replayed requests where
  relevant. Inspect limits and whether partial failure bypasses a protection.

## Inspect exposure and dependencies

- Check credentials and sensitive data in source, logs, errors, client responses,
  caches, and build artifacts. Redact evidence rather than copying live secrets.
- Check transport, storage, access, and retention controls against the data's
  actual sensitivity and project requirements. Internal diagnostics and public
  error messages have different audiences.
- For package, image, or runtime changes, inspect exact resolved versions and
  provenance. Record the advisory or scanner source, lookup date, and affected
  range when citing a vulnerability. Distinguish advisory applicability from
  demonstrated exploitability; a clean or unavailable scan proves neither safety
  nor absence of vulnerabilities.

## Substantiate findings

Check existing guards and supported configurations before reporting a bypass.
Use safe local tests or static traces to establish the path and consequence;
testing a live service needs authorization. Identify missing regression coverage
for a concrete abuse case. If evidence is incomplete, name the uncertainty and
needed check without claiming an exploit.
