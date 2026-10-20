# FF8 Steam Deck Button Glyphs

Final Fantasy VIII on PC labels buttons as "B1", "B2", ... This mod shows the actual Steam Deck
buttons instead: A, B, X, Y, L1/R1, L2/R2, View and Menu.

<img width="1262" height="942" alt="Screenshot_2026-10-20_17-00-22" src="https://github.com/user-attachments/assets/656a7526-889d-40eb-9c34-5eb908d33175" />


- The icons follow your button setup from the in-game Config menu.
- On keyboard, the game shows key names as usual.

## Requirements

- Final Fantasy VIII, Steam version (2013 or Remastered), English
- [Junction VIII](https://github.com/tsunamods-codes/Junction-VIII)

## Install

1. Download `FF8DeckGlyphs.iroj` from the [latest release](../../releases/latest).
2. In Junction VIII, click **Import mod** and pick the file.
3. Activate **FF8 Steam Deck Button Glyphs** and start the game.

Using AxlRose's mod with its UI? Place this mod above it in the list.

Known limitation: the keypad in Rinoa's briefing for the Timber train mission keeps the
PlayStation layout. With the default buttons it matches the Deck; if you swap face buttons in
the Config menu, the glyphs show up in other corners.

## Building

`tools/release.sh <version>` builds `dist/FF8DeckGlyphs.iroj`. Needs Python 3 with Pillow and the
DejaVu fonts.

## License

GPL-3.0. Steam Deck is a trademark of Valve Corporation. This project is not affiliated with Valve
or Square Enix.
