# Luc: items & props (Tabula Rasa)
Spec: SPEC.md section 5. WebP lossless with alpha, sRGB. `@4x.png` = 512px masters.

## Shop icons (128x128, ids from team/story/items.json)
icons/icon-rice_cake, icon-plum_tonic, icon-pine_tea, icon-festival_bento,
icon-inkstone_chip, icon-fresh_ink_pot, icon-paper_cracker, icon-thunder_jar (.webp)
Preview: contact_icons.png

## Props
props/prop-kobo-tsuru-mark.webp (512x512, vermilion crane-in-circle crest for the Kobo Tsuru noren)
props/prop-kobo-tsuru-mark-ink.webp (black ink variant). Interior is transparent so the curtain cloth shows through; composite onto the noren.
Preview: contact_mark.png (on dark backing)

## Other
manifest-items.json: entries in assets/art/manifest.json format to merge (src paths relative to this folder; adjust to assets/art/<group>/ on integration).
extra-icons/: earlier non-canon icons (not in the shop list), spare.
src/: raw generations.

## Signature weapons (weapons/)
wpn-itsuki-katana.webp (1024x120), brush-handled katana
wpn-benika-bow.webp (199x1024), tall bow with prayer slips (gap between string and limb is transparent)
wpn-gonzo-staff.webp (1024x92), iron-banded staff
wpn-gonzo-prayer-beads.webp (873x1024), prayer-bead mala
icon-wpn-*.webp at 128x128 (diagonal for long weapons), plus @4x.png masters.
Preview: contact-weapons.png

## App icons
assets/icons/ overwritten; masters and preview in app-icon/.

## Town and forest props (props/), 512x512, anchor at the feet [0.5,1] (lantern-string hangs from the top, [0.5,0])
Hanshi: prop-lantern-paper, prop-lantern-stone, prop-signpost, prop-barrel, prop-shop-kobo-tsuru (shop front with a blank noren; composite prop-kobo-tsuru-mark onto it), prop-shrine (small shrine with a red gate), prop-shrine-stair, prop-lantern-string
Sumikage Wood: prop-seal-stone-tall, prop-seal-stones-cluster, prop-bamboo-tall, prop-bamboo-young
Preview: contact-props.png
