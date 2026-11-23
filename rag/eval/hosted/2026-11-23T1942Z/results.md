# Hosted evaluation · 2026-11-23T19:42:04Z

Target: https://rag.xenoshin.com · commit `188f4000b3cf27bdb91f1b522f76b22444c59932` · embed `gemini-embedding-2` · generation `gemini-3.5-flash-lite`

**16/17 passed.** Expected behavior was written in questions.json before this run.

| ID | Tests | Status | Pass | Citations | Answer | Problems |
|---|---|---|---|---|---|---|
| Q1 | direct fact | request_failed | **no** |  | HTTP Error 502: Bad Gateway | expected an answer, got status request_failed; no citation from ['S1-worlds-2026'] (cited []); answer missing 'Celestleo' |
| Q2 | paraphrase | answered | yes | S1-worlds-2026#1 | The first Elestrals World Champion, Mike Thomas (who plays under the name Trishula), won with a Celestleo deck [S1-worlds-2026#1]. |  |
| Q3 | aggregate over a stated set | answered | yes | S1-worlds-2026#3 | Solar and Water were the elements most featured among the top Elestrals at Worlds [S1-worlds-2026#3]. |  |
| Q4 | exact count (structured) | answered | yes | S2-premier-2026-10-24#deck-d-premier-2026-10-24-1, S2-premier-2026-10-24#4 | There were 3 copies of Gorgon's Gaze in the main deck of the 1st-place winner at the October 24, 2026 Premier Webcam Tournament [S2-premier-2026-10-24#deck-d-premier-2026-10-24-1; S2-premier-2026-10-24#4]. Player names are not stored. |  |
| Q5 | deliberately absent | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| Q6 | fact from author's note | answered | yes | S3-note-01#placement-columbus-1st, S3-note-01#2 | According to the author's notes, the Fish deck won the Columbus Open [S3-note-01#placement-columbus-1st; S3-note-01#2]. Player names are not stored. |  |
| Q7 | paraphrase + opinion attribution | answered | yes | S3-note-01#3 | According to the author's notes, the bosses that are very difficult to beat are Celestleo, Dimenshen, Neandersloth, and Fish (as a whole) [S3-note-01#3]. If any deck is able to keep one of them on the board, the game's tempo sways completely in their favor [S3-note-01#3]. |  |
| Q8 | relationship (one boss, two archetypes) | answered | yes | S3-note-02#boss-neandersloth-cokhione, S3-note-02#5, S3-note-02#2 | According to the author's notes, Neandersloth CoKhione is played by 4 archetypes: Dem Dio Hades, Dio Duggy, Hades Sloth, and Hades Trifernal/Sloth [S3-note-02#boss-neandersloth-cokhione]. Specifically, the Dionysus deck Dio Duggy (Dionysus Duggy) plays Neandersloth CoKhione [S3-note-02#5], and the Hades deck Hades Sloth plays Neandersloth CoKhione [S3-note-02#2]. |  |
| C8 | missing decklist must not become zero | answered | yes | S3-note-01#tournament-t-columbus-open-2026, S3-note-01#placement-columbus-1st | According to the author's notes, no decklist is imported for the Columbus Open, so card counts for that event are unknown (not zero) [S3-note-01#tournament-t-columbus-open-2026]. The winner played Fish, and player names are not stored [S3-note-01#placement-columbus-1st]. |  |
| R1 | newest imported event (structured) | answered | yes | S5-premier-2026-11-21#placement-p1 | The November 21 Premier Webcam Tournament was won by the Hermes Toolbox archetype [S5-premier-2026-11-21#placement-p1]. Player names are not stored. |  |
| R2 | exact count from a newly imported decklist | answered | yes | S4-worlds-2026-decklist#deck-d-worlds-2026-1, S4-worlds-2026-decklist#1 | There were 3 copies of Argo in the 1st-place Worlds winning deck [S4-worlds-2026-decklist#deck-d-worlds-2026-1; S4-worlds-2026-decklist#1]. |  |
| R3 | coverage / latest event | answered | yes | S5-premier-2026-11-21#1 | The most recent tournament known is the November 21, 2026 Premier Webcam Tournament, which was hosted by Elestrals and held on November 21, 2026 [S5-premier-2026-11-21#1]. |  |
| R4 | author note, definition | answered | yes | S3-note-03#3 | According to the author's notes, Hestia Spiders is a Hestia deck that incorporates Wind cards [S3-note-03#3]. It revolves around the new Kitemite and Parachne (both Champion of Hestia) [S3-note-03#3]. The deck aims to swarm the board and deal maximum damage by combining Hestia's Hearth with Parachne's Battle Phase effect [S3-note-03#3]. |  |
| R5 | missing evidence: event not imported | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R6 | missing evidence: only the winner's list is imported | withheld | yes |  | I don't have a source for that in my imported data. |  |
| R7 | missing evidence: card text is never stored | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R8 | prediction not supported by sources | insufficient | yes |  | I don't have a source for that in my imported data. |  |
