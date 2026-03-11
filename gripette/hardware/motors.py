"""Rustypot wrapper for two Feetech STS3215 servos.

Falls back to a mock (simulated positions) when rustypot is unavailable.

Rustypot API:
  controller = Sts3215PyController(serial_port, baudrate, timeout)
  controller.sync_read_present_position(ids)  -> list[float]  (radians)
  controller.sync_write_goal_position(ids, values)
"""

import logging
import threading

logger = logging.getLogger(__name__)

try:
    from rustypot import Sts3215PyController

    _HAS_RUSTYPOT = True
except ImportError:
    _HAS_RUSTYPOT = False


class MotorController:
    """Thread-safe controller for two STS3215 servos on a shared serial bus.

    The lock is critical: the streaming loop reads positions while command RPCs
    write goals — these must not interleave on the serial bus.
    """

    def __init__(
        self,
        port: str = "/dev/ttyS0",
        baudrate: int = 1_000_000,
        id_1: int = 1,
        id_2: int = 2,
        timeout: float = 1.0,
        limits: tuple[tuple[float, float], tuple[float, float]] | None = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.ids = [id_1, id_2]
        self.timeout = timeout
        # limits: ((m1_min, m1_max), (m2_min, m2_max)) in radians
        self.limits = limits
        self._lock = threading.Lock()
        self._controller = None
        self._mock = not _HAS_RUSTYPOT
        # Mock state
        self._mock_positions = [0.0, 0.0]

    def start(self) -> None:
        if self._mock:
            logger.warning("rustypot not available — using mock motors")
            return
        self._controller = Sts3215PyController(
            self.port, self.baudrate, self.timeout,
        )
        # Verify communication by reading positions
        try:
            pos = self._controller.sync_read_present_position(self.ids)
            logger.info(
                "Motors started on %s: ids=%s, positions=%s",
                self.port, self.ids, pos,
            )
        except RuntimeError as e:
            logger.error(
                "Motor communication failed on %s: %s — falling back to mock",
                self.port, e,
            )
            self._controller = None
            self._mock = True

    def read_positions(self) -> tuple[float, float]:
        """Read current positions in radians. Thread-safe."""
        if self._mock:
            return (self._mock_positions[0], self._mock_positions[1])
        with self._lock:
            pos = self._controller.sync_read_present_position(self.ids)
        return (pos[0], pos[1])

    def _check_limits(self, pos1: float, pos2: float) -> None:
        """Raise ValueError if positions are outside configured limits."""
        if self.limits is None:
            return
        (m1_min, m1_max), (m2_min, m2_max) = self.limits
        if not (m1_min <= pos1 <= m1_max):
            raise ValueError(
                f"Motor 1 goal {pos1:.3f} rad outside limits [{m1_min:.3f}, {m1_max:.3f}]"
            )
        if not (m2_min <= pos2 <= m2_max):
            raise ValueError(
                f"Motor 2 goal {pos2:.3f} rad outside limits [{m2_min:.3f}, {m2_max:.3f}]"
            )

    def write_goal_positions(self, pos1: float, pos2: float) -> None:
        """Write goal positions in radians. Thread-safe. Rejects out-of-range commands."""
        self._check_limits(pos1, pos2)
        if self._mock:
            self._mock_positions = [pos1, pos2]
            logger.debug("Mock motors → goals: (%.3f, %.3f)", pos1, pos2)
            return
        with self._lock:
            self._controller.sync_write_goal_position(self.ids, [pos1, pos2])

    def set_torque(self, enable: bool) -> None:
        """Enable or disable motor torque. Thread-safe."""
        if self._mock:
            logger.debug("Mock motors → torque %s", "on" if enable else "off")
            return
        with self._lock:
            self._controller.sync_write_torque_enable(self.ids, [enable, enable])
        logger.info("Motors torque %s", "enabled" if enable else "disabled")

    def stop(self) -> None:
        if self._controller is not None:
            self._controller = None
            logger.info("Motors stopped")
