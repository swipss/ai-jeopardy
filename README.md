# Jeopardy generator for friend nights

AI-generated Jeopardy boards tuned to a specific friend group's interests, with a custom human-written category for inside jokes and an AI verification step that flags hallucinated clues.

Generates 5 categories from friends' interests, using past beloved categories as few-shot style examples

Generates 5 clues per category at escalating difficulty calibrated to "lived experience" not "obscurity"

Verifies each clue with a separate adversarial AI call, flagging suspect or broken clues

Outputs board in JeopardyLabs paste-ready format

# Known limits

The verifier catches structural errors (tautologies, multi-answer responses, fabricated cross-domain facts) reliably, but cannot reliably catch subtle factual errors in real domains because it shares the same knowledge gaps as the generator.
