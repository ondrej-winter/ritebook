"""Source CLI runner with a test-only pause before sync lockfile persistence."""

from __future__ import annotations

import sys
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING
from unittest.mock import patch

import ritebook.cli as cli_module
from ritebook.features.skill_installation.adapters.outbound import FilesystemSyncWriterAdapter

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import GeneratedStateFile


class PausingSyncWriter(FilesystemSyncWriterAdapter):
    def __init__(self, ready: Path) -> None:
        self.ready = ready

    def write_lockfile(self, candidate: GeneratedStateFile) -> None:
        del candidate
        self.ready.write_text("replacement complete; lockfile not written\n")
        Event().wait(30)
        msg = "interruption test did not terminate the child before lockfile persistence"
        raise TimeoutError(msg)


def main(arguments: list[str]) -> int:
    """Run the normal composition, optionally pausing its real sync writer."""
    if arguments[0] == "pause-before-lockfile":
        ready = Path(arguments[1])
        with patch.object(cli_module, "FilesystemSyncWriterAdapter", return_value=PausingSyncWriter(ready)):
            return cli_module.main(arguments[2:])
    return cli_module.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
