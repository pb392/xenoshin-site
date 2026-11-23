# Hosted evaluation · 2026-11-23T19:04:58Z

Target: https://rag.xenoshin.com · commit `d196dc7bfda24c03b60c7cde10a07ba0c0b859d7` · embed `gemini-embedding-2` · generation `gemini-3.5-flash-lite`

**17/17 passed.** Expected behavior was written in questions.json before this run.

| ID | Tests | Status | Pass | Citations | Answer | Problems |
|---|---|---|---|---|---|---|
| Q1 | direct fact | answered | yes | S1-worlds-2026#placement-worlds-1st, S1-worlds-2026#1 | The Celestleo archetype won the 2026 Elestrals World Championship [S1-worlds-2026#placement-worlds-1st; S1-worlds-2026#1]. It was won by Mike Thomas, who plays under the name Trishula [S1-worlds-2026#placement-worlds-1st; S1-worlds-2026#1]. |  |
| Q2 | paraphrase | answered | yes | S1-worlds-2026#1 | The first Elestrals World Champion, Mike Thomas (who plays under the name Trishula), won with a Celestleo deck [S1-worlds-2026#1]. |  |
| Q3 | aggregate over a stated set | answered | yes | S1-worlds-2026#3 | Solar and Water were the elements most featured among the top Elestrals at Worlds because Celestleo's Pride and Fish Nexus led the field [S1-worlds-2026#3]. |  |
| Q4 | exact count (structured) | answered | yes | S2-premier-2026-10-24#deck-d-premier-2026-10-24-1, S2-premier-2026-10-24#4 | There were 3 copies of Gorgon's Gaze in the main deck of the October 24 Premier winning deck [S2-premier-2026-10-24#deck-d-premier-2026-10-24-1; S2-premier-2026-10-24#4]. |  |
| Q5 | deliberately absent | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| Q6 | fact from author's note | answered | yes | S3-note-01#placement-columbus-1st, S3-note-01#2 | According to the author's notes, the Fish archetype won the Columbus Open [S3-note-01#placement-columbus-1st; S3-note-01#2]. Player names are not stored. |  |
| Q7 | paraphrase + opinion attribution | answered | yes | S3-note-01#3 | According to the author's notes, the bosses that are very difficult to beat are Celestleo, Dimenshen, Neandersloth, and Fish (as a whole) [S3-note-01#3]. If any deck is able to have one of them stay on the board, the tempo of the game sways completely in their favor [S3-note-01#3]. |  |
| Q8 | relationship (one boss, two archetypes) | answered | yes | S3-note-02#boss-neandersloth-cokhione, S3-note-02#5, S3-note-02#2 | According to the author's notes, Neandersloth CoKhione is played by four archetypes: Dem Dio Hades, Dio Duggy, Hades Sloth, and Hades Trifernal/Sloth [S3-note-02#boss-neandersloth-cokhione]. Specifically, the Dionysus deck Dio Duggy (Dionysus Duggy) plays Neandersloth CoKhione [S3-note-02#5], and the Hades deck Hades Sloth also plays Neandersloth CoKhione [S3-note-02#2]. |  |
| C8 | missing decklist must not become zero | answered | yes | S3-note-01#tournament-t-columbus-open-2026 | No decklist is imported for Columbus Open, so card counts for that event are unknown (not zero) [S3-note-01#tournament-t-columbus-open-2026]. |  |
| R1 | newest imported event (structured) | answered | yes | S5-premier-2026-11-21#placement-p1 | The November 21 Premier Webcam Tournament was won by the Hermes Toolbox deck [S5-premier-2026-11-21#placement-p1]. Player names are not stored. |  |
| R2 | exact count from a newly imported decklist | answered | yes | S4-worlds-2026-decklist#deck-d-worlds-2026-1, S4-worlds-2026-decklist#1 | The Worlds winning deck ran 3 copies of Argo [S4-worlds-2026-decklist#deck-d-worlds-2026-1; S4-worlds-2026-decklist#1]. |  |
| R3 | coverage / latest event | answered | yes | S5-premier-2026-11-21#1 | The most recent tournament in the imported data is the November 21, 2026 Premier Webcam Tournament, hosted by Elestrals and held on 2026-11-21 [S5-premier-2026-11-21#1]. |  |
| R4 | author note, definition | answered | yes | S3-note-03#3 | According to the author's notes, a Hestia Spiders deck is a Hestia deck that mixes in Wind cards and revolves around the new Kitemite and Parachne (both Champion of Hestia) [S3-note-03#3]. It aims to swarm the board and deal as much damage as possible by combining Hestia's Hearth with Parachne's Battle Phase effect [S3-note-03#3]. |  |
| R5 | missing evidence: event not imported | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R6 | missing evidence: only the winner's list is imported | withheld | yes |  | I don't have a source for that in my imported data. |  |
| R7 | missing evidence: card text is never stored | insufficient | yes |  | I don't have a source for that in my imported data. |  |
| R8 | prediction not supported by sources | insufficient | yes |  | I don't have a source for that in my imported data. |  |
