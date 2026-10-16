# Performance Review Checklist

Use for changes to request paths, rendering, storage, background work, caches,
startup, data volume, or artifact size. Separate suspected cost from a measured
regression. Do not require a benchmark for every change or optimize without a
relevant workload or requirement.

## Establish the workload

- Identify expected input size, request rate, concurrency, and growth. Use the
  project's latency, throughput, memory, or cost requirements where available.
- Trace work added to the critical path, including network calls, database
  queries, file reads, repeated computation, and blocking operations.
- Inspect complexity, query plans or indexes where available, batching,
  pagination, and data transfer at representative scale. Small fixtures can hide
  repeated queries or unbounded work.

## Check resource behavior

- Check bounds on allocations, result sets, queues, fan-out, and retries.
  Consider backpressure, timeouts, cancellation, and cleanup under failure.
- Check cache keys, invalidation, size bounds, miss behavior, and simultaneous
  misses. Include any correctness trade-off in the review.
- For UI or startup changes, inspect unnecessary rendering, oversized assets,
  eager work, and delays visible to the user.

## Assess evidence

- For measured claims, compare baseline and candidate under comparable conditions:
  revisions, environment, input size, concurrency, warm or cold state, and metric
  units. Note sample size or variability where it affects the conclusion.
- State which metric improved and which may have worsened. A faster average does
  not establish better tail latency, lower memory use, or lower cost.
- Static reasoning can establish an unbounded operation or added work. Do not
  invent timings or claim user impact without evidence about the relevant load.
- If measurement is unavailable, report the specific risk and the smallest check
  that would resolve it. Block only for an evidenced defect or unmet requirement;
  defer when missing evidence prevents assessing a material risk.
