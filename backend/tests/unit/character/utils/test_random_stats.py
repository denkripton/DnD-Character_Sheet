from src.modules.character.utils.random_stats import (
    STANDARD_ARRAY,
    generate_random_stats,
    generate_standard_array,
    roll_4d6_drop_lowest,
)


def test_4d6_drop_lowest_in_range():
    for _ in range(200):
        roll = roll_4d6_drop_lowest()
        assert 3 <= roll <= 18


def test_random_generation_returns_six_scores():
    scores = generate_random_stats()
    assert len(scores) == 6


def test_standard_array_matches_phb():
    assert STANDARD_ARRAY == [15, 14, 13, 12, 10, 8]


def test_standard_array_generator():
    assert generate_standard_array() == [15, 14, 13, 12, 10, 8]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("random stats tests passed")