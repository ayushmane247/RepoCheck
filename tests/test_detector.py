from app.detector import detect_support


def test_detects_test_prefix():
    result = detect_support(["tests/test_api.py", "app/main.py"])
    assert result["supported"] is True
    assert result["test_files"] == ["tests/test_api.py"]


def test_detects_test_suffix():
    assert detect_support(["app/calculator_test.py"])["supported"] is True


def test_ignores_non_python_and_dependency_directories():
    result = detect_support([
        "node_modules/test_example.py", ".venv/test_hidden.py",
        "tests/test_ui.js", "app/main.py",
    ])
    assert result["supported"] is False
    assert result["test_file_count"] == 0


def test_ignores_traversal_paths():
    assert detect_support(["../test_escape.py", "/tmp/test_absolute.py"])["supported"] is False


def test_deduplicates_and_sorts_results():
    result = detect_support(["tests/test_z.py", "tests/test_a.py", "tests/test_z.py"])
    assert result["test_files"] == ["tests/test_a.py", "tests/test_z.py"]


def test_identifies_an_unsupported_source_language():
    result = detect_support(["src/index.js", "README.md"])
    assert result["supported"] is False
    assert result["language"] == "javascript"
    assert result["unsupported_language"] is True
