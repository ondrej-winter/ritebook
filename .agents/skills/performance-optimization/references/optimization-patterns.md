# Performance Optimization Patterns

Use the pattern that matches a measured bottleneck. Prefer removing unnecessary
work before adding caches or complex infrastructure. Adapt examples to the project
language, framework, and runtime.

## Repeated dependent reads

Avoid one dependency or storage call per item when the data can be fetched in a
single bounded operation.

```text
Avoid:
1. Fetch records.
2. For each record, fetch related data with another call.

Prefer:
1. Fetch records and required related data in one query, join, batch request, or
   preloaded lookup.
2. Preserve limits so the result size remains bounded.
```

## Unbounded data processing

Do not load or process all records when the user or operation needs only a subset.

```python
# Avoid: unbounded work for every call.
records = repository.list_all_records()

# Prefer: explicit limit and cursor or page boundary.
records = repository.list_records(limit=50, cursor=next_cursor)
```

## Repeated expensive computation

Compute expensive values once per required scope and reuse them only while the
inputs remain valid.

```python
# Avoid: repeated computation in a hot loop.
for item in items:
    score = calculate_expensive_score(config, item)
    publish(score)

# Prefer: precompute shared inputs or move invariant work outside the loop.
prepared_config = prepare_scoring_config(config)
for item in items:
    score = calculate_score(prepared_config, item)
    publish(score)
```

## Missing bounds on caches or queues

Caches and queues should have clear bounds, invalidation, and fallback behavior.

```text
Avoid:
- unlimited cache growth
- stale data with no invalidation path
- queues with no backpressure or dead-letter handling

Prefer:
- maximum size or time-to-live
- explicit invalidation conditions
- metrics for hit rate, evictions, depth, age, and failures
```

## Oversized artifacts or payloads

Send, store, or load only what the operation needs.

```text
Check for:
- unused fields in responses or messages
- large media, documents, archives, or generated artifacts
- unnecessary dependency bundles or plugin loading
- repeated serialization of the same data

Prefer:
- field selection or projections
- pagination, streaming, compression, or chunking
- lazy loading for expensive optional features
```
