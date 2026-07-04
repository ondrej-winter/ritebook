---
name: write-python-docstrings
description: Write concise Google-style Python docstrings and inline comments that explain contracts, invariants, and non-obvious behavior.
---

# Write Python Docstrings

Use this skill when Python code needs documentation that helps callers or future
maintainers understand contracts, side effects, invariants, or non-obvious
behavior.

## When to use this skill

Use this skill when you need to document:

- a public module with non-obvious responsibilities
- a public class with lifecycle or invariant expectations
- a public function or method with tricky inputs, side effects, or error rules
- inline logic that is hard to understand from names alone

Do not add documentation just to restate obvious names or type hints.

## Steps

### 1. Decide what actually needs documentation

Prefer documentation for:

- public APIs
- non-obvious behavior
- side effects
- concurrency or cancellation rules
- invariants and usage constraints

Skip trivial private helpers when names and types already tell the story.

### 2. Choose the right form

- module docstring for module purpose and constraints
- class docstring for responsibility and invariants
- function or method docstring for contract and caller-facing behavior
- inline comment only for non-obvious local logic

### 3. Write a short summary first

Start with one clear sentence.

Examples:

```python
"""Build the outbound payload for the payment gateway."""
```

```python
"""Coordinate order placement through the application boundary."""
```

### 4. Add only the sections that help callers

Use Google-style sections such as `Args`, `Returns`, `Raises`, `Yields`, or
`Examples` only when they add real value.

Good candidates:

- unusual argument semantics
- caller-visible exceptions
- partial-failure or retry behavior
- important side effects
- units, encodings, timezones, or ownership expectations

### 5. Keep inline comments rare and useful

Inline comments should explain why a choice exists, not narrate obvious code.

Good:

```python
# Keep the legacy field name for backward compatibility with existing clients.
```

Avoid:

```python
# Increment the counter by one.
counter += 1
```

### 6. Re-check for noise

Before finishing, remove documentation that:

- repeats type hints without adding meaning
- reads like a changelog or ADR
- uses marketing language
- documents implementation details callers do not need

## Output checklist

- documentation exists only where it adds value
- summaries are short and concrete
- Google-style sections are used only when helpful
- comments explain why rather than what
- documentation stays aligned with the real behavior
