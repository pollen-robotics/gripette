"""Rustypot wrapper for two Feetech STS3215 servos.

Falls back to a mock (simulated positions) when rustypot is unavailable.
"""

import logging
import math
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
    ):
        self.port = port
        self.baudrate = baudrate
        self.ids = [id_1, id_2]
        self._lock = threading.Lock()
        self._controller = None
        self._mock = not _HAS_RUSTYPOT
        # Mock state
        self._mock_positions = [0.0, 0.0]

    def start(self) -> None:
        if self._mock:
            logger.warning("rustypot not available — using mock motors")
            return
        self._controller = Sts3215PyController(self.port, self.baudrate, self.ids)
        # Verify communication by reading positions
        pos = self._controller.get_present_position()
        logger.info(
            "Motors started on %s: id=%s, positions=%s",
            self.port, self.ids, pos,
        )

    def read_positions(self) -> tuple[float, float]:
        """Read current positions in radians. Thread-safe."""
        if self._mock:
            return (self._mock_positions[0], self._mock_positions[1])
        with self._lock:
            pos = self._controller.get_present_position()
        return (pos[0], pos[1])

    def write_goal_positions(self, pos1: float, pos2: float) -> None:
        """Write goal positions in radians. Thread-safe."""
        if self._mock:
            self._mock_positions = [pos1, pos2]
            logger.debug("Mock motors → goals: (%.3f, %.3f)", pos1, pos2)
            return
        with self._lock:
            self._controller.set_goal_position([pos1, pos2])

    def stop(self) -> None:
        if self._controller is not None:
            # No explicit close needed for rustypot controller,
            # but we clear the reference
            self._controller = None
            logger.info("Motors stopped")
