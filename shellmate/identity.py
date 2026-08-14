"""Buddy identity persistence. Stable per install."""

import hashlib
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    seed: str  # opaque, stable per install
    name: str  # derived from seed
    species: str  # a key from characters.NAMES, derived from seed
    born_at: float  # unix timestamp of first run


# Syllable tables for name generation
_CONSONANTS = [
    "b",
    "c",
    "d",
    "f",
    "g",
    "h",
    "j",
    "k",
    "l",
    "m",
    "n",
    "p",
    "r",
    "s",
    "t",
    "v",
    "w",
    "z",
]
_VOWELS = ["a", "e", "i", "o", "u"]


def new_seed() -> str:
    """Generate a random opaque seed. Use uuid.uuid4().hex for randomness."""
    return uuid.uuid4().hex


def name_from_seed(seed: str) -> str:
    """Generate a deterministic pronounceable name from seed.

    Same seed always yields the same name. Uses syllable-based generation
    with consonant/vowel alternation to produce pronounceable 2-3 syllable names.
    """
    hash_bytes = hashlib.sha256(seed.encode()).digest()

    # Use different slices of the hash for different syllable positions
    syllables = []
    syllable_count = 2 + (hash_bytes[0] % 2)  # 2 or 3 syllables

    for i in range(syllable_count):
        # Each syllable starts with consonant, followed by vowel
        c_idx = hash_bytes[i * 2] % len(_CONSONANTS)
        v_idx = hash_bytes[i * 2 + 1] % len(_VOWELS)

        consonant = _CONSONANTS[c_idx]
        vowel = _VOWELS[v_idx]

        syllables.append(consonant + vowel)

    name = "".join(syllables)
    return name.capitalize()


def rare_species_for_seed(seed: str) -> str | None:
    """Which rare species this seed rolled, or None. Pure and deterministic.

    Each rare species gets its own two bytes and its own independent roll, so
    adding one does not dilute the odds of the others. Those bytes are untouched
    by the name and common-species rolls, so a rare buddy is no likelier to have
    any particular name. If two rolls somehow hit at once the earlier entry wins,
    which at 1-in-100 each happens about once in ten thousand seeds.
    """
    from shellmate.characters import RARE_NAMES, RARE_ODDS

    hash_bytes = hashlib.sha256(seed.encode()).digest()
    for index, name in enumerate(RARE_NAMES):
        offset = 12 + index * 2
        if int.from_bytes(hash_bytes[offset : offset + 2], "big") % RARE_ODDS == 0:
            return name
    return None


def is_rare_seed(seed: str) -> bool:
    """Whether this seed rolled any rare species. Pure and deterministic."""
    return rare_species_for_seed(seed) is not None


def species_from_seed(seed: str) -> str:
    """Pick a species deterministically from seed.

    Uses a different slice of the hash than name_from_seed, so name and
    species vary independently. Must return a key from characters.NAMES.

    The rare species is drawn from its own roll and excluded from the common one.
    Deriving it from the seed rather than storing it means it costs nothing to
    persist and survives any state loss that leaves identity.json intact.
    """
    from shellmate.characters import COMMON_NAMES

    rare = rare_species_for_seed(seed)
    if rare is not None:
        return rare

    hash_bytes = hashlib.sha256(seed.encode()).digest()
    species_idx = hash_bytes[8] % len(COMMON_NAMES)  # Use byte 8, different from name
    return COMMON_NAMES[species_idx]


def age_label(born_at: float, now: float) -> str:
    """Format buddy's age in human-readable form.

    Returns strings like "just laid", "2h old", "3d old", "5w old".
    Pure function.

    Note the under-a-minute case says "just laid", not "just hatched": for the
    first 8 hours the buddy is still an egg, so reporting it as hatched
    contradicts the "(egg)" stage shown beside it — and that pairing is the
    very first thing a new user reads.
    """
    elapsed = now - born_at

    if elapsed < 60:
        return "just laid"

    minutes = int(elapsed // 60)
    if minutes < 60:
        return f"{minutes}m old"

    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h old"

    days = int(hours // 24)
    if days < 7:
        return f"{days}d old"

    weeks = int(days // 7)
    return f"{weeks}w old"
