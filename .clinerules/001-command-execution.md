# Cline command execution

These rules govern Cline command execution. Root `AGENTS.md` owns repository-wide
safety policy, including Git authorization and remote-execution restrictions.

- Treat `run_commands` as non-interactive. Never use it to launch an editor, pager,
  watcher, prompt, or other process that waits for terminal input, even when the
  user requests an interactive workflow. Explain the limitation or use a supported
  host interaction mechanism.
- Prefer direct, readable one-line commands. Do not stream multiline scripts into
  a shell or interpreter, including through heredocs or piped standard input.
  Ordinary non-interactive pipelines between commands remain allowed.
- In Act mode, create necessary non-trivial helper scripts with a file-writing
  tool under the ignored `.tmp/cline/` directory. Use descriptive filenames and
  execute each script explicitly by absolute path.
- In Plan mode, do not create helper files. Use a straightforward read-only
  command when possible; otherwise describe and defer the command until Act mode.
- Disable Git paging, for example with `git --no-pager`, and use non-interactive
  Git options when available.
