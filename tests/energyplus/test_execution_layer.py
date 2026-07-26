from __future__ import annotations

import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from typing import cast

import pytest
from pydantic import ValidationError

from ecoloop_energyplus.config.models import EnergyPlusSettings, SimulationSettings
from ecoloop_energyplus.domain.enums import SimulationStatus
from ecoloop_energyplus.domain.models import SimulationSpec
from ecoloop_energyplus.infrastructure.execution import (
    EnergyPlusCommandBuilder,
    EnergyPlusRunner,
    ExecutionCommand,
    ExecutionResult,
    ExecutionTimeout,
    ProcessManager,
    next_wait_seconds,
    remaining_seconds,
)
from ecoloop_energyplus.infrastructure.locator import (
    CompositeEnergyPlusLocator,
    EnergyPlusCandidateSource,
    EnergyPlusInstallationCandidate,
)
from ecoloop_energyplus.infrastructure.locator.candidate import (
    detect_platform_name,
    expected_executable_name,
)

CURRENT_PLATFORM = detect_platform_name()


def _candidate(executable_path: Path) -> EnergyPlusInstallationCandidate:
    return EnergyPlusInstallationCandidate.create(
        source=EnergyPlusCandidateSource.EXPLICIT_CONFIGURED_EXECUTABLE,
        root_path=executable_path.parent,
        executable_path=executable_path,
        platform=CURRENT_PLATFORM,
        supported=True,
        version="25.1.0",
    )


def test_execution_result_requires_terminal_status() -> None:
    with pytest.raises(ValidationError, match="terminal simulation status"):
        ExecutionResult(
            command_line=("python", "-c", "pass"),
            working_directory=Path("."),
            status=SimulationStatus.RUNNING,
            started_at=datetime.now(tz=UTC),
            completed_at=datetime.now(tz=UTC),
            duration_ms=0,
        )


def test_execution_result_requires_non_empty_command_line() -> None:
    with pytest.raises(ValidationError, match="non-empty command line"):
        ExecutionResult(
            command_line=(),
            working_directory=Path("."),
            status=SimulationStatus.SUCCEEDED,
            started_at=datetime.now(tz=UTC),
            completed_at=datetime.now(tz=UTC),
            duration_ms=0,
        )


def test_execution_result_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        ExecutionResult(
            command_line=("python", "-c", "pass"),
            working_directory=Path("."),
            status=SimulationStatus.SUCCEEDED,
            started_at=datetime.now(),
            completed_at=datetime.now(tz=UTC),
            duration_ms=0,
        )


def test_execution_command_requires_non_empty_command_line() -> None:
    with pytest.raises(ValidationError, match="non-empty command line"):
        ExecutionCommand(
            command_line=(),
            working_directory=Path("."),
        )


def test_timeout_helpers_compute_remaining_budget() -> None:
    timeout = ExecutionTimeout(seconds=10, poll_interval_seconds=0.5)

    remaining = remaining_seconds(
        started_monotonic=100.0,
        current_monotonic=104.25,
        timeout=timeout,
    )
    wait = next_wait_seconds(
        started_monotonic=100.0,
        current_monotonic=104.25,
        timeout=timeout,
    )

    assert remaining == pytest.approx(5.75)
    assert wait == pytest.approx(0.5)


def test_timeout_helpers_return_zero_when_deadline_is_exceeded() -> None:
    timeout = ExecutionTimeout(seconds=1.0, poll_interval_seconds=0.5)

    wait = next_wait_seconds(
        started_monotonic=100.0,
        current_monotonic=101.5,
        timeout=timeout,
    )

    assert wait == 0.0


def test_command_builder_constructs_energyplus_cli_with_settings(tmp_path: Path) -> None:
    builder = EnergyPlusCommandBuilder()
    candidate = _candidate(tmp_path / expected_executable_name(CURRENT_PLATFORM))
    spec = SimulationSpec(
        idf_path=Path("building.idf"),
        epw_path=Path("weather.epw"),
    )
    settings = SimulationSettings(
        run_readvars=True,
        run_expandobjects=True,
        force_annual=True,
        force_design_day=True,
    )

    command = builder.build(
        candidate=candidate,
        spec=spec,
        settings=settings,
        output_directory=tmp_path / "output",
        environment_overrides={"B": "2", "A": "1"},
    )

    assert command.command_line == (
        str(candidate.executable_path),
        "-d",
        str(tmp_path / "output"),
        "-w",
        "weather.epw",
        "--annual",
        "--design-day",
        "--readvars",
        "--expandobjects",
        "building.idf",
    )
    assert command.working_directory == tmp_path / "output"
    assert command.environment_overrides == (("A", "1"), ("B", "2"))


def test_command_builder_omits_optional_flags_by_default(tmp_path: Path) -> None:
    builder = EnergyPlusCommandBuilder()
    candidate = _candidate(tmp_path / expected_executable_name(CURRENT_PLATFORM))
    spec = SimulationSpec(
        idf_path=Path("building.idf"),
        epw_path=Path("weather.epw"),
    )
    working_directory = tmp_path / "working"
    settings = SimulationSettings()

    command = builder.build(
        candidate=candidate,
        spec=spec,
        settings=settings,
        output_directory=tmp_path / "output",
        working_directory=working_directory,
    )

    assert command.command_line == (
        str(candidate.executable_path),
        "-d",
        str(tmp_path / "output"),
        "-w",
        "weather.epw",
        "building.idf",
    )
    assert command.working_directory == working_directory
    assert command.environment_overrides == ()


def test_process_manager_executes_successful_command(tmp_path: Path) -> None:
    process_manager = ProcessManager()
    command = ExecutionCommand(
        command_line=(
            sys.executable,
            "-c",
            (
                "import os,sys; "
                "print('stdout-ok'); "
                "print(os.environ['ECOLOOP_FLAG']); "
                "print('stderr-ok', file=sys.stderr)"
            ),
        ),
        working_directory=tmp_path,
        environment_overrides=(("ECOLOOP_FLAG", "present"),),
    )

    result = process_manager.execute(command, timeout=ExecutionTimeout(seconds=5))

    assert result.status is SimulationStatus.SUCCEEDED
    assert result.exit_code == 0
    assert "stdout-ok" in result.stdout
    assert "present" in result.stdout
    assert "stderr-ok" in result.stderr


def test_process_manager_uses_base_environment_overrides(tmp_path: Path) -> None:
    process_manager = ProcessManager(environment={"ECOLOOP_BASE_FLAG": "base-value"})
    command = ExecutionCommand(
        command_line=(
            sys.executable,
            "-c",
            "import os; print(os.environ['ECOLOOP_BASE_FLAG'])",
        ),
        working_directory=tmp_path,
    )

    result = process_manager.execute(command, timeout=ExecutionTimeout(seconds=5))

    assert result.status is SimulationStatus.SUCCEEDED
    assert "base-value" in result.stdout


def test_process_manager_times_out_long_running_command(tmp_path: Path) -> None:
    process_manager = ProcessManager()
    command = ExecutionCommand(
        command_line=(
            sys.executable,
            "-c",
            "import time; print('start', flush=True); time.sleep(3)",
        ),
        working_directory=tmp_path,
    )

    result = process_manager.execute(
        command,
        timeout=ExecutionTimeout(seconds=0.2, poll_interval_seconds=0.05),
    )

    assert result.status is SimulationStatus.TIMED_OUT
    assert "timed out" in result.diagnostics[0]
    assert "start" in result.stdout


def test_process_manager_cancels_running_command(tmp_path: Path) -> None:
    process_manager = ProcessManager()
    cancellation_event = Event()
    command = ExecutionCommand(
        command_line=(
            sys.executable,
            "-c",
            "import time; print('waiting', flush=True); time.sleep(3)",
        ),
        working_directory=tmp_path,
    )

    def cancel_later() -> None:
        time.sleep(0.2)
        cancellation_event.set()

    worker = Thread(target=cancel_later)
    worker.start()
    try:
        result = process_manager.execute(
            command,
            timeout=ExecutionTimeout(seconds=5, poll_interval_seconds=0.05),
            cancellation_event=cancellation_event,
        )
    finally:
        worker.join()

    assert result.status is SimulationStatus.CANCELLED
    assert "cancelled" in result.diagnostics[0]


def test_process_manager_reports_non_zero_exit_codes(tmp_path: Path) -> None:
    process_manager = ProcessManager()
    command = ExecutionCommand(
        command_line=(sys.executable, "-c", "import sys; sys.exit(3)"),
        working_directory=tmp_path,
    )

    result = process_manager.execute(command, timeout=ExecutionTimeout(seconds=5))

    assert result.status is SimulationStatus.FAILED
    assert result.exit_code == 3
    assert result.diagnostics == ("Process exited with code 3.",)


def test_process_manager_handles_missing_executable(tmp_path: Path) -> None:
    process_manager = ProcessManager()
    command = ExecutionCommand(
        command_line=(str(tmp_path / "missing-executable"), "--version"),
        working_directory=tmp_path,
    )

    result = process_manager.execute(command, timeout=ExecutionTimeout(seconds=5))

    assert result.status is SimulationStatus.FAILED
    assert result.exit_code is None
    assert "Failed to start process" in result.diagnostics[0]


def test_process_manager_respects_pre_start_cancellation(tmp_path: Path) -> None:
    process_manager = ProcessManager()
    cancellation_event = Event()
    cancellation_event.set()
    command = ExecutionCommand(
        command_line=(sys.executable, "-c", "print('never-runs')"),
        working_directory=tmp_path,
    )

    result = process_manager.execute(
        command,
        timeout=ExecutionTimeout(seconds=5),
        cancellation_event=cancellation_event,
    )

    assert result.status is SimulationStatus.CANCELLED
    assert "before the process started" in result.diagnostics[0]


class _GracefulTimeoutProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.killed = False
        self.terminated = False
        self._communicate_calls = 0

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self.terminated = True

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        self._communicate_calls += 1
        if self._communicate_calls == 1:
            raise subprocess.TimeoutExpired(cmd="energyplus", timeout=timeout or 0.0)

        self.returncode = -9
        return ("late-stdout", "late-stderr")

    def kill(self) -> None:
        self.killed = True


class _CompletedProcess:
    def __init__(self) -> None:
        self.returncode = 0

    def poll(self) -> int:
        return 0

    def terminate(self) -> None:
        raise AssertionError("terminate should not be called for completed processes")

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        return ("done", "")


def test_process_manager_force_kills_after_graceful_timeout() -> None:
    process_manager = ProcessManager()
    process = _GracefulTimeoutProcess()

    stdout, stderr, exit_code = process_manager._terminate_process(
        process=cast("subprocess.Popen[str]", process),
        grace_period_seconds=0.1,
    )

    assert process.terminated is True
    assert process.killed is True
    assert stdout == "late-stdout"
    assert stderr == "late-stderr"
    assert exit_code == -9


def test_process_manager_skips_terminate_for_completed_process() -> None:
    process_manager = ProcessManager()
    process = _CompletedProcess()

    stdout, stderr, exit_code = process_manager._terminate_process(
        process=cast("subprocess.Popen[str]", process),
        grace_period_seconds=0.1,
    )

    assert stdout == "done"
    assert stderr == ""
    assert exit_code == 0


class StubCommandBuilder(EnergyPlusCommandBuilder):
    def __init__(self, command: ExecutionCommand) -> None:
        self.command = command
        self.calls: list[tuple[Path, Path | None]] = []

    def build(
        self,
        *,
        candidate: EnergyPlusInstallationCandidate,
        spec: SimulationSpec,
        settings: SimulationSettings,
        output_directory: Path,
        working_directory: Path | None = None,
        environment_overrides: dict[str, str] | None = None,
    ) -> ExecutionCommand:
        self.calls.append((output_directory, working_directory))
        return self.command


class StubProcessManager(ProcessManager):
    def __init__(self, result: ExecutionResult) -> None:
        self.result = result
        self.calls: list[ExecutionTimeout] = []

    def execute(
        self,
        command: ExecutionCommand,
        *,
        timeout: ExecutionTimeout,
        cancellation_event: Event | None = None,
    ) -> ExecutionResult:
        self.calls.append(timeout)
        return self.result


def test_runner_uses_command_builder_and_process_manager(tmp_path: Path) -> None:
    command = ExecutionCommand(
        command_line=(sys.executable, "-c", "print('runner')"),
        working_directory=tmp_path,
    )
    expected_result = ExecutionResult(
        command_line=command.command_line,
        working_directory=command.working_directory,
        status=SimulationStatus.SUCCEEDED,
        exit_code=0,
        stdout="runner",
        stderr="",
        started_at=datetime.now(tz=UTC),
        completed_at=datetime.now(tz=UTC),
        duration_ms=5,
    )
    builder = StubCommandBuilder(command)
    process_manager = StubProcessManager(expected_result)
    runner = EnergyPlusRunner(
        command_builder=builder,
        process_manager=process_manager,
    )
    spec = SimulationSpec(
        idf_path=Path("building.idf"),
        epw_path=Path("weather.epw"),
    )

    result = runner.run(
        candidate=_candidate(tmp_path / expected_executable_name(CURRENT_PLATFORM)),
        spec=spec,
        settings=SimulationSettings(default_timeout_seconds=90),
        output_directory=tmp_path / "output",
    )

    assert result == expected_result
    assert builder.calls == [(tmp_path / "output", None)]
    assert process_manager.calls[0].seconds == 90


def test_process_manager_executes_energyplus_version_if_installed(tmp_path: Path) -> None:
    locator_result = CompositeEnergyPlusLocator().locate(EnergyPlusSettings())
    if locator_result.selected_candidate is None:
        pytest.skip("EnergyPlus is not installed locally.")

    command = ExecutionCommand(
        command_line=(str(locator_result.selected_candidate.executable_path), "--version"),
        working_directory=tmp_path,
    )

    result = ProcessManager().execute(command, timeout=ExecutionTimeout(seconds=10))

    assert result.status is SimulationStatus.SUCCEEDED
    assert result.exit_code == 0
    assert "energyplus" in (result.stdout + result.stderr).casefold()
