# Hosted evaluation · 2026-11-23T17:36:43Z

Target: https://rag.xenoshin.com · commit `d6ae784aff46057b85d34272a18ab6106c40d8fa` · embed `gemini-embedding-2` · generation `gemini-3.5-flash-lite`

**16/17 passed.** Expected behavior was written in questions.json before this run.

| ID | Tests | Status | Pass | Citations | Answer | Problems |
|---|---|---|---|---|---|---|
| Q1 | direct fact | answered | yes | S1-worlds-2026#placement-worlds-1st, S1-worlds-2026#1 | The 2026 Elestrals World Championship was won by the Celestleo archetype [S1-worlds-2026#placement-worlds-1st; S1-worlds-2026#1]. Mike Thomas (Trishula) won the event using a Celestleo decklist [S1-worlds-2026#placement-worlds-1st; S1-worlds-2026#1]. |  |
| Q2 | paraphrase | answered | yes | S1-worlds-2026#1 | The first Elestrals World Champion, Mike Thomas (Trishula), won with a Celestleo deck [S1-worlds-2026#1]. |  |
| Q3 | aggregate over a stated set | answered | yes | S1-worlds-2026#3 | Solar and Water were the elements most featured among the top Elestrals at Worlds, because Celestleo's Pride and Fish Nexus led the field [S1-worlds-2026#3]. |  |
| Q4 | exact count (structured) | answered | yes | S2-premier-2026-10-24#deck-d-premier-2026-10-24-1, S2-premier-2026-10-24#4 | There were 3 copies of Gorgon's Gaze in the main deck of the October 24 Premier winning deck [S2-premier-2026-10-24#deck-d-premier-2026-10-24-1; S2-premier-2026-10-24#4]. |  |
| Q5 | deliberately absent | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| Q6 | fact from author's note | answered | yes | S3-note-01#placement-columbus-1st, S3-note-01#2 | According to the author's notes, the Fish deck won the Columbus Open [S3-note-01#placement-columbus-1st; S3-note-01#2]. |  |
| Q7 | paraphrase + opinion attribution | answered | yes | S3-note-01#3 | According to the author's notes, the bosses that are all very difficult to beat are Celestleo, Dimenshen, Neandersloth, and Fish (as a whole) [S3-note-01#3]. If any deck manages to keep one of them on the board, the game's tempo sways completely in their favor [S3-note-01#3]. |  |
| Q8 | relationship (one boss, two archetypes) | answered | yes | S3-note-02#boss-neandersloth-cokhione, S3-note-02#5, S3-note-02#2 | According to the author's notes, Neandersloth CoKhione is played by four archetypes: Dem Dio Hades, Dio Duggy, Hades Sloth, and Hades Trifernal/Sloth [S3-note-02#boss-neandersloth-cokhione]. Specifically, the Dio Duggy (Dionysus Duggy) archetype plays Neandersloth CoKhione, and the Hades Sloth archetype also plays Neandersloth CoKhione [S3-note-02#5; S3-note-02#2]. |  |
| C8 | missing decklist must not become zero | answered | yes | S3-note-01#tournament-t-columbus-open-2026 | According to the author's notes, no decklist is imported for the Columbus Open, so card counts for that event are unknown (not zero) [S3-note-01#tournament-t-columbus-open-2026]. |  |
| R1 | newest imported event (structured) | insufficient | **no** |  | I don't have a source for that in my imported data. | expected an answer, got status insufficient; no citation from ['S5-premier-2026-11-21'] (cited []); answer missing 'Hermes Toolbox' |
| R2 | exact count from a newly imported decklist | answered | yes | S4-worlds-2026-decklist#deck-d-worlds-2026-1, S4-worlds-2026-decklist#1 | There were 3 copies of Argo in the 1st-place deck at the 2026 Elestrals World Championship [S4-worlds-2026-decklist#deck-d-worlds-2026-1; S4-worlds-2026-decklist#1]. |  |
| R3 | coverage / latest event | answered | yes | S5-premier-2026-11-21#1 | The most recent tournament is the November 21, 2026 Premier Webcam Tournament hosted by Elestrals, which was held on November 21, 2026 [S5-premier-2026-11-21#1]. |  |
| R4 | author note, definition | answered | yes | S3-note-03#3 | According to the author's notes, a Hestia Spiders deck is a Hestia deck that incorporates Wind cards and is built around the Hestia spider Elestrals Kitemite and Parachne, which are both Champions of Hestia [S3-note-03#3]. |  |
| R5 | missing evidence: event not imported | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R6 | missing evidence: only the winner's list is imported | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R7 | missing evidence: card text is never stored | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R8 | prediction not supported by sources | insufficient | yes |  | I don't have a source for that in my imported data. |  |
