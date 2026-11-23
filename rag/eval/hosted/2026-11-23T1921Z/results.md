# Hosted evaluation · 2026-11-23T19:21:04Z

Target: https://rag.xenoshin.com · commit `ead96cff3101cb248f7a6bfc72b78e17cf9a781f` · embed `gemini-embedding-2` · generation `gemini-3.5-flash-lite`

**16/17 passed.** Expected behavior was written in questions.json before this run.

| ID | Tests | Status | Pass | Citations | Answer | Problems |
|---|---|---|---|---|---|---|
| Q1 | direct fact | answered | yes | S1-worlds-2026#placement-worlds-1st, S1-worlds-2026#1 | The 2026 Elestrals World Championship was won by the Celestleo archetype [S1-worlds-2026#placement-worlds-1st; S1-worlds-2026#1]. |  |
| Q2 | paraphrase | answered | yes | S1-worlds-2026#1 | The first Elestrals World Champion, Mike Thomas (who plays under the name Trishula), won with a Celestleo deck [S1-worlds-2026#1]. |  |
| Q3 | aggregate over a stated set | answered | yes | S1-worlds-2026#3 | Solar and Water were the elements most featured among the top Elestrals at Worlds, because Celestleo's Pride and Fish Nexus led the field [S1-worlds-2026#3]. |  |
| Q4 | exact count (structured) | request_failed | **no** |  | HTTP Error 500: Internal Server Error | expected an answer, got status request_failed; no citation from ['S2-premier-2026-10-24'] (cited []); answer missing '3' |
| Q5 | deliberately absent | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| Q6 | fact from author's note | answered | yes | S3-note-01#placement-columbus-1st, S3-note-01#2 | According to the author's notes, the deck that won the Columbus Open was Fish [S3-note-01#placement-columbus-1st; S3-note-01#2]. Player names are not stored. |  |
| Q7 | paraphrase + opinion attribution | answered | yes | S3-note-01#3 | According to the author's notes, the bosses that are very difficult to beat are Celestleo, Dimenshen, Neandersloth, and Fish (as a whole) [S3-note-01#3]. If any deck manages to keep one of these bosses on the board, the game's tempo shifts completely in their favor [S3-note-01#3]. |  |
| Q8 | relationship (one boss, two archetypes) | answered | yes | S3-note-02#boss-neandersloth-cokhione, S3-note-02#5, S3-note-02#2 | According to the author's notes, Neandersloth CoKhione is played by 4 archetypes: Dem Dio Hades, Dio Duggy, Hades Sloth, and Hades Trifernal/Sloth [S3-note-02#boss-neandersloth-cokhione]. Specifically, the Dionysus deck Dio Duggy (Dionysus Duggy) plays it [S3-note-02#5], and the Hades deck Hades Sloth also plays Neandersloth CoKhione [S3-note-02#2]. |  |
| C8 | missing decklist must not become zero | answered | yes | S3-note-01#tournament-t-columbus-open-2026 | No decklist is imported for Columbus Open, so card counts for that event are unknown (not zero) [S3-note-01#tournament-t-columbus-open-2026]. |  |
| R1 | newest imported event (structured) | answered | yes | S5-premier-2026-11-21#placement-p1 | The November 21 Premier Webcam Tournament was won by the Hermes Toolbox deck [S5-premier-2026-11-21#placement-p1]. Player names are not stored. |  |
| R2 | exact count from a newly imported decklist | answered | yes | S4-worlds-2026-decklist#deck-d-worlds-2026-1, S4-worlds-2026-decklist#1 | The Worlds winning deck ran 3 copies of Argo [S4-worlds-2026-decklist#deck-d-worlds-2026-1; S4-worlds-2026-decklist#1]. |  |
| R3 | coverage / latest event | answered | yes | S5-premier-2026-11-21#1 | The most recent tournament is the November 21, 2026 Premier Webcam Tournament, hosted by Elestrals on 2026-11-21 [S5-premier-2026-11-21#1]. |  |
| R4 | author note, definition | answered | yes | S3-note-03#3 | According to the author's notes, Hestia Spiders is a Hestia deck that incorporates Wind cards [S3-note-03#3]. It revolves around the new Kitemite and Parachne (both Champion of Hestia) [S3-note-03#3]. The deck aims to swarm the board and deal maximum damage by combining Hestia's Hearth with Parachne's Battle Phase effect [S3-note-03#3]. |  |
| R5 | missing evidence: event not imported | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R6 | missing evidence: only the winner's list is imported | answered | yes | S3-note-03#2, S5-premier-2026-11-21#2, S5-premier-2026-11-21#3 | Based on the imported data, the exact number of Hestia copies in the 2nd place deck at the November 21 Premier is unknown. Player names are not stored. However, according to the author's notes, the 2nd place archetype is likely Hephestia (combining Hephaestus and Hestia cores), and featured cards in the 2nd deck included Warmite - Champion of Hestia and Hestia's Hearth [S3-note-03#2; S5-premier-2026-11-21#2; S5-premier-2026-11-21#3]. |  |
| R7 | missing evidence: card text is never stored | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R8 | prediction not supported by sources | insufficient | yes |  | I don't have a source for that in my imported data. |  |
