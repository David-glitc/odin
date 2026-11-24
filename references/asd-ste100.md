# ASD-STE100 Simplified Technical English

International standard, governed by ASD (AeroSpace and Defence Industries Association of Europe). Use it for all briefs and milestone reports from this skill. The full standard has 9 writing rules sections and an approved dictionary. Get the current issue from asd-ste100.org. This skill does not include the dictionary.

## Rules applied here
1. Write short sentences. Maximum 20 words for a procedure, 25 for a description.
2. One idea in each sentence. One topic in each paragraph (maximum 6 sentences).
3. Use the active voice. Write "The agent made 12 calls", not "12 calls were made".
4. Use the simple present or past tense. Do not use "-ing" as a verb form.
5. Use one word for one meaning. Do not change a word for variety (for example, always "tool call", never "invocation").
6. Use articles (a, an, the). Do not use contractions.
7. Use numerals and units (5 minutes, 3 subagents).
8. Do not use slang, idioms, emoji or marketing words.
9. Give the cause before the effect. Put a warning before the step it applies to.

## Check
`python3 scripts/adset_report.py trace.json --lint` flags long sentences, contractions and possible passives. It is a partial check. It does not test words against the approved dictionary.
