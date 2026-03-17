from dataclasses import dataclass, field


@dataclass
class ImportRowError:
    row_number: int
    message: str


@dataclass
class ImportResult:
    imported_count: int = 0
    failed_rows: list[ImportRowError] = field(default_factory=list)
