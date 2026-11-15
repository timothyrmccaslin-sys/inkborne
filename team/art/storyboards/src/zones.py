# Single source of truth for UI zones (logical 1280x720, SPEC v1.1 s1). Used by boards AND LAYOUT_NOTES.md.
# Every rect is (code, name, x, y, w, h, note). Reserved touch rects (SPEC s4) are drawn on EVERY board;
# no other UI may overlap them.
SAFE=(64,36)  # 5% title-safe each side, applied on top of env(safe-area-inset-*)
RESERVED=[("T1","touch stick",64,496,192,188,"virtual stick, lower left. PROPOSED rect: SPEC s4 names the corner only. Reserved on every screen."),
          ("T2","touch A / B",1024,496,192,188,"A = confirm / timed press, B = cancel / Still Water. PROPOSED rect (SPEC s4: lower right). Reserved on every screen."),
          ("M","menu ☰",1152,36,64,64,"☰ menu button, top right. PROPOSED rect (SPEC s4: top right). Reserved on every screen.")]
Z={
"world":[("W1","location plate",64,36,400,64,"node name; red seal dot when the node opens a POI"),
         ("W2","node prompt",400,600,480,84,"'Enter Sumikage Wood  [A]'; shows while the token rests on a node"),
         ("W3","party token",0,0,48,64,"floats 24px above node centre; follows path bezier ~260 px/s")],
"poi":[("P1","area toast",64,36,400,56,"area name: fade in 0.4s, hold 2.5s, fade 0.6s"),
       ("P2","interact prompt",0,0,220,44,"centred on target x, bottom edge 96px above target feet; clamp outside T1/T2/M"),
       ("P3","exit marker",0,0,64,64,"ink chevron at the screen edge when an exit is on screen; clamp outside T1/T2")],
"dialogue":[("D1","portrait L",64,108,300,376,"512x640 art at ~0.59; bottom edge y=484 stays above T1"),
            ("D2","portrait R",916,108,300,376,"mirror of D1; bottom y=484 stays above T2"),
            ("D3","text box",272,500,736,184,"between T1 and T2. 3 lines max, 24px serif, ~44 chars/line, 28px padding"),
            ("D4","name plate L",288,472,220,40,"overlaps D3 top edge; red seal tick on the active speaker"),
            ("D5","name plate R",772,472,220,40,"mirror of D4"),
            ("D6","advance mark",972,648,24,24,"red brush tick inside D3, bobs 4px at 1.2Hz when the line is fully typed"),
            ("D7","choices",424,248,432,200,"2-3 rows x 56px, 16px gap, between portraits; focus = red underline"),
            ("D8","log / auto",944,36,192,44,"text log + auto toggle, left of M")],
"shop":[("S1","Buy / Sell tabs",64,36,320,56,"active tab = red brush underline"),
        ("S2","shop title",400,36,400,56,"'Kōbō Tsuru'"),
        ("S3","mon counter",936,36,200,56,"coin icon + amount; counts down 20/s on purchase"),
        ("S4","keeper portrait",64,112,248,310,"Grandmother Tsuru, 512x640 at ~0.48"),
        ("S5","keeper name",64,430,248,40,"name plate under portrait"),
        ("S6","item list",336,112,448,500,"header 20 + 8 rows x 60: icon 48, name, owned, price right"),
        ("S7","description",808,112,408,224,"128px icon, name, 2-3 line desc"),
        ("S8","party compare",808,352,408,136,"3 rows x 40: chip, name, now -> after (HP / Ink)"),
        ("S9","keeper line",272,628,736,56,"one-line barks (Ollie); doubles as qty stepper on confirm")],
"battle":[("B1","turn order",64,36,520,48,"chips left->right; current actor ringed red"),
          ("B2","target plate",600,36,400,48,"enemy name + HP stroke while targeting"),
          ("B3","banner",340,104,600,56,"action names, 'Clean Line', 'Itsuki Unfurls!'; ink wipe in 180ms"),
          ("B4","party HUD",272,588,736,96,"3 cards 240x96, gap 8: chip 56, name, HP stroke, Vermilion Ink stroke"),
          ("B5","command menu",64,232,232,248,"title row + 5 rows x 44: Brushstroke, Unfurl, Still Water, Items, Flee"),
          ("B6","press ring",904,234,192,192,"floats on the target hit point (shown on Smudge Ronin)"),
          ("B7","stroke pips",904,436,192,36,"one pip per Stroke; red = Clean Line, grey = good, cracked = miss"),
          ("B8","seal stamp",544,232,192,192,"perfect-chain finisher, near centre"),
          ("B9","results panel",340,176,600,300,"victory: mon, ink kept, drops; party lines up below it")],
}
STAGE={"benika":(340,430),"itsuki":(470,495),"gonzo":(615,565),"lantern":(860,300),"ronin":(1010,440),"blotling":(1150,455)}
WORLD_NODES={"start":(230,470),"forest":(560,360),"town":(930,450),"locked":(1110,210)}  # positions from data/world.json
