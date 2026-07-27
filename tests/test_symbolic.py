"""Tests for the generated dataset constants module."""

from utils.symbolic import symbolic


def test_generated_module_has_stable_docstring_spacing(tmp_path):
    """Keep formatting from changing the generated module on every run."""
    destination = tmp_path / "datasets.py"
    generator = symbolic()
    generator.store_dataset(["acs/acs5"], ["https://api.census.gov/data.html"])

    generator.write_file(destination)

    generated = destination.read_text()
    assert '"""\n\nACS5 = "acs/acs5"' in generated
    assert '"""\n\n\nACS5 = "acs/acs5"' not in generated
