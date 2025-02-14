import typing as t
from pathlib import Path


def get_path_from_root(path: t.Union[str, Path]) -> Path:
    base_path = Path(__file__).resolve().parent
    full_path = base_path / path
    if not full_path.exists():
        full_path.mkdir(parents=True, exist_ok=True)
    return full_path


def get_files_recursive(path: t.Union[str, Path]) -> t.List[Path]:
    path = Path(path)
    if path.is_file():
        return [path]
    return [file for file in path.rglob('*') if file.is_file()]
