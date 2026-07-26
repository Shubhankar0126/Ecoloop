"""Safe subprocess execution for EnergyPlus infrastructure components."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from threading import Event

from ecoloop_energyplus.domain.enums import SimulationStatus
from ecoloop_energyplus.infrastructure.execution.command_builder import ExecutionCommand
from ecoloop_energyplus.infrastructure.execution.execution_result import ExecutionResult
from ecoloop_energyplus.infrastructure.execution.timeout import (
    ExecutionTimeout,
    next_wait_seconds,
)


class ProcessManager:
    """Execute subprocess commands without exposing process handles to callers."""

    def __init__(
        self,
        *,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        """Initialize the process manager with optional base environment overrides."""
        self._environment = dict(environment) if environment is not None else None

    def execute(
        self,
        command: ExecutionCommand,
        *,
        timeout: ExecutionTimeout,
        cancellation_event: Event | None = None,
    ) -> ExecutionResult:
        """Execute a command with captured output, timeout, and cancellation handling."""
        started_at = datetime.now(tz=UTC)
        started_monotonic = time.monotonic()

        if cancellation_event is not None and cancellation_event.is_set():
            return self._build_result(
                command=command,
                status=SimulationStatus.CANCELLED,
                exit_code=None,
                stdout="",
                stderr="",
                diagnostics=("Execution was cancelled before the process started.",),
                started_at=started_at,
                started_monotonic=started_monotonic,
            )

        try:
            process = subprocess.Popen(
                command.command_line,
                cwd=str(command.working_directory),
                env=self._build_environment(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as error:
            return self._build_result(
                command=command,
                status=SimulationStatus.FAILED,
                exit_code=None,
                stdout="",
                stderr="",
                diagnostics=(f"Failed to start process: {error}.",),
                started_at=started_at,
                started_monotonic=started_monotonic,
            )

        while True:
            if cancellation_event is not None and cancellation_event.is_set():
                stdout, stderr, exit_code = self._terminate_process(
                    process=process,
                    grace_period_seconds=timeout.grace_period_seconds,
                )
                return self._build_result(
                    command=command,
                    status=SimulationStatus.CANCELLED,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    diagnostics=("Execution was cancelled during process runtime.",),
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                )

            wait_seconds = next_wait_seconds(
                started_monotonic=started_monotonic,
                current_monotonic=time.monotonic(),
                timeout=timeout,
            )
            if wait_seconds <= 0:
                stdout, stderr, exit_code = self._terminate_process(
                    process=process,
                    grace_period_seconds=timeout.grace_period_seconds,
                )
                return self._build_result(
                    command=command,
                    status=SimulationStatus.TIMED_OUT,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    diagnostics=(f"Execution timed out after {timeout.seconds} seconds.",),
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                )

            try:
                stdout, stderr = process.communicate(timeout=wait_seconds)
            except subprocess.TimeoutExpired:
                continue

            status = (
                SimulationStatus.SUCCEEDED
                if process.returncode == 0
                else SimulationStatus.FAILED
            )
            diagnostics: tuple[str, ...] = ()
            if process.returncode != 0:
                diagnostics = (f"Process exited with code {process.returncode}.",)

            return self._build_result(
                command=command,
                status=status,
                exit_code=process.returncode,
                stdout=stdout or "",
                stderr=stderr or "",
                diagnostics=diagnostics,
                started_at=started_at,
                started_monotonic=started_monotonic,
            )

    def _build_environment(self, command: ExecutionCommand) -> dict[str, str]:
        """Build the process environment for one command invocation."""
        environment = dict(self._environment) if self._environment is not None else dict(os.environ)
        for key, value in command.environment_overrides:
            environment[key] = value

        return environment

    def _terminate_process(
        self,
        *,
        process: subprocess.Popen[str],
        grace_period_seconds: float,
    ) -> tuple[str, str, int | None]:
        """Terminate a running process gracefully, then force-kill if needed."""
        if process.poll() is None:
            process.terminate()

        try:
            stdout, stderr = process.communicate(timeout=grace_period_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

        return stdout or "", stderr or "", process.returncode

    def _build_result(
        self,
        *,
        command: ExecutionCommand,
        status: SimulationStatus,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        diagnostics: tuple[str, ...],
        started_at: datetime,
        started_monotonic: float,
    ) -> ExecutionResult:
        """Build a terminal execution result from process state."""
        completed_at = datetime.now(tz=UTC)
        duration_ms = max(0, int((time.monotonic() - started_monotonic) * 1000))

        return ExecutionResult(
            command_line=command.command_line,
            working_directory=command.working_directory,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            diagnostics=diagnostics,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


__all__ = ["ProcessManager"]
