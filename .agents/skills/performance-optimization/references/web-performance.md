# Web Performance Examples

Use these browser-specific metrics and prompts only when they match the measured
user experience. They are examples, not universal performance goals. Verify current
thresholds and project requirements before applying them.

## Core Web Vitals assessment context

The thresholds below match the official [Web Vitals](https://web.dev/articles/vitals)
guidance verified on 2026-09-22; the source page was last updated on 2024-10-31.
Assess each metric at the 75th percentile of page loads, segmented by mobile and
desktop devices. Reverify the source before presenting these values as current
policy because Web Vitals definitions and thresholds can evolve.

| Metric                         | Good    | Needs improvement   | Poor    |
| ------------------------------ | ------- | ------------------- | ------- |
| LCP, Largest Contentful Paint  | ≤ 2.5s  | > 2.5s and ≤ 4.0s   | > 4.0s  |
| INP, Interaction to Next Paint | ≤ 200ms | > 200ms and ≤ 500ms | > 500ms |
| CLS, Cumulative Layout Shift   | ≤ 0.1   | > 0.1 and ≤ 0.25    | > 0.25  |

## Investigation examples

- first load: network waterfall, server response time, render-blocking resources,
  asset size, font loading, and image dimensions
- interaction delay: main-thread work, expensive rendering, long tasks, event
  handlers, and unnecessary UI updates
- navigation or data loading: request waterfalls, cache behavior, streaming, and
  user-visible loading states
