from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    max_retries_per_step: int = 2

    def can_retry(self, retries_done: int) -> bool:
        return retries_done < self.max_retries_per_step
