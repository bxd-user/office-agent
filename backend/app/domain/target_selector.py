from dataclasses import dataclass


@dataclass
class TargetSelector:
    strategy: str = "auto"
    hint: str = ""
