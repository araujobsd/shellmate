"""Tests for buddy identity, naming, and aging."""

import pytest

from shellmate.characters import NAMES
from shellmate.identity import (
    Identity,
    age_label,
    name_from_seed,
    new_seed,
    species_from_seed,
)


def test_new_seed_generates_hex_string():
    """new_seed() returns a non-empty hex string."""
    seed = new_seed()
    assert isinstance(seed, str)
    assert len(seed) > 0
    assert all(c in "0123456789abcdef" for c in seed)


def test_new_seed_generates_different_values():
    """Repeated calls to new_seed() generate different values."""
    seeds = [new_seed() for _ in range(10)]
    assert len(set(seeds)) == 10, "All seeds should be unique"


def test_name_from_seed_is_deterministic():
    """Same seed always yields the same name."""
    seed = "test-seed-12345"
    name1 = name_from_seed(seed)
    name2 = name_from_seed(seed)
    assert name1 == name2


def test_name_from_seed_varies_with_seed():
    """Different seeds usually produce different names."""
    seeds = [f"seed-{i}" for i in range(50)]
    names = [name_from_seed(s) for s in seeds]
    unique_names = set(names)
    # With only ~200 possible 2-syllable names and ~200*2 for 3-syllable,
    # we expect most to be different
    assert len(unique_names) > 40, f"Only {len(unique_names)}/50 unique names"


def test_name_from_seed_is_capitalized():
    """Generated names are capitalized."""
    for _ in range(20):
        seed = new_seed()
        name = name_from_seed(seed)
        assert name[0].isupper(), f"Name {name} should start with uppercase"


def test_name_from_seed_is_alphabetic():
    """Generated names contain only alphabetic characters."""
    for _ in range(20):
        seed = new_seed()
        name = name_from_seed(seed)
        assert name.isalpha(), f"Name {name} should be alphabetic only"


def test_name_from_seed_reasonable_length():
    """Generated names have reasonable length (4-10 characters)."""
    for _ in range(20):
        seed = new_seed()
        name = name_from_seed(seed)
        assert 4 <= len(name) <= 10, f"Name {name} has unexpected length {len(name)}"


def test_species_from_seed_is_deterministic():
    """Same seed always yields the same species."""
    seed = "test-seed-species"
    species1 = species_from_seed(seed)
    species2 = species_from_seed(seed)
    assert species1 == species2


def test_species_from_seed_is_valid():
    """Generated species are always valid keys in NAMES."""
    for _ in range(50):
        seed = new_seed()
        species = species_from_seed(seed)
        assert species in NAMES, f"Species {species} not in NAMES"


def test_species_from_seed_varies_with_seed():
    """Different seeds usually produce different species."""
    seeds = [f"seed-{i}" for i in range(50)]
    species_list = [species_from_seed(s) for s in seeds]
    unique_species = set(species_list)
    # With 4 possible species, we expect good variety
    assert len(unique_species) >= 2, f"Only {len(unique_species)} unique species"


def test_name_and_species_vary_independently():
    """Name and species from same seed vary independently."""
    seed = "test-independence"
    name = name_from_seed(seed)
    species = species_from_seed(seed)
    # They should be different values derived from same seed
    assert name != species  # Technically species is a key, name is a name


def test_age_label_newborn():
    """Age < 60 seconds returns 'just laid'.

    Not "just hatched": the first 8 hours are the egg stage, and --whoami prints
    the age beside the stage, so "just hatched (egg)" contradicted itself on the
    very first line of a clean install.
    """
    now = 1000.0
    born_at = 999.0
    assert age_label(born_at, now) == "just laid"


def test_age_label_never_claims_hatched_during_egg_stage():
    """No label produced inside the egg window may say "hatched"."""
    from shellmate.characters import EGG_SECONDS

    now = 1_000_000.0
    for age in (0.0, 1.0, 59.9, 60.0, 3600.0, EGG_SECONDS - 1):
        assert "hatch" not in age_label(now - age, now), f"age={age}"


def test_age_label_minutes():
    """Age 60-3600 seconds returns minutes format."""
    now = 1000.0
    born_at = 880.0  # 120 seconds = 2 minutes
    assert age_label(born_at, now) == "2m old"


def test_age_label_hours():
    """Age 3600+ seconds returns hours format."""
    now = 1000.0
    born_at = 1.0  # 999 seconds ≈ 16 minutes, but let's use more
    born_at = 1000.0 - 7200  # 2 hours
    assert age_label(born_at, now) == "2h old"


def test_age_label_days():
    """Age 24+ hours returns days format."""
    now = 1000.0
    born_at = now - (86400 * 3)  # 3 days
    assert age_label(born_at, now) == "3d old"


def test_age_label_weeks():
    """Age 7+ days returns weeks format."""
    now = 1000.0
    born_at = now - (86400 * 14)  # 2 weeks
    assert age_label(born_at, now) == "2w old"


def test_identity_dataclass():
    """Identity can be created and accessed."""
    ident = Identity(seed="abc123", name="Miso", species="cat", born_at=100.0)
    assert ident.seed == "abc123"
    assert ident.name == "Miso"
    assert ident.species == "cat"
    assert ident.born_at == 100.0


def test_identity_is_frozen():
    """Identity is a frozen dataclass (immutable)."""
    ident = Identity(seed="abc123", name="Miso", species="cat", born_at=100.0)
    with pytest.raises(AttributeError):
        ident.name = "Neko"
