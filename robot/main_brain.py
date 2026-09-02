"""Compatibility entry point. New deployments use the ``robot-agent`` command."""

from robot_app.application.voice import (
    EXIT_WORDS,
    WAKE_WORDS,
    is_exit_command,
    is_wake_word,
    listen_command_with_retry,
    normalize,
    run_voice_loop,
)
from robot_app.bootstrap import main


if __name__ == "__main__":
    main()
