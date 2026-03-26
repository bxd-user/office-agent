from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VerificationPolicy:
    require_step_verification: bool = True
    stop_on_verification_error: bool = False
