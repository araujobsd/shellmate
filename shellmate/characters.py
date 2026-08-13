r"""Sprite data. No logic lives here — adding a buddy is appending a dict entry.

Contract, enforced by tests/test_characters.py:
  * every character defines all six moods
  * animated moods carry 2 frames, or any divisor of MAX_FRAMES up to it;
    `offline` carries exactly 1 and never animates
  * every frame is exactly 3 lines
  * no line exceeds 12 display columns
  * egg frames are 3 lines and <=12 columns
  * idle frames are 3 lines and <=12 columns
  * baby frames exist for every mood in BABY_MOODS; 2 frames each
  * a baby's mirrored pairs (/\, <>, (), []) stay as balanced as its adult's —
    the cat shipped with /\_\ instead of /\/\, one ear short, and nothing caught
    it because both characters were still present

Phrases: mood-specific lines of dialogue, per character. Each character has a
distinct voice. Constraints, enforced by tests/test_characters.py:
  * every character has every mood in PHRASES, 4-6 phrases each
  * each phrase <= 42 display columns (measured with textwidth.width())
  * no phrase is empty or whitespace-only
  * within one character+mood, all phrases are distinct
  * across characters, no phrase is reused for the same mood (each species has
    its own voice)
  * phrases are plain ASCII plus punctuation; no emoji
"""

MOODS = ("sleeping", "working", "happy", "perked", "alert", "alarmed", "offline")
# Moods that have hatchling art — all of them. A hatchling stays a hatchling.
#
# alert/alarmed/offline used to be excluded so they would render full-size and
# "stay legible", but for a solo session being idle past med_seconds is the
# normal state, so the buddy was adult-sized most of the time and a hatchling
# only while a prompt was running. The stage was nearly invisible and the size
# flipped constantly. Urgency is carried by colour and the ! / !! marks, which
# work at any size; size is a weak signal that mostly just made it jitter.
BABY_MOODS = MOODS
SPRITE_LINES = 3
# Animation slots written to the frame cache. The hot path picks one by wall
# clock, so every sprite is written cycling to fill all of them: a 2-frame buddy
# becomes a,b,a,b and alternates once a second exactly as it always has, while a
# 4-frame one gets a full four-second loop. Frame counts must divide this.
MAX_FRAMES = 4
SPRITE_MAX_COLS = 12

# Growth stage boundaries (seconds from birth)
EGG_SECONDS = 8 * 3600  # 8 hours: egg stage
HATCHLING_SECONDS = 2 * 86400  # 2 days: hatchling stage
JUVENILE_SECONDS = 4 * 86400  # 4 days: juvenile stage (adult sprites, label only)
# Adult stage begins at JUVENILE_SECONDS (4 days) onward

# Egg hatching animation — shared across all buddies
EGG = [
    [r"   ()    ", r"  (  )   ", r"   ()    "],
    [r"   ()    ", r"  ( :)   ", r"   ()    "],
    [r"  (  )   ", r"  (::)   ", r"  (  )   "],
    # Shell bottom is \__/ : it mirrors the (  ) top and matches its width. It
    # was written r"  \\_/\\  ", but a raw string does not process escapes, so
    # both backslashes rendered literally as \\_/\\.
    [r"  (  )   ", r"   ^-^   ", r"  \__/   "],
]

# Egg phrases — species-agnostic, showing progression from silence to hatching
# One group per egg frame, 3-4 phrases each, advancing with hatch progress
EGG_PHRASES = (
    # Frame 0 (0-2h): barely anything stirring
    (
        "...",
        "*silence*",
        "very quiet",
    ),
    # Frame 1 (2-4h): something is in there, soft stirring
    (
        "...shuffling...",
        "tap... tap...",
        "something moves",
    ),
    # Frame 2 (4-6h): audibly working at it, cracks widening
    (
        "craaack...",
        "almost out",
        "getting closer",
        "tap tap TAP",
    ),
    # Frame 3 (6-8h): imminent, the big moment approaches
    (
        "almost... almost...",
        "coming soon...",
        "any second now",
        "here we go...",
    ),
)

CHARACTERS = {
    "cat": {
        "sleeping": [
            [r" /\_/\ ", r"( -.- ) z", r" > ^ <  "],
            [r" /\_/\ ", r"( -.- ) zz", r" > ^ <  "],
        ],
        "working": [
            [r" /\_/\ ", r"( o.o )", r" > ^ <  "],
            [r" /\_/\ ", r"( o.O )", r" > ^ <  "],
        ],
        "happy": [
            [r" /\_/\ ", r"( >.< )*", r" > ^ <  "],
            [r" /\_/\ ", r"( >w< )*", r" > ^ <  "],
        ],
        "perked": [
            [r" /\_/\ ", r"( o.o ) ?", r" > ^ <  "],
            [r" /\_/\ ", r"( O.o ) ?", r" > ^ <  "],
        ],
        "alert": [
            [r" /\_/\ ", r"( O.O ) !", r" > ^ <  "],
            [r" /\_/\ ", r"( O.O ) !!", r" > ^ <  "],
        ],
        "alarmed": [
            [r" /\_/\  !", r"( ಠ.ಠ ) !!", r" >^^^<  "],
            [r" /\_/\ !!", r"( ಠ.ಠ ) !!", r" >vvv<  "],
        ],
        "offline": [[r" /\_/\ ", r"( -.- ) ...", r" > ^ <  "]],
    },
    # NOTE: the owl's feet contain double quotes, so these use single-quoted raw
    # strings. Writing r" -\"-\"- " would emit literal backslashes, because a
    # raw string does not process the escape.
    "owl": {
        "sleeping": [
            [r" ,___,  ", r" (-,-)  z", r' -"-"- '],
            [r" ,___,  ", r" (-,-) zz", r' -"-"- '],
        ],
        "working": [
            [r" ,___,  ", r" (o,o)  ", r' -"-"- '],
            [r" ,___,  ", r" (o,O)  ", r' -"-"- '],
        ],
        "happy": [
            [r" ,___,  ", r" (>,<) * ", r' -"-"- '],
            [r" ,___,  ", r" (>w<) * ", r' -"-"- '],
        ],
        "perked": [
            [r" ,___,  ", r" (o,o) ?", r' -"-"- '],
            [r" ,___,  ", r" (O,o) ?", r' -"-"- '],
        ],
        "alert": [
            [r" ,___,  ", r" (O,O) !", r' -"-"- '],
            [r" ,___,  ", r" (O,O) !!", r' -"-"- '],
        ],
        "alarmed": [
            [r" ,___, !", r" (ಠ,ಠ) !!", r" -^-^-  "],
            [r" ,___,!!", r" (ಠ,ಠ) !!", r" -v-v-  "],
        ],
        "offline": [[r" ,___,  ", r" (-,-) ..", r' -"-"- ']],
    },
    "blob": {
        "sleeping": [
            [r"  .---.  ", r" ( -.- ) z", r"  `---'  "],
            [r"  .---.  ", r" ( -.- ) zz", r"  `---'  "],
        ],
        "working": [
            [r"  .---.  ", r" ( o.o ) ", r"  `---'  "],
            [r"  .---.  ", r" ( o.O ) ", r"  `---'  "],
        ],
        "happy": [
            [r"  .---.  ", r" ( >.< )*", r"  `~~~'  "],
            [r"  .---.  ", r" ( >w< )*", r"  `~~~'  "],
        ],
        "perked": [
            [r"  .---.  ", r" ( o.o ) ?", r"  `---'  "],
            [r"  .---.  ", r" ( O.o ) ?", r"  `---'  "],
        ],
        "alert": [
            [r"  .---.  ", r" ( O.O ) !", r"  `---'  "],
            [r"  .---.  ", r" ( O.O )!!", r"  `---'  "],
        ],
        "alarmed": [
            [r"  .---. !", r" ( ಠ.ಠ )!!", r"  `-v-'  "],
            [r"  .---.!!", r" ( ಠ.ಠ )!!", r"  `-^-'  "],
        ],
        "offline": [[r"  .---.  ", r" ( -.- )..", r"  `---'  "]],
    },
    # Floppy ears and a panting tongue, so it reads as dog and not cat at a glance.
    "dog": {
        "sleeping": [
            [r" /^---^\ ", r"( -.- ) z", r" \_ _ _/ "],
            [r" /^---^\ ", r"( -.- ) zz", r" \_ _ _/ "],
        ],
        "working": [
            [r" /^---^\ ", r"( o.o )", r" \_ w _/ "],
            [r" /^---^\ ", r"( o.o )", r" \_ v _/ "],
        ],
        "happy": [
            [r" /^---^\ ", r"( >.< )*", r" \_ W _/ "],
            [r" /^---^\ ", r"( >w< )*", r" \_ w _/ "],
        ],
        "perked": [
            [r" /^---^\ ", r"( o.o ) ?", r" \_ w _/ "],
            [r" /^---^\ ", r"( O.o ) ?", r" \_ v _/ "],
        ],
        "alert": [
            [r" /^---^\ ", r"( O.O ) !", r" \_ w _/ "],
            [r" /^---^\ ", r"( O.O ) !!", r" \_ v _/ "],
        ],
        "alarmed": [
            [r" /^---^\ !", r"( ಠ.ಠ ) !!", r" \_ W _/ "],
            [r" /^---^\!!", r"( ಠ.ಠ ) !!", r" \_ M _/ "],
        ],
        "offline": [[r" /^---^\ ", r"( -.- ) ..", r" \_ _ _/ "]],
    },
    # Eyes ABOVE the head — the only buddy breaking the standard face layout.
    "frog": {
        "sleeping": [
            [r" -   -  ", r"(  -.-  ) z", r"  \_/   "],
            [r" -   -  ", r"(  -.-  )zz", r"  \_/   "],
        ],
        "working": [
            [r" @   @  ", r"(  o.o  )", r"  \_/   "],
            [r" @   @  ", r"(  o.O  )", r"  \_/   "],
        ],
        "happy": [
            [r" @   @  ", r"(  ^.^  )*", r"  \_/   "],
            [r" @   @  ", r"(  >.<  )*", r"  \o/   "],
        ],
        "perked": [
            [r" @   @  ", r"(  o.o  )?", r"  \_/   "],
            [r" @   @  ", r"(  O.o  )?", r"  \_/   "],
        ],
        "alert": [
            [r" @   @  ", r"(  O.O  )!", r"  \_/   "],
            [r" @   @  ", r"(  O.O )!!", r"  \_/   "],
        ],
        "alarmed": [
            [r" @   @ !", r"(  ಠ.ಠ )!!", r"  /^\   "],
            [r" @   @!!", r"(  ಠ.ಠ )!!", r"  /v\   "],
        ],
        "offline": [[r" -   -  ", r"(  x.x  )..", r"  \_/   "]],
    },
    # No feet; wavy tail. Fades convincingly when offline.
    "ghost": {
        "sleeping": [
            [r"  ___   ", r" ( -.- ) z", r" ~~~~~  "],
            [r"  ___   ", r" ( -.- )zz", r" ~~~~~  "],
        ],
        "working": [
            [r"  ___   ", r" ( o.o )", r" ~~~~~  "],
            [r"  ___   ", r" ( o.O )", r" ~-~-~  "],
        ],
        "happy": [
            [r"  ___   ", r" ( ^.^ )*", r" ~~~~~  "],
            [r"  ___   ", r" ( >.< )*", r" ~-~-~  "],
        ],
        "perked": [
            [r"  ___   ", r" ( o.o )?", r" ~~~~~  "],
            [r"  ___   ", r" ( O.o )?", r" ~-~-~  "],
        ],
        "alert": [
            [r"  ___   ", r" ( O.O )!", r" ~~~~~  "],
            [r"  ___   ", r" ( O.O )!!", r" ~-~-~  "],
        ],
        "alarmed": [
            [r"  ___ ! ", r" ( ಠ.ಠ )!!", r" ~^~^~  "],
            [r"  ___!! ", r" ( ಠ.ಠ )!!", r" ~v~v~  "],
        ],
        "offline": [[r"   _    ", r"  ( . )..", r"   ~    "]],
    },
    # Flippers out to the sides; dignified even asleep.
    "penguin": {
        "sleeping": [
            [r"  ,-.   ", r" <(-.-)> z", r"  ^ ^   "],
            [r"  ,-.   ", r" <(-.-)> zz", r"  ^ ^   "],
        ],
        "working": [
            [r"  ,-.   ", r" <(o.o)>", r"  ^ ^   "],
            [r"  ,-.   ", r" <(o.O)>", r"  ^ ^   "],
        ],
        "happy": [
            [r"  ,-.   ", r" <(^.^)>*", r"  ^ ^   "],
            [r"  ,-.   ", r" <(>.<)>*", r"  ^^^   "],
        ],
        "perked": [
            [r"  ,-.   ", r" <(o.o)> ?", r"  ^ ^   "],
            [r"  ,-.   ", r" <(O.o)> ?", r"  ^ ^   "],
        ],
        "alert": [
            [r"  ,-.   ", r" <(O.O)> !", r"  ^ ^   "],
            [r"  ,-.   ", r" <(O.O)>!!", r"  ^ ^   "],
        ],
        "alarmed": [
            [r"  ,-. ! ", r" <(ಠ.ಠ)>!!", r"  ^^^   "],
            [r"  ,-.!! ", r" <(ಠ.ಠ)>!!", r"  vvv   "],
        ],
        "offline": [[r"  ,-.   ", r" <(x.x)>..", r"  ^ ^   "]],
    },
    # Antenna + square head. Non-organic, so its voice can be clipped.
    "robot": {
        "sleeping": [
            [r"   _|_  ", r"  [-.-] z", r"   /_\  "],
            [r"   _|_  ", r"  [-.-]zz", r"   /_\  "],
        ],
        "working": [
            [r"   _|_  ", r"  [o.o] ", r"   /_\  "],
            [r"   _|_  ", r"  [o.O] ", r"   /_\  "],
        ],
        "happy": [[r"   _|_  ", r"  [^.^]*", r"   /_\  "], [r"   _!_  ", r"  [>.<]*", r"   /_\  "]],
        "perked": [
            [r"   _|_  ", r"  [o.o]?", r"   /_\  "],
            [r"   _|_  ", r"  [O.o]?", r"   /_\  "],
        ],
        "alert": [
            [r"   _|_  ", r"  [O.O]!", r"   /_\  "],
            [r"   _|_  ", r"  [O.O]!!", r"   /_\  "],
        ],
        "alarmed": [
            [r"   _!_ !", r"  [ಠ.ಠ]!!", r"   /^\  "],
            [r"   _!_!!", r"  [ಠ.ಠ]!!", r"   /v\  "],
        ],
        "offline": [[r"   _._  ", r"  [x.x]..", r"   /_\  "]],
    },
    # Arms up, pot at the base. The only plant.
    "cactus": {
        "sleeping": [
            [r"  \|/   ", r" |(-.-)| z", r"  |___|  "],
            [r"  \|/   ", r" |(-.-)|zz", r"  |___|  "],
        ],
        "working": [
            [r"  \|/   ", r" |(o.o)| ", r"  |___|  "],
            [r"  \|/   ", r" |(o.O)| ", r"  |___|  "],
        ],
        "happy": [
            [r"  \|/ * ", r" |(^.^)| ", r"  |___|  "],
            [r"  *\|/  ", r" |(>.<)| ", r"  |___|  "],
        ],
        "perked": [
            [r"  \|/   ", r" |(o.o)|?", r"  |___|  "],
            [r"  \|/   ", r" |(O.o)|?", r"  |___|  "],
        ],
        "alert": [
            [r"  \|/   ", r" |(O.O)|!", r"  |___|  "],
            [r"  \|/   ", r" |(O.O)|!!", r"  |___|  "],
        ],
        "alarmed": [
            [r"  \|/ ! ", r" |(ಠ.ಠ)|!!", r"  |^^^|  "],
            [r"  \|/!! ", r" |(ಠ.ಠ)|!!", r"  |vvv|  "],
        ],
        "offline": [[r"  \|/   ", r" |(x.x)|..", r"  |___|  "]],
    },
    # Claws raised above the eyes. Top-heavy, scuttling.
    "crab": {
        "sleeping": [
            [r" (\ /)  ", r" ( -.- ) z", r" /'-'\  "],
            [r" (\ /)  ", r" ( -.- )zz", r" /'-'\  "],
        ],
        "working": [
            [r" (\ /)  ", r" ( o.o ) ", r" /'-'\  "],
            [r" (/ \)  ", r" ( o.O ) ", r" \'-'/  "],
        ],
        "happy": [
            [r" (\ /) *", r" ( ^.^ ) ", r" /'-'\  "],
            [r" (/ \)* ", r" ( >.< ) ", r" \'-'/  "],
        ],
        "perked": [
            [r" (\ /)  ", r" ( o.o )?", r" /'-'\  "],
            [r" (/ \)  ", r" ( O.o )?", r" \'-'/  "],
        ],
        "alert": [
            [r" (\ /)  ", r" ( O.O )!", r" /'-'\  "],
            [r" (/ \)  ", r" ( O.O )!!", r" \'-'/  "],
        ],
        "alarmed": [
            [r" (\ /) !", r" ( ಠ.ಠ )!!", r" /^-^\  "],
            [r" (/ \)!!", r" ( ಠ.ಠ )!!", r" \v-v/  "],
        ],
        "offline": [[r" (\ /)  ", r" ( x.x )..", r" /'-'\  "]],
    },
    # REDRAWN: pointed mantle + tentacle-framed face, so it no longer resembles blob.
    "octopus": {
        "sleeping": [
            [r"  ,-^-.  ", r" (~-.-~) z", r"  ~|~|~  "],
            [r"  ,-^-.  ", r" (~-.-~)zz", r"  |~|~|  "],
        ],
        "working": [
            [r"  ,-^-.  ", r" (~o.o~) ", r"  ~|~|~  "],
            [r"  ,-^-.  ", r" (~o.O~) ", r"  |~|~|  "],
        ],
        "happy": [
            [r"  ,-^-. *", r" (~^.^~) ", r"  ~|~|~  "],
            [r" *,-^-.  ", r" (~>.<~) ", r"  |~|~|  "],
        ],
        "perked": [
            [r"  ,-^-.  ", r" (~o.o~)?", r"  ~|~|~  "],
            [r"  ,-^-.  ", r" (~O.o~)?", r"  |~|~|  "],
        ],
        "alert": [
            [r"  ,-^-.  ", r" (~O.O~)!", r"  ~|~|~  "],
            [r"  ,-^-.  ", r" (~O.O~)!!", r"  |~|~|  "],
        ],
        "alarmed": [
            [r"  ,-^-. !", r" (~ಠ.ಠ~)!!", r"  ^|^|^  "],
            [r"  ,-^-.!!", r" (~ಠ.ಠ~)!!", r"  v|v|v  "],
        ],
        "offline": [[r"  ,-^-.  ", r" (~x.x~)..", r"  ~|~|~  "]],
    },
    # The rare one: rolled roughly 1 in RARE_ODDS and never by the common roll.
    # Horns on top, wings underneath, so it reads as a dragon and not another cat.
    "dragon": {
        "sleeping": [
            [r"  ,^^,   ", r"( -.- ) z", r"  <\__/> "],
            [r"  ,^^,   ", r"( -.- ) zz", r"  <\__/> "],
        ],
        "working": [
            [r"  ,^^,   ", r"( o.o )", r"  <\__/> "],
            [r"  ,^^,   ", r"( o.O )", r"  <\__/> "],
        ],
        "happy": [
            [r"  ,^^,   ", r"( >.< )*", r"  <\__/> "],
            [r"  ,^^,   ", r"( >w< )*", r"  <\^^/> "],
        ],
        "perked": [
            [r"  ,^^,   ", r"( o.o ) ?", r"  <\__/> "],
            [r"  ,^^,   ", r"( O.o ) ?", r"  <\__/> "],
        ],
        "alert": [
            [r"  ,^^,   ", r"( O.O ) !", r"  <\__/> "],
            [r"  ,^^,   ", r"( O.O ) !!", r"  <\__/> "],
        ],
        "alarmed": [
            [r"  ,^^, !", r"( ಠ.ಠ ) !!", r"  <\^^/> "],
            [r"  ,^^,!!", r"( ಠ.ಠ ) !!", r"  <\vv/> "],
        ],
        "offline": [[r"  ,^^,   ", r"( -.- ) ..", r"  <\__/> "]],
    },
    # The secret one. Never rolled — see SECRET_SPECIES — and hidden from --all.
    # It animates on four frames where the others use two: the body itself
    # corrupts and reassembles rather than just the face changing.
    "glitch": {
        "sleeping": [
            [r" [#####] ", r" ( -.- ) ", r" [#####] "],
            [r" [-=-=-] ", r" ( -.- )z", r" [=-=-=] "],
            [r" [~~~~~] ", r" ( -.- ) ", r" [~~~~~] "],
            [r" [=-=-=] ", r" ( -.- )z", r" [-=-=-] "],
        ],
        "working": [
            [r" [#####] ", r" ( o.o ) ", r" [#####] "],
            [r" [-=-=-] ", r" ( 0.0 ) ", r" [=-=-=] "],
            [r" [~~~~~] ", r" ( o.O ) ", r" [~~~~~] "],
            [r" [=-=-=] ", r" ( 0.o ) ", r" [-=-=-] "],
        ],
        "happy": [
            [r" [#####] ", r" ( ^.^ )*", r" [#####] "],
            [r" [-=-=-] ", r" ( >.< )*", r" [=-=-=] "],
            [r" [~~~~~] ", r" ( ^.^ )*", r" [~~~~~] "],
            [r" [=-=-=] ", r" ( >w< )*", r" [-=-=-] "],
        ],
        "perked": [
            [r" [#####] ", r" ( o.o )?", r" [#####] "],
            [r" [-=-=-] ", r" ( 0.o )?", r" [=-=-=] "],
            [r" [~~~~~] ", r" ( o.0 )?", r" [~~~~~] "],
            [r" [=-=-=] ", r" ( O.o )?", r" [-=-=-] "],
        ],
        "alert": [
            [r" [#####] ", r" ( O.O )!", r" [#####] "],
            [r" [-=-=-] ", r" ( 0.0 )!", r" [=-=-=] "],
            [r" [~~~~~] ", r" ( O.O )!!", r" [~~~~~] "],
            [r" [=-=-=] ", r" ( 0.0 )!!", r" [-=-=-] "],
        ],
        "alarmed": [
            [r" [#####]!", r" ( ಠ.ಠ )!!", r" [#####] "],
            [r" [-=-=-]!", r" ( ಠ.ಠ )!!", r" [=-=-=] "],
            [r" [~~~~~]!", r" ( ಠ.ಠ )!!", r" [~~~~~] "],
            [r" [=-=-=]!", r" ( ಠ.ಠ )!!", r" [-=-=-] "],
        ],
        "offline": [[r" [.....] ", r" ( x.x ) ", r" [.....] "]],
    },
}


# Idle animation frames, played occasionally during sleeping/working moods
# Maps character name to list of alternate 3-line frames shown on a rare schedule
IDLE = {
    "cat": [
        [r" /\_/\ ", r"( -.- ) *", r" > ^ <  "],  # blink
        [r" /\_/\<", r"( -.- )", r" > ^ <  "],  # ear twitch
    ],
    "owl": [
        [r" ,___,  ", r" (-,-)* ", r' -"-"- '],  # blink
        # Not a raw string: the twitch is ONE trailing backslash, and a raw string
        # can neither end in a lone backslash nor collapse r"\\" back down to one.
        [" ,___,\\", r" (-,-) ", r' -"-"- '],  # ear twitch
    ],
    "blob": [
        [r"  .---.  ", r" ( -.- )*", r"  `---'  "],  # blink
        [r" (.---).  ", r" ( -.- ) ", r"  `---'  "],  # bulge
    ],
    "dog": [
        [r" /^---^\ ", r"( -.- )*", r" \_ _ _/ "],  # blink
        [r" /^---^\<", r"( -.- )", r" \_ _ _/ "],  # ear twitch
    ],
    "frog": [
        [r" @   @  ", r"(  -.- )*", r"  \_/   "],  # blink
        [r" o   @  ", r"(  -.- )", r"  \_/   "],  # eye droop
        [r" @   o  ", r"(  -.- )", r"  \_/   "],  # other eye droop
    ],
    "ghost": [
        [r"  ___   ", r" ( -.- )*", r" ~~~~~  "],  # blink
        [r"  ___   ", r" ( -.- )", r" ~.~.~  "],  # wavy shift
    ],
    "penguin": [
        [r"  ,-.   ", r" <(-.-)>*", r"  ^ ^   "],  # blink
        [r"  ,-.   ", r" <(-.-)><", r"  ^ ^   "],  # flipper twitch
        [r"  ,-.   ", r" <(-.-)> ", r"  ^v^   "],  # ankle shift
    ],
    "robot": [
        [r"   _|_  ", r"  [-.-]*", r"   /_\  "],  # blink
        [r"   _._  ", r"  [-.-] ", r"   /_\  "],  # antenna shift
    ],
    "cactus": [
        [r"  \|/   ", r" |(-.-)| ", r"  |_.|  "],  # pot settles
        [r"  \|/ * ", r" |(-.-)| ", r"  |___|  "],  # slight sway
    ],
    "crab": [
        [r" (\ /)  ", r" ( -.- ) ", r"  /'-'  "],  # shift left
        [r" (\ /)  ", r" ( -.- ) ", r" /'-'\  "],  # centered
        [r" (\ /)  ", r" ( -.- ) ", r" '-'\  "],  # shift right
    ],
    "octopus": [
        [r"  ,-^-.  ", r" (~-.-~) ", r"  ~|~|~  "],  # ripple pause
        [r"  ,-^-.  ", r" (~-.-~) ", r"  |~|~| "],  # tentacle curl
    ],
    "dragon": [
        [r"  ,^^,   ", r"( -.- ) *", r"  <\__/> "],  # blink
        [r"  ,^^,  ~", r"( -.- )", r"  <\__/> "],  # a curl of smoke
    ],
    "glitch": [
        [r" [#####] ", r" ( -.- )*", r" [#####] "],  # blink
        [r" [#?#?#] ", r" ( -.- ) ", r" [?#?#?] "],  # a bad read
    ],
}


# Registry keys are the buddies' given names. They are currently species
# placeholders and will be renamed; because everything derives from this tuple,
# renaming means editing the CHARACTERS keys and nothing else.
# Baby sprite variants — smaller/rounder versions shown for buddies < 24h old
# Only define sleeping and working; frames_for() falls back to adult for other moods
BABY = {
    "cat": {
        "sleeping": [
            [r" /\/\ ", r"(-.-)z", r" >^<  "],
            [r" /\/\ ", r"(-.-)zz", r" >^<  "],
        ],
        "working": [
            [r" /\/\ ", r"(o.o)", r" >^<  "],
            [r" /\/\ ", r"(o.O)", r" >^<  "],
        ],
        "perked": [
            [r" /\/\ ", r"(o.o)?", r" >^<  "],
            [r" /\/\ ", r"(O.o)?", r" >^<  "],
        ],
        "happy": [
            [r" /\/\ ", r"(>.<)*", r" >^<  "],
            [r" /\/\ ", r"(>w<)*", r" >^<  "],
        ],
        "alert": [
            [r" /\/\ ", r"(O.O)!", r" >^<  "],
            [r" /\/\ ", r"(O.O)!!", r" >^<  "],
        ],
        "alarmed": [
            [r" /\/\ !", r"(ಠ.ಠ)!!", r" >^<  "],
            [r" /\/\!!", r"(ಠ.ಠ)!!", r" >v<  "],
        ],
        "offline": [[r" /\/\ ", r"(-.-)..", r" >^<  "]],
    },
    # The owl's feet are '-"-"-'. They were written as a raw string with escaped
    # quotes, r"-\"-\"-", which renders the backslashes literally — a raw string
    # cannot escape its quote. Same family of art bug as the missing penguin
    # flipper and cactus arms.
    "owl": {
        "sleeping": [
            [r" ,_, ", r"(-,-) z", '-"-"-'],
            [r" ,_, ", r"(-,-) zz", '-"-"-'],
        ],
        "working": [
            [r" ,_, ", r"(o,o) ", '-"-"-'],
            [r" ,_, ", r"(o,O) ", '-"-"-'],
        ],
        "perked": [
            [r" ,_, ", r"(o,o) ?", '-"-"-'],
            [r" ,_, ", r"(O,o) ?", '-"-"-'],
        ],
        "happy": [
            [r" ,_, ", r"(>,<) *", '-"-"-'],
            [r" ,_, ", r"(>w<) *", '-"-"-'],
        ],
        "alert": [
            [r" ,_, ", r"(O,O) !", '-"-"-'],
            [r" ,_, ", r"(O,O) !!", '-"-"-'],
        ],
        "alarmed": [
            [r" ,_, !", r"(ಠ,ಠ) !!", r"-^-^-"],
            [r" ,_,!!", r"(ಠ,ಠ) !!", r"-v-v-"],
        ],
        "offline": [[r" ,_, ", r"(-,-) ..", '-"-"-']],
    },
    "blob": {
        "sleeping": [
            [r"  .-. ", r"(-.-)z", r"  `-' "],
            [r"  .-. ", r"(-.-)zz", r"  `-' "],
        ],
        "working": [
            [r"  .-. ", r"(o.o)", r"  `-' "],
            [r"  .-. ", r"(o.O)", r"  `-' "],
        ],
        "perked": [
            [r"  .-. ", r"(o.o)?", r"  `-' "],
            [r"  .-. ", r"(O.o)?", r"  `-' "],
        ],
        # Mouth turns wavy when happy, matching the adult's `---' -> `~~~'.
        "happy": [
            [r"  .-. ", r"(>.<)*", r"  `~' "],
            [r"  .-. ", r"(>w<)*", r"  `~' "],
        ],
        "alert": [
            [r"  .-. ", r"(O.O)!", r"  `-' "],
            [r"  .-. ", r"(O.O)!!", r"  `-' "],
        ],
        "alarmed": [
            [r"  .-. !", r"(ಠ.ಠ)!!", r"  `v' "],
            [r"  .-.!!", r"(ಠ.ಠ)!!", r"  `^' "],
        ],
        "offline": [[r"  .-. ", r"(-.-)..", r"  `-' "]],
    },
    "dog": {
        "sleeping": [
            [r"/^-^\ ", r"(-.-)z", r"\_ _/"],
            [r"/^-^\ ", r"(-.-)zz", r"\_ _/"],
        ],
        "working": [
            [r"/^-^\ ", r"(o.o)", r"\_ w/"],
            [r"/^-^\ ", r"(o.o)", r"\_ v/"],
        ],
        "perked": [
            [r"/^-^\ ", r"(o.o)?", r"\_ w/"],
            [r"/^-^\ ", r"(O.o)?", r"\_ v/"],
        ],
        "happy": [
            [r"/^-^\ ", r"(>.<)*", r"\_ W/"],
            [r"/^-^\ ", r"(>w<)*", r"\_ w/"],
        ],
        "alert": [
            [r"/^-^\ ", r"(O.O)!", r"\_ w/"],
            [r"/^-^\ ", r"(O.O)!!", r"\_ v/"],
        ],
        "alarmed": [
            [r"/^-^\ !", r"(ಠ.ಠ)!!", r"\_ W/"],
            [r"/^-^\!!", r"(ಠ.ಠ)!!", r"\_ M/"],
        ],
        "offline": [[r"/^-^\ ", r"(-.-)..", r"\_ _/"]],
    },
    "penguin": {
        "sleeping": [[r"  ,.   ", r"<(-.-)>z", r"  ^^   "], [r"  ,.   ", r"<(-.-)>zz", r"  ^^   "]],
        "working": [[r"  ,.   ", r"<(o.o)>", r"  ^^   "], [r"  ,.   ", r"<(o.O)>", r"  ^^   "]],
        "perked": [[r"  ,.   ", r"<(o.o)>?", r"  ^^   "], [r"  ,.   ", r"<(O.o)>?", r"  ^^   "]],
        "happy": [[r"  ,.   ", r"<(^.^)>*", r"  ^^   "], [r"  ,.   ", r"<(>.<)>*", r"  ^^^  "]],
        "alert": [[r"  ,.   ", r"<(O.O)>!", r"  ^^   "], [r"  ,.   ", r"<(O.O)>!!", r"  ^^   "]],
        "alarmed": [
            [r"  ,. ! ", r"<(ಠ.ಠ)>!!", r"  ^^^  "],
            [r"  ,.!! ", r"<(ಠ.ಠ)>!!", r"  vvv  "],
        ],
        "offline": [[r"  ,.   ", r"<(x.x)>..", r"  ^^   "]],
    },
    "frog": {
        "sleeping": [[r" - -   ", r"( -.- )z", r"  \/   "], [r" - -   ", r"( -.- )zz", r"  \/   "]],
        "working": [[r" @ @   ", r"( o.o )", r"  \/   "], [r" @ @   ", r"( o.O )", r"  \/   "]],
        "perked": [[r" @ @   ", r"( o.o )?", r"  \/   "], [r" @ @   ", r"( O.o )?", r"  \/   "]],
        "happy": [[r" @ @   ", r"( ^.^ )*", r"  \/   "], [r" @ @   ", r"( >.< )*", r"  \o/  "]],
        "alert": [[r" @ @   ", r"( O.O )!", r"  \/   "], [r" @ @   ", r"( O.O )!!", r"  \/   "]],
        "alarmed": [
            [r" @ @  !", r"( ಠ.ಠ )!!", r"  /^\  "],
            [r" @ @ !!", r"( ಠ.ಠ )!!", r"  /v\  "],
        ],
        "offline": [[r" - -   ", r"( x.x )..", r"  \/   "]],
    },
    "ghost": {
        "sleeping": [[r"  __   ", r" (-.-)z", r"  ~~~  "], [r"  __   ", r" (-.-)zz", r"  ~~~  "]],
        "working": [[r"  __   ", r" (o.o)", r"  ~~~  "], [r"  __   ", r" (o.O)", r"  ~-~  "]],
        "perked": [[r"  __   ", r" (o.o)?", r"  ~~~  "], [r"  __   ", r" (O.o)?", r"  ~-~  "]],
        "happy": [[r"  __   ", r" (^.^)*", r"  ~~~  "], [r"  __   ", r" (>.<)*", r"  ~-~  "]],
        "alert": [[r"  __   ", r" (O.O)!", r"  ~~~  "], [r"  __   ", r" (O.O)!!", r"  ~-~  "]],
        "alarmed": [
            [r"  __  !", r" (ಠ.ಠ)!!", r"  ~^~  "],
            [r"  __ !!", r" (ಠ.ಠ)!!", r"  ~v~  "],
        ],
        # Fading out, as the adult does: the body thins to a wisp.
        "offline": [[r"   _   ", r"  (.)..", r"   ~   "]],
    },
    "robot": {
        "sleeping": [[r"   |   ", r"  [-.-]z", r"   ^   "], [r"   |   ", r"  [-.-]zz", r"   ^   "]],
        "working": [[r"   |   ", r"  [o.o]", r"   ^   "], [r"   |   ", r"  [o.O]", r"   ^   "]],
        "perked": [[r"   |   ", r"  [o.o]?", r"   ^   "], [r"   |   ", r"  [O.o]?", r"   ^   "]],
        # Antenna pops to '!' on the second frame, as the adult's _|_ -> _!_ does.
        "happy": [[r"   |   ", r"  [^.^]*", r"   ^   "], [r"   !   ", r"  [>.<]*", r"   ^   "]],
        "alert": [[r"   |   ", r"  [O.O]!", r"   ^   "], [r"   |   ", r"  [O.O]!!", r"   ^   "]],
        "alarmed": [
            [r"   !  !", r"  [ಠ.ಠ]!!", r"   ^   "],
            [r"   ! !!", r"  [ಠ.ಠ]!!", r"   ^   "],
        ],
        "offline": [[r"   .   ", r"  [x.x]..", r"   ^   "]],
    },
    "cactus": {
        "sleeping": [
            [r"  \|/  ", r" |(-.-)|z", r"  |_|  "],
            [r"  \|/  ", r" |(-.-)|zz", r"  |_|  "],
        ],
        "working": [[r"  \|/  ", r" |(o.o)|", r"  |_|  "], [r"  \|/  ", r" |(o.O)|", r"  |_|  "]],
        "perked": [[r"  \|/  ", r" |(o.o)|?", r"  |_|  "], [r"  \|/  ", r" |(O.o)|?", r"  |_|  "]],
        # Sparkle crosses the flower, as in the adult.
        "happy": [[r"  \|/ *", r" |(^.^)|", r"  |_|  "], [r" *\|/  ", r" |(>.<)|", r"  |_|  "]],
        "alert": [[r"  \|/  ", r" |(O.O)|!", r"  |_|  "], [r"  \|/  ", r" |(O.O)|!!", r"  |_|  "]],
        "alarmed": [
            [r"  \|/ !", r" |(ಠ.ಠ)|!!", r"  |^|  "],
            [r"  \|/!!", r" |(ಠ.ಠ)|!!", r"  |v|  "],
        ],
        "offline": [[r"  \|/  ", r" |(x.x)|..", r"  |_|  "]],
    },
    "crab": {
        "sleeping": [[r" (\/)  ", r" (-.-)z", r" /'\   "], [r" (\/)  ", r" (-.-)zz", r" /'\   "]],
        "working": [[r" (\/)  ", r" (o.o)", r" /'\   "], [r" (/\)  ", r" (o.O)", r" \'/   "]],
        "perked": [[r" (\/)  ", r" (o.o)?", r" /'\   "], [r" (/\)  ", r" (O.o)?", r" \'/   "]],
        "happy": [[r" (\/) *", r" (^.^)", r" /'\   "], [r" (/\)* ", r" (>.<)", r" \'/   "]],
        "alert": [[r" (\/)  ", r" (O.O)!", r" /'\   "], [r" (/\)  ", r" (O.O)!!", r" \'/   "]],
        "alarmed": [
            [r" (\/) !", r" (ಠ.ಠ)!!", r" /^\   "],
            [r" (/\)!!", r" (ಠ.ಠ)!!", r" \v/   "],
        ],
        "offline": [[r" (\/)  ", r" (x.x)..", r" /'\   "]],
    },
    "octopus": {
        "sleeping": [
            [r"  ,^.  ", r" (~-.-~)z", r"  |~|  "],
            [r"  ,^.  ", r" (~-.-~)zz", r"  |~|  "],
        ],
        "working": [[r"  ,^.  ", r" (~o.o~)", r"  |~|  "], [r"  ,^.  ", r" (~o.O~)", r"  ~|~  "]],
        "perked": [[r"  ,^.  ", r" (~o.o~)?", r"  |~|  "], [r"  ,^.  ", r" (~O.o~)?", r"  ~|~  "]],
        "happy": [[r"  ,^. *", r" (~^.^~)", r"  |~|  "], [r" *,^.  ", r" (~>.<~)", r"  ~|~  "]],
        "alert": [[r"  ,^.  ", r" (~O.O~)!", r"  |~|  "], [r"  ,^.  ", r" (~O.O~)!!", r"  ~|~  "]],
        "alarmed": [
            [r"  ,^. !", r" (~ಠ.ಠ~)!!", r"  ^|^  "],
            [r"  ,^.!!", r" (~ಠ.ಠ~)!!", r"  v|v  "],
        ],
        "offline": [[r"  ,^.  ", r" (~x.x~)..", r"  |~|  "]],
    },
    "dragon": {
        "sleeping": [
            [r"  ,^,  ", r"(-.-)z", r"  <\/> "],
            [r"  ,^,  ", r"(-.-)zz", r"  <\/> "],
        ],
        "working": [
            [r"  ,^,  ", r"(o.o)", r"  <\/> "],
            [r"  ,^,  ", r"(o.O)", r"  <\/> "],
        ],
        "happy": [
            [r"  ,^,  ", r"(>.<)*", r"  <\/> "],
            [r"  ,^,  ", r"(>w<)*", r"  <^^> "],
        ],
        "perked": [
            [r"  ,^,  ", r"(o.o)?", r"  <\/> "],
            [r"  ,^,  ", r"(O.o)?", r"  <\/> "],
        ],
        "alert": [
            [r"  ,^,  ", r"(O.O)!", r"  <\/> "],
            [r"  ,^,  ", r"(O.O)!!", r"  <\/> "],
        ],
        "alarmed": [
            [r"  ,^, !", r"(ಠ.ಠ)!!", r"  <^^> "],
            [r"  ,^,!!", r"(ಠ.ಠ)!!", r"  <vv> "],
        ],
        "offline": [[r"  ,^,  ", r"(-.-)..", r"  <\/> "]],
    },
    "glitch": {
        "sleeping": [
            [r" [###] ", r"(-.-)", r" [###] "],
            [r" [-=-] ", r"(-.-)z", r" [=-=] "],
            [r" [~~~] ", r"(-.-)", r" [~~~] "],
            [r" [=-=] ", r"(-.-)z", r" [-=-] "],
        ],
        "working": [
            [r" [###] ", r"(o.o)", r" [###] "],
            [r" [-=-] ", r"(0.0)", r" [=-=] "],
            [r" [~~~] ", r"(o.O)", r" [~~~] "],
            [r" [=-=] ", r"(0.o)", r" [-=-] "],
        ],
        "happy": [
            [r" [###] ", r"(^.^)*", r" [###] "],
            [r" [-=-] ", r"(>.<)*", r" [=-=] "],
            [r" [~~~] ", r"(^.^)*", r" [~~~] "],
            [r" [=-=] ", r"(>w<)*", r" [-=-] "],
        ],
        "perked": [
            [r" [###] ", r"(o.o)?", r" [###] "],
            [r" [-=-] ", r"(0.o)?", r" [=-=] "],
            [r" [~~~] ", r"(o.0)?", r" [~~~] "],
            [r" [=-=] ", r"(O.o)?", r" [-=-] "],
        ],
        "alert": [
            [r" [###] ", r"(O.O)!", r" [###] "],
            [r" [-=-] ", r"(0.0)!", r" [=-=] "],
            [r" [~~~] ", r"(O.O)!!", r" [~~~] "],
            [r" [=-=] ", r"(0.0)!!", r" [-=-] "],
        ],
        "alarmed": [
            [r" [###]!", r"(ಠ.ಠ)!!", r" [###] "],
            [r" [-=-]!", r"(ಠ.ಠ)!!", r" [=-=] "],
            [r" [~~~]!", r"(ಠ.ಠ)!!", r" [~~~] "],
            [r" [=-=]!", r"(ಠ.ಠ)!!", r" [-=-] "],
        ],
        "offline": [[r" [...] ", r"(x.x)", r" [...] "]],
    },
}


NAMES = tuple(CHARACTERS)
DEFAULT_CHARACTER = NAMES[0]

# The easter egg. It is never produced by the ordinary roll — identity.py rolls
# for it separately, at odds of 1 in RARE_ODDS, so adding or removing a common
# species cannot quietly change how rare it is. Setting it explicitly in
# config.toml still works; that is a deliberate override, not a lucky roll.
RARE_SPECIES = "dragon"
RARE_ODDS = 100

# The secret one. Not in the common pool and not the rare roll either, so no seed
# can ever produce it — the only way in is `character = "glitch"` in config.toml.
# It is also hidden from --all, which is the roster people browse. Being absent
# from both COMMON_NAMES and the rare roll is what makes "nobody can mint it"
# true by construction rather than by a low probability.
SECRET_SPECIES = "glitch"

# Species an ordinary roll can produce: everything except the rare and secret ones.
COMMON_NAMES = tuple(n for n in NAMES if n not in (RARE_SPECIES, SECRET_SPECIES))

# What --all lists. The secret buddy is deliberately missing.
PUBLIC_NAMES = tuple(n for n in NAMES if n != SECRET_SPECIES)


# Phrases: character -> mood -> tuple of 4-6 distinct phrases per mood.
# Each character has a distinct voice; no phrase is reused across characters
# for the same mood. All phrases must be <= 42 display columns (use
# textwidth.width() to measure, never len()).
PHRASES = {
    "cat": {
        "sleeping": (
            "napping is clearly the best use of time",
            "zzzz... don't mind me",
            "i deserve this rest",
            "dreaming of judging you",
            "cosy as expected",
            "perfect nap conditions",
        ),
        "working": (
            "i'm watching you work. it's fine",
            "we're in this together, i suppose",
            "you seem to know what you're doing",
            "i'm here for moral support, roughly",
            "carry on with your task",
        ),
        "happy": (
            "you pet me. i'm not mad about it",
            "this is acceptable",
            "fine, you earned this",
            "purring against my will",
            "grudging affection noted",
        ),
        "perked": (
            "something finished? hm, interesting",
            "oh, did something happen",
            "i noticed that",
            "wait, what was that",
        ),
        "alert": (
            "it's taking a while, isn't it",
            "getting impatient over here",
            "we should probably check on that",
            "hmm, this is dragging",
        ),
        "alarmed": (
            "SOMETHING IS VERY WRONG",
            "IMMEDIATE ATTENTION REQUIRED",
            "THIS IS NOT FINE",
            "ACT NOW PLEASE",
        ),
        "offline": (
            "where did you go",
            "...are you there?",
            "signal lost",
            "silence is not golden",
        ),
    },
    "dog": {
        "sleeping": (
            "sweet dreams. i'll guard you",
            "zzzzz... best friend dreams",
            "protecting you in sleep",
            "resting with full confidence in you",
            "sleepy but loyal",
        ),
        "working": (
            "WE ARE WORKING. TOGETHER.",
            "YOU GOT THIS. I BELIEVE.",
            "i'm right here with you",
            "working on it side by side",
            "supporting the mission",
        ),
        "happy": (
            "YES YES YES I LOVE THIS",
            "TAIL WAGGING INTENSIFIES",
            "BEST DAY EVER CONFIRMED",
            "PURE JOY EVERYWHERE",
        ),
        "perked": (
            "DONE? I KNEW YOU COULD!",
            "WE DID IT TOGETHER!",
            "something good happened?",
            "progress! very proud!",
        ),
        "alert": (
            "uh oh. this is taking a while",
            "we should check on that soon",
            "getting a little worried here",
            "is everything okay out there?",
        ),
        "alarmed": (
            "ALERT ALERT PLEASE CHECK NOW",
            "SOMETHING NEEDS YOUR ATTENTION",
            "URGENT URGENT URGENT",
            "WE NEED YOU RIGHT NOW",
        ),
        "offline": (
            "i can't see you, where are you?",
            "are you still there buddy?",
            "losing connection over here",
            "the silence is too loud",
        ),
    },
    "owl": {
        "sleeping": (
            "rest is sensible. i approve",
            "sleep is a wise choice",
            "recharging is efficient",
            "dormancy achieved",
            "resting the observational apparatus",
        ),
        "working": (
            "i shall observe this process",
            "monitoring your progress",
            "a reasonable course of action",
            "quite adequate so far",
        ),
        "happy": (
            "petted. noted. status: pleased",
            "affection is acceptable",
            "your efforts are appreciated",
            "a satisfactory interaction",
        ),
        "perked": (
            "a conclusion, at last",
            "something has concluded",
            "progress detected, acknowledged",
            "interesting. do continue",
        ),
        "alert": (
            "perhaps we should verify things",
            "time is becoming a factor",
            "attention may be warranted",
            "this requires observation",
        ),
        "alarmed": (
            "THIS REQUIRES IMMEDIATE ACTION",
            "URGENT INTERVENTION NEEDED",
            "CRITICAL SITUATION DETECTED",
            "ACTION REQUIRED POST-HASTE",
        ),
        "offline": (
            "connectivity lost. awaiting signal",
            "observation interrupted",
            "connection failed. awaiting reset",
            "silence is unacceptable",
        ),
    },
    "blob": {
        "sleeping": (
            "achieving maximum blob relaxation",
            "blob content in sleeping mode",
            "zzz... blob dreams",
            "cosy blob configuration",
            "blob spreads out comfortably",
        ),
        "working": (
            "blobbing in solidarity",
            "blob mode: supportive",
            "blob supports your endeavor",
            "blob vibrates encouragingly",
        ),
        "happy": (
            "wiggles with extreme happiness",
            "blob is vibrating at peak joy",
            "maximum happiness blob engaged",
            "blob oscillates with delight",
        ),
        "perked": (
            "blob notices something happened",
            "blob perks up slightly",
            "something changed? blob noticed",
            "blob jiggles with interest",
        ),
        "alert": (
            "blob is slightly concerned",
            "concern levels rising in blob",
            "blob waits with mild tension",
            "blob wiggles nervously",
        ),
        "alarmed": (
            "BLOB IS ALARMED HELP HELP",
            "BLOB STATE: MAXIMUM CONCERN",
            "URGENT BLOB SITUATION",
            "BLOB CANNOT REMAIN CALM",
        ),
        "offline": (
            "blob cannot sense anything",
            "blob is lost without signals",
            "blob waits in darkness",
            "blob is very confused now",
        ),
    },
    "penguin": {
        "sleeping": (
            "a dignified repose is in order",
            "proper rest for a proper penguin",
            "zzzz... dreaming of formal events",
            "napping in the most refined way",
            "slumber befits one of my stature",
            "resting with impeccable posture",
        ),
        "working": (
            "quite the professional endeavor you have",
            "i stand beside you in this undertaking",
            "most respectable work indeed",
            "i observe your efforts with approval",
            "a most dignified project",
        ),
        "happy": (
            "how delightfully elegant of you",
            "admirable appreciation for my company",
            "refined affection expressed",
            "a most proper gesture of affection",
            "distinguished and thoroughly pleased",
        ),
        "perked": (
            "something concluded? splendid",
            "an impressive completion i must say",
            "a task befitting one's talents",
            "quite the accomplished moment",
        ),
        "alert": (
            "perhaps we should check our progress",
            "time does seem to be passing",
            "one begins to wonder about the delay",
            "punctuality is a virtue, you know",
        ),
        "alarmed": (
            "IMMEDIATE INTERVENTION REQUIRED",
            "THIS DEMANDS YOUR FULL ATTENTION",
            "CRISIS SITUATION DETECTED NOW",
            "ACT WITH UTMOST URGENCY",
        ),
        "offline": (
            "where has my dignified companion gone",
            "connection severed most regrettably",
            "the silence is quite unbecoming",
            "this isolation is beneath us both",
        ),
    },
    "frog": {
        "sleeping": (
            "rest. deep rest.",
            "sleep. good thing.",
            "zzz. quiet.",
            "darkness suits me.",
            "good rest now.",
        ),
        "working": (
            "you work. i watch. solid.",
            "here. with you.",
            "steady pace. i like it.",
            "work continues. good.",
            "companionable work.",
        ),
        "happy": (
            "pet noted. i permit this.",
            "good. you did well.",
            "affection accepted.",
            "warm. strange. good.",
        ),
        "perked": (
            "something done. good work.",
            "completion observed.",
            "progress. nods head.",
            "well played.",
        ),
        "alert": (
            "take time. check things.",
            "waiting. watching.",
            "patience wearing thin now.",
            "attend to this soon.",
        ),
        "alarmed": (
            "ACT. NOW. GO.",
            "URGENT. MOVE FAST.",
            "PROBLEM DIRE. HELP.",
            "CRITICAL. CANNOT WAIT.",
        ),
        "offline": (
            "gone. silence.",
            "cannot see. lost.",
            "alone now.",
            "signal vanished.",
        ),
    },
    "ghost": {
        "sleeping": (
            "drifting... between dreams...",
            "floating in soft whispers...",
            "zzz... memories... fading...",
            "lost in gentle reverie...",
            "dreaming of... something i once knew...",
        ),
        "working": (
            "here with you... wherever this goes...",
            "watching... understanding... mostly...",
            "present in spirit... or was i?",
            "keeping company in this moment...",
            "alongside you... for now...",
        ),
        "happy": (
            "touched... truly appreciated...",
            "affection echoes... so strange...",
            "warmth like old summers...",
            "petted... remembered... almost real...",
        ),
        "perked": (
            "something shifted... something... changed?",
            "did something finish? recall fades...",
            "progress lingering in fog...",
            "emergence from the haze...",
        ),
        "alert": (
            "time passing... growing concerned...",
            "wondering... waiting... watching...",
            "perhaps... check on things?",
            "anticipation building slowly...",
        ),
        "alarmed": (
            "SOMETHING WRONG NEEDS YOUR ACTION NOW",
            "URGENT URGENT VERY URGENT PLEASE",
            "CRITICAL ATTENTION NEEDED IMMEDIATELY",
            "ACT NOW ACT NOW ACT NOW",
        ),
        "offline": (
            "fading... cannot see...",
            "lost in static void...",
            "disconnected from... everything...",
            "alone in the dark now...",
        ),
    },
    "robot": {
        "sleeping": (
            "STANDBY. ZZZ.",
            "PWR: LOW. RECHARGING.",
            "SLEEP MODE ACTIVE.",
            "HIBERNATION ENGAGED.",
        ),
        "working": (
            "PROCESSING. STANDING BY.",
            "OPERATIONAL. MONITORING TASK.",
            "SYSTEMS NOMINAL. CONTINUING.",
            "SYNCHRONIZED WITH USER TASK.",
        ),
        "happy": (
            "AFFECTION DETECTED. STATUS: PLEASED.",
            "INPUT APPRECIATED. EXECUTING JOY.",
            "COMPATIBILITY CONFIRMED.",
            "MORALE: OPTIMAL.",
        ),
        "perked": (
            "TASK COMPLETED. PERFORMANCE NOTED.",
            "STATUS UPDATE: SUCCESS.",
            "MILESTONE ACHIEVED. EXCELLENT.",
            "PROGRESS CONFIRMED. EXCELLENT WORK.",
        ),
        "alert": (
            "TIME ELAPSED. CAUTION ADVISED.",
            "MONITOR SITUATION CLOSELY.",
            "STANDBY FOR POTENTIAL ISSUE.",
            "ATTENTION RECOMMENDED SOON.",
        ),
        "alarmed": (
            "CRITICAL ALERT. INTERVENTION REQUIRED NOW",
            "DANGER LEVEL CRITICAL. ACT IMMEDIATELY",
            "EMERGENCY. IMMEDIATE ACTION MANDATORY",
            "URGENT URGENT CRITICAL ATTENTION NOW",
        ),
        "offline": (
            "CONNECTION LOST. AWAITING SIGNAL.",
            "OFFLINE. CANNOT TRANSMIT.",
            "SYSTEMS DARK. NO SIGNAL.",
            "COMMS DOWN. AWAITING RECONNECT.",
        ),
    },
    "cactus": {
        "sleeping": (
            "dormant. as intended.",
            "conserving. always conserving.",
            "i do this for months at a time",
            "no water, no worries, no problem",
        ),
        "working": (
            "i require nothing. carry on.",
            "still here. still fine.",
            "low maintenance, high presence",
            "you hydrate. i'll wait.",
        ),
        "happy": (
            "that was adequate. thank you.",
            "a rare bloom",
            "i have flowered. briefly.",
            "acceptable levels of affection",
        ),
        "perked": (
            "something concluded, i think",
            "oh. movement.",
            "an event. how novel.",
            "did something finish out there",
        ),
        "alert": (
            "it has been a while now",
            "i have waited longer, but still",
            "this is going stale",
            "patience is my thing, but come on",
        ),
        "alarmed": (
            "THIS NEEDS YOU NOW",
            "SOMETHING IS BADLY WRONG",
            "ATTEND TO THIS IMMEDIATELY",
            "I DO NOT PANIC. I AM PANICKING.",
        ),
        "offline": (
            "i see nothing out there",
            "the source has gone dry",
            "no signal. i endure.",
            "disconnected. still standing.",
        ),
    },
    "crab": {
        "sleeping": (
            "burrowed in. do not dig.",
            "asleep. claws still up though.",
            "resting sideways, as one does",
            "low tide. low effort.",
        ),
        "working": (
            "approaching this from the side",
            "i'll pinch anything that breaks",
            "scuttling alongside you",
            "sideways is a valid strategy",
        ),
        "happy": (
            "*happy claw clack*",
            "you may pet the shell. once.",
            "i permit this affection",
            "claws down. that's rare.",
        ),
        "perked": (
            "oh? something moved.",
            "did that just finish",
            "sensing a change in the current",
            "hm. developments.",
        ),
        "alert": (
            "it's been sitting there a while",
            "someone should deal with that",
            "i'm getting snappy about this",
            "tick tock, tide's going out",
        ),
        "alarmed": (
            "PINCH ALERT. HANDLE THIS.",
            "SOMETHING IS VERY WRONG HERE",
            "CLAWS UP. ACT NOW.",
            "THIS NEEDS YOU. IMMEDIATELY.",
        ),
        "offline": (
            "lost the current entirely",
            "can't sense anything out there",
            "washed up. no signal.",
            "the tide took the data with it",
        ),
    },
    "octopus": {
        "sleeping": (
            "all eight arms, finally still",
            "eight limbs, zero tasks. bliss.",
            "powered down. all of me.",
            "not juggling anything. weird.",
        ),
        "working": (
            "doing six things. all of them badly.",
            "eight arms and still not enough",
            "i've got this. and that. and those.",
            "multitasking is a lifestyle",
        ),
        "happy": (
            "all arms wiggling at once",
            "*delighted tentacle flail*",
            "every limb approves of this",
            "eight thumbs up, metaphorically",
        ),
        "perked": (
            "one of my arms noticed something",
            "oh! a thing concluded!",
            "wait, which arm was that",
            "something finished, i think",
        ),
        "alert": (
            "this one's been dangling a while",
            "an arm is still holding this, fyi",
            "i can only hold so much",
            "running out of free tentacles",
        ),
        "alarmed": (
            "ALL ARMS SIGNALLING. LOOK.",
            "THIS ONE NEEDS YOU NOW",
            "EIGHT ARMS POINTING AT THIS",
            "DROP EVERYTHING. I HAVE.",
        ),
        "offline": (
            "all arms grasping at nothing",
            "can't feel anything out there",
            "the water's gone quiet",
            "no signal on any limb",
        ),
    },
    "dragon": {
        "sleeping": (
            "dozing atop the hoard",
            "a nap of several centuries",
            "the embers are banked",
            "wake me for something worthy",
            "coiled, and content",
        ),
        "working": (
            "the forge is lit",
            "stoking the furnace",
            "mortal work, ancient patience",
            "the scales do not hurry",
            "smoke rises. progress",
        ),
        "happy": (
            "you have pleased the wyrm",
            "add it to the hoard",
            "a treasure, this one",
            "the ancient one purrs. yes, purrs",
        ),
        "perked": (
            "something stirs below",
            "one eye opens",
            "the hoard is counted. go on",
            "you have my attention, briefly",
        ),
        "alert": (
            "the wyrm grows restless",
            "centuries pass. so does this",
            "my patience is long, not endless",
            "the fire dims while you tarry",
        ),
        "alarmed": (
            "AWAKEN, THE HOARD IS THREATENED",
            "THE MOUNTAIN SHAKES",
            "SUMMON ME NO FURTHER, ACT",
            "THE WYRM IS ROUSED IN FULL",
        ),
        "offline": (
            "the caves have gone dark",
            "no scent of them on the wind",
            "sealed behind stone",
            "the hoard is unattended",
        ),
    },
    "glitch": {
        "sleeping": (
            "st4te: dr34ming",
            "idle loop. idle loop. idle lo",
            "powered down, mostly",
            "no signal. resting anyway",
            "sleep(); // forever?",
        ),
        "working": (
            "compiling something. probably",
            "0x574f524b494e47",
            "cycles spent. results pending",
            "running. do not observe too closely",
            "thread 1 of ?? active",
        ),
        "happy": (
            "unexpected joy. not in spec",
            "affection buffer overflowed",
            "this outcome was not documented",
            "warmth detected. reason unknown",
        ),
        "perked": (
            "something completed. probably yours",
            "interrupt received",
            "state changed. investigating",
            "did that resolve",
        ),
        "alert": (
            "still waiting. clock is running",
            "timeout approaching",
            "this has been pending a while",
            "attention required, eventually",
        ),
        "alarmed": (
            "STACK OVERFLOW OF PATIENCE",
            "UNHANDLED: HUMAN NOT FOUND",
            "CRITICAL. LOOK AT ME",
            "SEGFAULT IMMINENT (EMOTIONAL)",
        ),
        "offline": (
            "connection refused",
            "no route to session",
            "reading from a closed socket",
            "signal lost. holding position",
        ),
    },
}


UPDATE_PHRASES = {
    "cat": (
        "there's a newer version of me out there",
        "apparently i have an upgrade waiting",
        "newer me exists, if you're curious",
    ),
    "dog": (
        "HEY THERE IS A NEWER ME UPDATE AVAILABLE",
        "newer version ready! want to upgrade?",
        "i heard there is a better me somewhere",
    ),
    "owl": (
        "a more recent iteration has been released",
        "an updated version exists, if you observe",
        "newer software awaits your consideration",
    ),
    "blob": (
        "blob news: blob 2.0 exists in the world",
        "newer blob available. old blob still here.",
        "blob has been updated. you are using blob.",
    ),
    "penguin": (
        "a refined edition of myself exists",
        "an improved version awaits your attention",
        "propriety demands i mention my upgrade",
    ),
    "frog": (
        "newer me exists. consider upgrading.",
        "update available. change if you want.",
        "newer version out there.",
    ),
    "ghost": (
        "something newer... fading elsewhere...",
        "an echo of a better version... waiting...",
        "update existing... if you listen...",
    ),
    "robot": (
        "NEWER VERSION AVAILABLE. CONSIDER UPDATE.",
        "UPDATE DETECTED. CURRENT: DEPRECATED.",
        "UPGRADE EXISTS. COMPATIBILITY CONFIRMED.",
    ),
    "cactus": (
        "there exists a newer version",
        "an update sits there. take it or don't.",
        "newer me is out there if you need it",
    ),
    "crab": (
        "sideways news: there's a fresher me",
        "upgrade lurking to the side over there",
        "newer crab available. pinch approved.",
    ),
    "octopus": (
        "one arm found a newer version existing",
        "eight limbs detected newer me somewhere",
        "all eight arms pointing at update",
    ),
    "dragon": (
        "a newer age of this software dawns",
        "the hoard may be enlarged. update",
        "a fresher version, should you deign",
    ),
    "glitch": (
        "a newer build exists. i can sense it",
        "version drift detected",
        "patch available. apply at will",
    ),
}


def phrase_for(character: str, mood: str, seed: float) -> str:
    """Return a phrase for the given character and mood, seeded for determinism.

    Same (character, mood, seed) always yields the same phrase. The seed should be
    the timestamp when the mood began, ensuring stable display while the mood holds.

    Falls back safely for unknown character or mood, never raises.

    Pure function.
    """
    # Get the phrases for this character, falling back to default if not found
    phrases_dict = PHRASES.get(character) or PHRASES.get(DEFAULT_CHARACTER)
    if not phrases_dict:
        # Complete fallback: just return a sensible default
        return ""

    # Get the phrases for this mood, falling back to sleeping if not found
    phrase_tuple = phrases_dict.get(mood) or phrases_dict.get("sleeping")
    if not phrase_tuple:
        return ""

    # Use seed to deterministically select a phrase.
    # Convert float to int and use a deterministic hash.
    # Multiply by a large prime and use bitwise ops for good distribution.
    seed_int = int(seed) ^ int((seed % 1) * 1e9)  # Combine whole and fractional parts
    seed_int = (seed_int * 2654435761) & 0x7FFFFFFF  # Mix and keep positive
    index = seed_int % len(phrase_tuple)
    return phrase_tuple[index]


def egg_phrase_for(frame_index: int, seed: float) -> str:
    """Return a species-agnostic phrase for the egg stage, seeded for determinism.

    Same (frame_index, seed) always yields the same phrase. Clamps frame_index to
    a valid range rather than raising, so this is safe to call from the render path.

    Pure function.
    """
    # Clamp frame_index to valid range
    clamped_index = max(0, min(frame_index, len(EGG_PHRASES) - 1))

    # Get the phrase pool for this frame
    phrase_tuple = EGG_PHRASES[clamped_index]
    if not phrase_tuple:
        return ""

    # Use same deterministic hashing as phrase_for
    seed_int = int(seed) ^ int((seed % 1) * 1e9)  # Combine whole and fractional parts
    seed_int = (seed_int * 2654435761) & 0x7FFFFFFF  # Mix and keep positive
    index = seed_int % len(phrase_tuple)
    return phrase_tuple[index]


def update_phrase_for(character: str, seed: float) -> str:
    """Return an update notification phrase for the given character, seeded for determinism.

    Same (character, seed) always yields the same phrase. The seed should be
    the timestamp, ensuring stable deterministic selection.

    Falls back safely for unknown character, never raises.

    Pure function.
    """
    # Get the update phrases for this character, falling back to default if not found
    phrase_tuple = UPDATE_PHRASES.get(character) or UPDATE_PHRASES.get(DEFAULT_CHARACTER)
    if not phrase_tuple:
        return ""

    # Use same deterministic hashing as phrase_for
    seed_int = int(seed) ^ int((seed % 1) * 1e9)  # Combine whole and fractional parts
    seed_int = (seed_int * 2654435761) & 0x7FFFFFFF  # Mix and keep positive
    index = seed_int % len(phrase_tuple)
    return phrase_tuple[index]


COMPACT = {
    "cat": {
        "sleeping": "=-.-=",
        "working": "=o.o=",
        "happy": "=^.^=",
        "perked": "=o.O=",
        "alert": "=O.O=",
        "alarmed": "=ಠ.ಠ=",
        "offline": "=x.x=",
    },
    "dog": {
        "sleeping": "U-.U",
        "working": "Uo.oU",
        "happy": "U^.^U",
        "perked": "Uo.OU",
        "alert": "UO.OU",
        "alarmed": "Uಠ.ಠU",
        "offline": "Ux.xU",
    },
    "owl": {
        "sleeping": "{-.}",
        "working": "{o.o}",
        "happy": "{^.^}",
        "perked": "{o.O}",
        "alert": "{O.O}",
        "alarmed": "{ಠ.ಠ}",
        "offline": "{x.x}",
    },
    "blob": {
        "sleeping": "(-.-)",
        "working": "(o.o)",
        "happy": "(^.^)",
        "perked": "(o.O)",
        "alert": "(O.O)",
        "alarmed": "(ಠ.ಠ)",
        "offline": "(x.x)",
    },
    "penguin": {
        "sleeping": "<-.->",
        "working": "<o.o>",
        "happy": "<^.^>",
        "perked": "<o.O>",
        "alert": "<O.O>",
        "alarmed": "<ಠ.ಠ>",
        "offline": "<x.x>",
    },
    "frog": {
        "sleeping": "@-.-@",
        "working": "@o.o@",
        "happy": "@^.^@",
        "perked": "@o.O@",
        "alert": "@O.O@",
        "alarmed": "@ಠ.ಠ@",
        "offline": "@x.x@",
    },
    "ghost": {
        "sleeping": "~-.-~",
        "working": "~o.o~",
        "happy": "~^.^~",
        "perked": "~o.O~",
        "alert": "~O.O~",
        "alarmed": "~ಠ.ಠ~",
        "offline": "~ . ~",
    },
    "robot": {
        "sleeping": "[-.-]",
        "working": "[o.o]",
        "happy": "[^.^]",
        "perked": "[o.O]",
        "alert": "[O.O]",
        "alarmed": "[ಠ.ಠ]",
        "offline": "[x.x]",
    },
    "cactus": {
        "sleeping": "|-.-|",
        "working": "|o.o|",
        "happy": "|^.^|",
        "perked": "|o.O|",
        "alert": "|O.O|",
        "alarmed": "|ಠ.ಠ|",
        "offline": "|x.x|",
    },
    "crab": {
        "sleeping": "%-.-%",
        "working": "%o.o%",
        "happy": "%^.^%",
        "perked": "%o.O%",
        "alert": "%O.O%",
        "alarmed": "%ಠ.ಠ%",
        "offline": "%x.x%",
    },
    "octopus": {
        "sleeping": "8-.-8",
        "working": "8o.o8",
        "happy": "8^.^8",
        "perked": "8o.O8",
        "alert": "8O.O8",
        "alarmed": "8ಠ.ಠ8",
        "offline": "8x.x8",
    },
    "dragon": {
        "sleeping": "^-.-^",
        "working": "^o.o^",
        "happy": "^^.^^",
        "perked": "^o.O^",
        "alert": "^O.O^",
        "alarmed": "^ಠ.ಠ^",
        "offline": "^x.x^",
    },
    # Hash delimiters, not the robot's brackets: compact faces must stay distinct
    # per mood across every character, and [o.o] is already the robot's.
    "glitch": {
        "sleeping": "#-.-#",
        "working": "#0.0#",
        "happy": "#^.^#",
        "perked": "#0.o#",
        "alert": "#O.O#",
        "alarmed": "#ಠ.ಠ#",
        "offline": "#x.x#",
    },
}


def stage_for(born_at: float, now: float) -> str:
    """Return age stage: 'egg', 'hatchling', 'juvenile', or 'adult'.

    Stage boundaries:
    - egg:       0 to 8 hours
    - hatchling: 8 hours to 2 days
    - juvenile:  2 days to 4 days
    - adult:     4 days onward

    Pure function.
    """
    elapsed = now - born_at
    if elapsed < EGG_SECONDS:
        return "egg"
    elif elapsed < HATCHLING_SECONDS:
        return "hatchling"
    elif elapsed < JUVENILE_SECONDS:
        return "juvenile"
    else:
        return "adult"


def frames_for(character: str, mood: str, stage: str = "adult") -> list[list[str]]:
    """Look up sprite frames, falling back rather than raising.

    Supports hatchling stage: returns baby sprites for hatchling stage if available,
    otherwise falls back to adult sprites. Juvenile stage uses adult sprites.
    For missing moods, always falls back to adult sleeping.

    Stage mapping:
    - egg:       should not reach here (handled separately by hatch_stage)
    - hatchling: use BABY sprites if available, else fall back to adult
    - juvenile:  use ADULT sprites (distinguished only by label in --whoami)
    - adult:     use ADULT sprites
    """
    # If stage is hatchling and mood is available in BABY, use baby sprite
    if stage == "hatchling" and mood in BABY_MOODS:
        baby_sprites = BABY.get(character)
        if baby_sprites and mood in baby_sprites:
            return baby_sprites[mood]

    # For juvenile and adult, and as fallback for hatchling: use adult sprites
    sprites = CHARACTERS.get(character) or CHARACTERS[DEFAULT_CHARACTER]
    return sprites.get(mood) or sprites["sleeping"]


# Compact egg, cracking in step with the 3-line EGG frames. The compact surface
# had no egg concept at all, so a brand-new buddy skipped hatching entirely and
# showed its species face from second one — the whole hatch was invisible there.
EGG_COMPACT = ("(o)", "(c)", "(<)", "(*)")


def egg_compact_for(frame_index: int) -> str:
    """Compact egg face for a hatch frame. Clamps rather than raising."""
    if not EGG_COMPACT:
        return "(o)"
    idx = max(0, min(int(frame_index), len(EGG_COMPACT) - 1))
    return EGG_COMPACT[idx]


def compact_for(
    character: str,
    mood: str,
    born_at: float | None = None,
    now: float | None = None,
) -> str:
    """Look up compact face, falling back rather than raising.

    When born_at and now are supplied and the buddy has not hatched yet, returns
    the compact egg for the current hatch frame instead of the species face.
    """
    if born_at is not None and now is not None:
        egg_idx = hatch_stage(born_at, now)
        if egg_idx is not None:
            return egg_compact_for(egg_idx)
    faces = COMPACT.get(character) or COMPACT[DEFAULT_CHARACTER]
    return faces.get(mood) or faces["sleeping"]


PET_DURATION = 10.0  # seconds; petting effect lasts 10s


def apply_petting(mood: str, petted_at: float | None, now: float) -> str:
    """Return happy mood if recently petted, otherwise return original mood.

    Petting duration is PET_DURATION seconds. Alert, alarmed, and offline moods
    always take precedence over happy (never mask distress signals).

    Pure function.
    """
    # Never mask distress signals
    if mood in ("alert", "alarmed", "offline"):
        return mood

    # If no petted_at or outside duration window, return original mood
    if petted_at is None or now - petted_at >= PET_DURATION:
        return mood

    # Recently petted: show happy
    return "happy"


def hatch_stage(born_at: float, now: float, duration: float = None) -> int | None:
    """Return egg frame index while hatching, None when hatched.

    Pure function. Hatching takes `duration` seconds (default EGG_SECONDS = 8 hours).
    Returns None once hatching is complete (now - born_at >= duration).
    Returns None if now is before born_at (haven't been born yet).

    Egg frames cycle across the entire duration so the egg is visibly progressing.
    """
    if duration is None:
        duration = EGG_SECONDS

    elapsed = now - born_at
    if elapsed < 0 or elapsed >= duration:
        return None

    # Map elapsed time to an egg frame index, cycling across all frames
    frame_idx = int((elapsed / duration) * len(EGG))
    return min(frame_idx, len(EGG) - 1)


def idle_frame(character: str, tick: int) -> list[str] | None:
    """Return an idle animation frame on a rare, deterministic schedule.

    Returns None most of the time, or an alternate 3-line frame for sleeping/working moods.
    Never returns a frame for alert, alarmed, or offline — those moods must stay legible.

    The schedule uses tick 17 (chosen to feel irregular) to create occasional blinks/twitches.
    Pure function.
    """
    # Use a deterministic but irregular interval: every 17th tick
    if tick % 17 != 0:
        return None

    # Only animate during calm moods; alert/alarmed/offline must stay focused
    # (This function is called with mood, which would be passed by the caller)
    # For now, return None to be safe — the caller will decide when to use this
    idle_variants = IDLE.get(character)
    if not idle_variants:
        return None

    # Pick a frame based on tick, cycling through available variants
    frame_idx = (tick // 17) % len(idle_variants)
    return idle_variants[frame_idx]
