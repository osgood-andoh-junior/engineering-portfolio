"""Initial delivery audit; intentionally stops passing after student ML is implemented."""

import ast
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
MARKER = "TODO(" + "STUDENT-ML)"
IGNORED = {
    ".venv",
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".git",
    ".ipynb_checkpoints",
    "storage",
    ".test-tmp",
}
GROUPS = {
    "Experiment 01 — Bag of Words + Naive Bayes": [
        "ml/src/preprocessing/",
        "ml/src/representations/vocabulary.py",
        "ml/src/representations/bow.py",
        "ml/src/training/",
        "ml/src/evaluation/",
        "ml/src/models/naive_bayes.py",
        "ml/notebooks/01_",
    ],
    "Experiment 02 — TF-IDF": [
        "ml/src/representations/tfidf.py",
        "ml/src/representations/similarity.py",
        "ml/notebooks/02_",
    ],
    "Experiment 03 — Embeddings + Neural Network": [
        "ml/src/representations/embeddings.py",
        "ml/src/models/neural_network.py",
        "ml/notebooks/03_",
    ],
    "Experiment 04 — RNN": [
        "ml/src/representations/sequences.py",
        "ml/src/models/rnn.py",
        "ml/notebooks/04_",
    ],
    "Experiment 05 — Attention": [
        "ml/src/models/attention.py",
        "ml/src/models/attention_components.py",
        "ml/notebooks/05_",
    ],
    "Experiment 06 — Transformer": [
        "ml/src/models/transformer.py",
        "ml/src/models/self_attention.py",
        "ml/notebooks/06_",
    ],
    "Shared classifier contract — inherited by Experiments 01, 03, 04, 05, 06": [
        "ml/src/models/base.py",
    ],
    "Infrastructure references — error messages and tests, not ML exercises": [],
}


def source_files(directory):
    for path in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
        if path.name in IGNORED or path.name.endswith(".egg-info"):
            continue
        if path.is_dir():
            yield from source_files(path)
        else:
            yield path


def tree(directory, prefix=""):
    entries = [
        p
        for p in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        if p.name not in IGNORED
        and not p.name.endswith(".egg-info")
        and not p.name.endswith(".tsbuildinfo")
    ]
    result = []
    for index, path in enumerate(entries):
        final = index == len(entries) - 1
        result.append(prefix + ("└── " if final else "├── ") + path.name)
        if path.is_dir():
            result.extend(tree(path, prefix + ("    " if final else "│   ")))
    return result


def main():
    groups = {group: [] for group in GROUPS}
    stub_count = 0
    notebook_count = 0
    for path in source_files(ROOT):
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith("ml/src/") and path.suffix == ".py":
            module = ast.parse(path.read_text(encoding="utf-8"))
            if path.name not in {"interfaces.py", "__init__.py"}:
                for node in ast.walk(module):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        body = node.body
                        if isinstance(body[0], ast.Expr) and isinstance(
                            body[0].value, ast.Constant
                        ):
                            body = body[1:]
                        assert len(body) == 1 and isinstance(body[0], ast.Raise), relative
                        stub_count += 1
                    if isinstance(node, ast.Import):
                        raise AssertionError(f"Unexpected ML import: {relative}")
                    if isinstance(node, ast.ImportFrom):
                        assert node.module in {
                            "pathlib",
                            "typing",
                            "ml.src.interfaces",
                            "base",
                        }, relative
        if relative == "docs/SCAFFOLD_INVENTORY.md":
            continue
        if path.suffix not in {".py", ".tsx", ".ts", ".ipynb", ".md"}:
            continue
        if MARKER not in path.read_text(encoding="utf-8"):
            continue
        group = next(
            (
                name
                for name, prefixes in GROUPS.items()
                if any(relative.startswith(prefix) for prefix in prefixes)
            ),
            list(GROUPS)[-1],
        )
        if path.suffix == ".ipynb":
            notebook = nbformat.read(path, as_version=4)
            nbformat.validate(notebook)
            notebook_count += 1
            section = "Introduction"
            for index, cell in enumerate(notebook.cells):
                if cell.cell_type == "markdown":
                    section = cell.source.strip().splitlines()[-1]
                else:
                    assert cell.source.strip() == "# " + MARKER, relative
                    assert not cell.outputs and cell.execution_count is None, relative
                if MARKER in cell.source:
                    groups[group].append(
                        f"- `{relative}`, cell {index + 1}, {section}: `{cell.source.strip()}`"
                    )
        else:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if MARKER in line:
                    groups[group].append(f"- `{relative}:{number}`: `{line.strip()}`")
    assert notebook_count == 6
    assert stub_count >= 19
    output = [
        "# Scaffold inventory",
        "",
        "Generated by scripts/audit_scaffold.py. Dependency folders, caches, and local SQLite "
        "storage are excluded from the source tree.",
        "",
        f"Validated {notebook_count} empty notebooks and {stub_count} raising ML method/function "
        "bodies. No ML implementation was added.",
        "",
        "## Directory tree",
        "",
        "```text",
        ROOT.name + "/",
        *tree(ROOT),
        "```",
        "",
    ]
    for name, lines in groups.items():
        output += ["## " + name, "", *lines, ""]
    report = "\n".join(output)
    (ROOT / "docs/SCAFFOLD_INVENTORY.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
