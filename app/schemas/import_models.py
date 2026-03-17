from dataclasses import dataclass, field


@dataclass
class ImportRowError:
    row_number: int
    message: str


@dataclass
class ImportResult:
    assets_created: int = 0
    assets_reused: int = 0
    lots_created: int = 0
    duplicates_skipped: int = 0
    failed_rows: list[ImportRowError] = field(default_factory=list)
