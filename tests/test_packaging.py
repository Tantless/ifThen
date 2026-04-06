from pathlib import Path
import tomllib


def test_pyproject_declares_sqlalchemy_runtime_dependency() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.startswith("sqlalchemy") for dependency in dependencies)
