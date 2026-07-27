# Copyright (c) 2022 Darren Erik Vengroff

"""Tests for the bundled diversity, integration, and segregation metrics."""

import pandas as pd
import pytest

from censusdis import divintseg


@pytest.fixture
def communities() -> pd.DataFrame:
    """Return nested communities used by the metric tests."""
    return pd.DataFrame(
        [
            ["X", "X1", 10, 10, 10],
            ["X", "X2", 20, 20, 20],
            ["Y", "Y1", 100, 0, 0],
            ["Y", "Y2", 0, 100, 0],
        ],
        columns=["region", "subregion", "A", "B", "C"],
    )


def test_diversity_accepts_iterables_and_dataframes() -> None:
    """Diversity preserves both forms of the public API."""
    assert divintseg.diversity([10, 10, 10]) == pytest.approx(2.0 / 3.0)

    actual = divintseg.diversity(
        pd.DataFrame([[10, 10, 10], [10, 0, 0]], columns=["A", "B", "C"])
    )

    pd.testing.assert_series_equal(
        actual,
        pd.Series([2.0 / 3.0, 0.0], name="diversity"),
    )


def test_diversity_integration_and_segregation(
    communities: pd.DataFrame,
) -> None:
    """The combined API computes all three related metrics."""
    actual = divintseg.di(
        communities,
        by="region",
        over="subregion",
        add_segregation=True,
    )

    expected = pd.DataFrame(
        [
            [2.0 / 3.0, 2.0 / 3.0, 1.0 / 3.0],
            [0.5, 0.0, 1.0],
        ],
        columns=["diversity", "integration", "segregation"],
        index=pd.Index(["X", "Y"], name="region"),
    )
    pd.testing.assert_frame_equal(actual, expected)

    pd.testing.assert_frame_equal(
        divintseg.integration(communities, by="region", over="subregion"),
        expected[["integration"]],
    )
    pd.testing.assert_frame_equal(
        divintseg.segregation(communities, by="region", over="subregion"),
        expected[["segregation"]],
    )


def test_drop_non_numeric_supports_pandas_3_string_dtype(
    communities: pd.DataFrame,
) -> None:
    """Extra string columns are excluded from metric calculations."""
    communities["label"] = ["one", "two", "three", "four"]

    actual = divintseg.di(
        communities,
        by="region",
        over="subregion",
        drop_non_numeric=True,
    )

    assert list(actual.columns) == ["diversity", "integration"]
    assert actual.loc["X", "diversity"] == pytest.approx(2.0 / 3.0)


def test_similarity_and_dissimilarity_are_complements() -> None:
    """Similarity is one minus dissimilarity for each community."""
    reference = {"A": 10, "B": 20, "C": 30}
    communities = pd.DataFrame(
        [[10, 20, 30], [60, 0, 0]],
        columns=["A", "B", "C"],
    )

    dissimilarity = divintseg.dissimilarity(communities, reference)
    similarity = divintseg.similarity(communities, reference)

    pd.testing.assert_series_equal(similarity, 1.0 - dissimilarity)
    assert dissimilarity.iloc[0] == 0.0


def test_isolation_bells_and_exposure_do_not_mutate_input() -> None:
    """The remaining metrics retain their public behavior."""
    communities = pd.DataFrame(
        [
            ["Region 1", "Subregion A", 100, 0, 0],
            ["Region 1", "Subregion B", 50, 50, 50],
            ["Region 2", "Subregion C", 0, 110, 100],
            ["Region 2", "Subregion D", 0, 50, 0],
            ["Region 2", "Subregion E", 10, 90, 0],
        ],
        columns=["REGION", "SUBREGION", "A", "B", "C"],
    )
    original = communities.copy()

    isolation = divintseg.isolation(communities, "A", by="REGION", over="SUBREGION")
    bells = divintseg.bells(communities, "A", by="REGION", over="SUBREGION")
    exposure = divintseg.exposure(communities, "A", by="REGION", over="SUBREGION")

    assert isolation["A"].tolist() == pytest.approx([7.0 / 9.0, 0.1])
    assert bells["A"].tolist() == pytest.approx([4.0 / 9.0, 13.0 / 175.0])
    assert exposure["B"].tolist() == pytest.approx([1.0 / 3.0, 0.036])
    assert exposure["C"].tolist() == pytest.approx([1.0 / 3.0, 0.0])
    pd.testing.assert_frame_equal(communities, original)
