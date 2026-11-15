# Inkborne: story canon (v2, demo)
Owner: Lisa (Lead Story Writer). This file is the source of truth for names. Art, audio, dialogue, and UI text should use these exactly. Ask Lisa before adding or changing a canon name.

## Working title
**Inkborne** (per SPEC v1.1; Tabula Rasa was briefly used and reverted).

## Hook and world
The world of **Shirofuda** was painted into being by the First Brush, and everything in it, from rivers to people, is ink on living paper. Where the red seals of the old shrines hold, the painting stays true. Now the seals are cracking, and a creeping smear called **the Blot** is soaking through the land, unwriting whatever it touches into blank paper and wandering ink-beasts. A swordsman who can't remember his own name, a shrine archer who refuses to let her village be erased, and a retired temple brawler set out from the border town of Hanshi to find who is breaking the seals. Each of them carries a fragment of the First Brush's red ink, and when their resolve runs high, that ink lets them unfurl into winged elemental forms painted straight from the old legends.

Tone: quiet, melancholy, and warm, with dry humor between the party. Red always means something alive or sacred (seals, blood, lanterns, the transformation ink).

## Party

### Itsuki Hane: wandering swordsman (lead, physical DPS)
- **Personality:** Calm, guarded, dry wit. He has no memory before waking in Sumikage Wood with a blank seal on his palm, and he's quietly afraid he's an unfinished drawing.
- **Look:** Tall and lean, a loose grey kimono with a torn sleeve, and long black hair tied low with a red cord. He carries a brush-handled katana whose blade leaves ink trails. Pale, sharp features, and his left palm is wrapped.
- **Ink:** Gale. **Inkwing:** the *Gale Crane*. Long white-and-grey crane wings with feathered ink edges and a muted pale jade tint.

### Benika Matsuo: shrine archer (healer and support, ranged)
- **Personality:** Bright, stubborn, fiercely protective, and quick to scold and quicker to laugh. She's the keeper of Hanshi's shrine, and she takes the cracking seals personally.
- **Look:** Short and sturdy, in a white shrine top with a vermilion hakama (the cast's main red accent). Her hair is chin length with a paper charm clipped in. She carries a tall bow with prayer slips tied to it.
- **Ink:** Ember. **Inkwing:** the *Ember Kite*. Wide kite-bird wings that smolder at the tips, with a muted ochre and ember tint and drifting ash.

### Gonzō Kuraishi: retired temple monk (tank, heavy hitter)
- **Personality:** Gruff, slow to speak, and endlessly kind under it. He eats too much, he hums off-key, and he once failed to protect a seal and has never forgiven himself.
- **Look:** Huge and broad, bald, with a thick grey beard and prayer beads the size of plums. He wears a patched dark robe and carries an iron-banded staff. A faded red seal is tattooed across his back.
- **Ink:** Stone. **Inkwing:** the *Stone Owl*. Heavy, rounded owl wings like layered slate, with a muted umber and moss tint and cracks that glow faintly red.

## Demo enemies
1. **Blotling:** a small puddle of living ink with one blinking eye. It splits when struck hard, and it's the basic fodder.
2. **Hollow Lantern:** a torn paper lantern drifting on ink smoke whose red flame is going grey. It casts a dimming curse that lowers accuracy.
3. **Smudge Ronin** (demo mini-boss): a samurai whose outline was half-unwritten by the Blot. He fights with a dripping blade and has no face, only a wet brushstroke.

## Places
- **Forest path:** **Sumikage Wood** ("ink-shadow wood"). It has bamboo and old pines, drifting mist, and falling leaves, with broken seal-stones along the path.
- **Town:** **Hanshi** (named for calligraphy paper). It's a small border town of paper-walled houses and red lanterns, with Benika's shrine at the top of the stair. The shop is **Kōbō Tsuru**, a general store run by the old shopkeeper **Grandmother Tsuru**.

### World-map nodes (ids match data/world.json)
| id | Canon name | Flavor |
|---|---|---|
| `woods_edge` | **Hakushi Clearing** | A ring of bare, paper-white grass where Itsuki woke with a blank seal on his palm. Nothing here has been painted yet. (Start node.) |
| `sumikage` | **Sumikage Wood** | The forest path POI. |
| `hanshi` | **Hanshi** | The town POI. |
| `shrine_stair` | **Shuin Stair** | Ninety-nine worn stone steps up to Benika's shrine, each one stamped with a fading red seal. (Locked in the demo.) |
| `grey_shore` | **Usuzumi Shore** | A beach of thin grey ink, where the sea has started forgetting its colour and the waves come in unwritten. (Locked in the demo.) |

Retired placeholder names: Mender's Hut, Mistcedar Path, Hollowbell, The Pale Gate, Where Itsuki Woke, Shrine Stair, The Grey Shore.

## Mechanics names (follow SPEC section 2)
- **Timed-press combo:** **Brushstroke**. Each press is a *Stroke*, and each character's named chains are also called *Strokes*: Itsuki's *Falling Pine*, Benika's *Three Prayer Slips*, and Gonzō's *Temple Bell*.
- **Perfect press:** **Clean Line**.
- **Transformation gauge:** **Vermilion Ink** (confirmed by Marc). It fills with red ink as the character lands Strokes and takes hits.
- **Transformation:** **Inkwing**. The act and battle command verb is **Unfurl** (for example, "Itsuki Unfurls! Gale Crane Inkwing.").
- **Timed magic while transformed:** **Seal Arts**.
- **Guard:** **Still Water**.
- **Elements:** the **Six Inks** are Ember, Tide, Gale, Stone, Dawn, and Dusk. Itsuki is **Gale**, Benika is **Ember**, and Gonzō is **Stone**.
- **Currency:** **mon**.

## Strokes and Seal Arts (approved; ids match Systems data)
| Character | First Stroke | Second Stroke | Seal Art (while Unfurled) |
|---|---|---|---|
| Itsuki | Falling Pine (`falling_pine`) | Wet Edge (`wet_edge`) | **Gale Crane Script** (`crane_gale_script`) |
| Benika | Three Prayer Slips (`three_prayer_slips`) | Lantern Volley (`lantern_volley`) | Ember Kite Litany (`ember_kite_litany`) |
| Gonzō | Temple Bell (`temple_bell`) | Mountain Gong (`mountain_gong`) | Stone Owl Verse (`stone_owl_verse`) |

Jake's names are approved as proposed, with one change. The display name "Crane Gale Script" becomes **Gale Crane Script** so it matches the Inkwing name, and the id stays `crane_gale_script`.

## Minor NPCs
- **Old Hotaru** (`lantern_keeper`): Hanshi's lamplighter, a stooped, soft-spoken old man who relights the red lanterns every dusk and talks to each flame like a grandchild. He's the first to notice that the flames are greying.

## Story beats to avoid (IP review)
- Never write a burned or destroyed hometown as a story beat, for any character, in backstory or on screen.
- Never write a captured or kidnapped childhood friend as a story beat.
- Itsuki is a katana swordsman, never a spear user.

## Naming rules for the team
- Never use any Legend of Dragoon names or terms, and never the word "Dragoon". Also avoid "Addition", "Spirit", and "Wingly" as mechanic or race terms.
- Japanese-flavored names should be simple and pronounceable. Mechanics use plain English ink and brush words.
- Ollie owns dialogue and shop text. Jamie owns the glossary and UI strings. Both pull names from this file.

## IDs (match Systems data)
Party: `itsuki`, `benika`, `gonzo`. Enemies: `blotling`, `hollow_lantern`, `smudge_ronin`. Shop: `kobo_tsuru`, with keeper `tsuru`. World nodes: `woods_edge`, `sumikage`, `hanshi`, `shrine_stair`, `grey_shore`. POIs: `forest` (Sumikage Wood) and `town` (Hanshi).
