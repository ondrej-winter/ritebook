# Boundary-Specific Design Checklist

Use only the sections relevant to the current boundary. These prompts supplement
the main workflow; they do not replace project conventions, protocol standards,
or consumer evidence.

## HTTP and RPC

- Define resource or operation identity, method semantics, and canonical paths or
  procedure names.
- Specify request and response media types, encoding, field casing, timestamps,
  time zones, units, numeric precision, and identifier formats.
- Map success and failure conditions consistently to transport status and a
  structured error contract.
- Define authentication, authorization scope, tenant context, and what information
  may be revealed when access is denied.
- For retriable writes, define idempotency keys, their scope, retention, replay
  response, and conflict behavior.
- Define deadlines, cancellation propagation, retry guidance, rate limits, and
  whether a timeout can occur after a commit.
- For reads, define caching, freshness, conditional requests, and consistency when
  these are part of the contract.
- State whether unknown request fields are rejected or ignored and whether clients
  must ignore unknown response fields or enum values.
- Keep correlation and trace identifiers distinct from domain identifiers.

## Messages and events

- State whether the message is a fact, command, request, reply, notification, or
  snapshot; name it for what happened or what is requested.
- Define producer ownership, intended consumers, topic or channel semantics, and
  routing or partition keys.
- Define the envelope: message identifier, event or command type, schema revision,
  producer, occurred-at versus published-at time, correlation, and causation.
- Document delivery guarantees, acknowledgement point, retry and backoff behavior,
  duplicate handling, ordering scope, and replay behavior.
- Provide a stable deduplication identity when consumers must make processing
  idempotent.
- Define poison-message handling, dead-letter behavior, retention, redrive, and
  operator ownership when supported.
- Specify how old consumers handle new fields or event types and how new consumers
  handle historical messages.
- Do not claim exactly-once processing unless the end-to-end effect, including
  external side effects, is proven under retries and failures.

## Libraries, modules, and plugins

- Define public versus private symbols and prevent accidental exposure through
  transitive types or re-exports.
- Specify ownership, mutability, lifecycle, cleanup, and whether values remain
  valid after a call returns.
- State synchronous or asynchronous behavior, concurrency or thread-safety
  guarantees, cancellation, and callback or re-entrancy rules.
- Use stable domain types and errors; avoid exposing dependency-specific objects
  unless adopting that dependency is an intentional consumer requirement.
- Check source, binary, serialization, and runtime compatibility as applicable to
  the language and packaging system.
- For extension points, define discovery, registration, capability negotiation,
  ordering, isolation, failure containment, and compatibility expectations.
- Define behavior for duplicate registration, missing capabilities, unsupported
  versions, and plugin startup or shutdown failure.

## Command-line interfaces

- Define command and subcommand grammar, positional arguments, flags, aliases,
  defaults, repeatability, and mutually exclusive options.
- State precedence among command arguments, environment variables, configuration,
  and built-in defaults.
- Reserve stdout for promised result data and stderr for diagnostics when machine
  consumption matters.
- Define exit codes by failure category; do not require scripts to parse prose.
- Specify stable machine-readable formats separately from human-readable output,
  including schema or version behavior where needed.
- Define TTY versus non-TTY behavior, prompts, confirmation, quiet or verbose
  modes, color, paging, and non-interactive failure behavior.
- Define signal, cancellation, timeout, partial-output, and partial-side-effect
  behavior.
- Treat help text, flag names, defaults, output columns, and commonly parsed text
  as compatibility-sensitive observable behavior.

## UI components

- Define required and optional inputs, defaults, controlled versus uncontrolled
  state, and ownership of mutable values.
- Specify emitted events, their timing, payload, cancellation, and whether an event
  reports intent, progress, or committed state.
- Cover loading, empty, error, disabled, stale, and partial-data states rather than
  only the success state.
- Define keyboard behavior, focus ownership, labels, roles, announcements, and
  other accessibility semantics that consumers must preserve.
- State composition rules for children, slots, content, styling, and extension
  points without leaking private DOM or framework structure unnecessarily.
- Define asynchronous race behavior, duplicate actions, optimistic updates, and
  what happens when the component is removed during work.

## Schemas and configuration

- Define required, optional, nullable, unknown, deprecated, computed, and secret
  fields separately.
- Specify validation timing, failure reporting, defaults, units, formats, ranges,
  cross-field constraints, and whether unknown keys are rejected.
- State precedence and merge behavior across files, profiles, environment,
  command-line overrides, remote settings, and built-in defaults.
- Define whether changes are static, reloadable, eventually applied, or require a
  restart, and how invalid updates affect the last known good configuration.
- Avoid storing secret values when a secret reference or platform mechanism is the
  intended contract.
- Define schema evolution, downgrade behavior, migration, and removal of deprecated
  keys or fields.

## Common compatibility traps

- Adding a response field can break strict decoders or snapshot assertions.
- Adding an enum, union variant, event type, or status can break exhaustive consumers.
- Relaxing provider validation can create outputs that older consumers cannot handle.
- Tightening validation rejects inputs that previously succeeded.
- Changing a default, unit, sort order, precision, timestamp, or identifier format
  changes semantics even when the shape is unchanged.
- Renaming human-readable output can break scripts when no stable format existed.
- Changing retry, timeout, authorization, or side-effect behavior can be more
  disruptive than a schema change.
- Reusing a field or error code with a new meaning is breaking even if its type and
  spelling remain unchanged.