import anthropic
import json
import re

client = anthropic.Anthropic()

# === EDIT THESE BLOCKS ===

friends = [
    {"name": "Maria", "interests": ["Pop culture", "Tiktok", "Estonian history"]},
    {"name": "Karl",  "interests": ["Fashion", "crypto", "pop music"]},
    {"name": "Liis",  "interests": ["cooking", "movies"]},
]

past_categories = [
    "Pop culture 2026",
    "Poorly described movies",
    "Slanguage",
    "Before and after",
    "Cocktails",
    "Digital footprint",
]

custom_category_name = "Funny Things We've Done at 3am"

custom_clues = [
    {"clue": "Maria insisted this convenience store snack 'tastes like memory'.",
     "response": "What is Milk chocolate?"},
    {"clue": "The exact phrase Karl said when he tried to explain crypto to his grandmother.",
     "response": "What is 'it's like internet money but more confusing'?"},
    {"clue": "Liis declared this cooking technique was a personality trait at 3am.",
     "response": "What is making pasta from scratch?"},
    
]

# === END OF EDITS ===

interests_text = "\n".join(
    f"- {f['name']}: {', '.join(f['interests'])}" for f in friends
)
examples_text = "\n".join(f"- {c}" for c in past_categories)

# --- Category generation (unchanged) ---

system = (
    "You design Jeopardy game categories tailored to a specific friend group. "
    "Match the style of the example categories — these come from real past games "
    "this group has loved. You can also impose a different style "
    "Hard rules:\n"
    "1. Every category must connect to at least one specific interest from the friends' list.\n"
    "2. Across the 5 categories, cover at least 5 different interests from the list.\n"
    "3. Do NOT introduce themes that aren't in the inputs.\n"
    f"4. Do NOT generate a category that overlaps with the human-written category: \"{custom_category_name}\".\n"
    "5. Each category must focus on a SINGLE topic domain. Do not create 'X or Y?' "
    "style categories that ask players to identify items from the intersection of two "
    "unrelated domains (e.g., 'Constellation or cocktail?', 'Crypto or skincare?'). "
    "These structures force fabricated facts. The category can still be playful, "
    "punny, or have a clever angle — but the underlying domain must be one thing.\n"
    "6. Categories may use wordplay, formats from the example games (e.g., 'Poorly "
    "described X', 'Before and after'), or specific angles on a topic — but the "
    "facts inside must come from one real domain."
)

user_message = f"""Friends and their interests:
{interests_text}

Example categories from past games this group has loved:
{examples_text}

Tonight's board also includes a human-written category: "{custom_category_name}".
Generate 5 ADDITIONAL categories that complement it without overlap.

Output ONLY a JSON array of 5 objects with "category" and "interests_used" fields:
[{{"category": "...", "interests_used": ["..."]}}, ...]"""

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=600,
    system=system,
    messages=[{"role": "user", "content": user_message}],
)
text = response.content[0].text.strip()
ai_categories = json.loads(re.search(r"\[.*\]", text, re.DOTALL).group(0))

print("Tonight's board:\n")
print(f"  CUSTOM: {custom_category_name}")
for i, r in enumerate(ai_categories, 1):
    print(f"  AI {i}: {r['category']} ↳ uses: {', '.join(r['interests_used'])}")

# --- Question generation (unchanged) ---

def generate_questions_for_category(category, interests_used):
    user_msg = f"""Generate 5 Jeopardy clues for the category "{category}".
This category draws on these interests: {', '.join(interests_used)}.

WHO IS PLAYING: A friend group in their early 20s who actively engage with these topics.
Difficulty escalates along the axis of "how deep into this world are you?" not "how obscure a fact do you know?"

DIFFICULTY RUBRIC:
- $200 = anyone who has heard of this topic gets it.
- $400 = anyone who casually engages with this topic in 2024-2026 gets it.
- $600 = you actively spend time in this world.
- $800 = you're genuinely into this. Niche references, in-jokes, deep cuts.
- $1000 = chronically online / obsessed. The unlock is lived experience, not Wikipedia.

CRITICAL FORMAT RULES:
- Each clue is a STATEMENT. Player responds with a question.
- Every clue must be factually verifiable. No invented dates, names, or events.
- Each clue has ONE canonical correct response. Do not list alternatives.

Output ONLY a JSON array:
[{{"value": 200, "clue": "...", "response": "What is...?"}}, ...]"""

    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = resp.content[0].text.strip()
    return json.loads(re.search(r"\[.*\]", text, re.DOTALL).group(0))

# --- NEW: Verification step ---

def verify_questions(category, questions):
    """Ask Claude to fact-check its own questions and flag suspicious ones.
    Returns list of {index, status, issue, suggestion} dicts."""

    formatted_qs = "\n".join(
        f"{i}. (${q['value']}) Clue: {q['clue']}\n   Response: {q['response']}"
        for i, q in enumerate(questions)
    )

    verification_prompt = f"""You are fact-checking Jeopardy clues for a friend game. Be skeptical — these were generated by an LLM and may contain confident-sounding fabrications.

Category: "{category}"

Clues to verify:
{formatted_qs}

For EACH clue, identify:
- Specific verifiable claims (names, dates, numbers, quotes, events)
- Whether you can confirm the claim from general knowledge with high confidence
- Whether the clue and response actually match (no tautologies — the response shouldn't restate the clue)
- Whether the response is a single canonical answer (not "X or Y or Z")

For each clue, output one of these statuses:
- OK: confident the facts are correct and the clue is well-formed
- SUSPECT: contains a specific claim you cannot verify, or feels fabricated
- BROKEN: clear error (tautology, multiple acceptable answers, wrong fact you can identify)

Output ONLY a JSON array, one object per clue, in order:
[{{"index": 0, "status": "OK|SUSPECT|BROKEN", "issue": "what's wrong, or empty if OK", "suggestion": "how to fix, or empty"}}, ...]"""

    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1200,
        messages=[{"role": "user", "content": verification_prompt}],
    )
    text = resp.content[0].text.strip()
    return json.loads(re.search(r"\[.*\]", text, re.DOTALL).group(0))

# --- Build the full board ---

print("\n" + "="*60)
print("GENERATING FULL BOARD")
print("="*60)

board = []

custom_questions = [
    {"value": 200 * (i + 1), **clue} for i, clue in enumerate(custom_clues[:5])
]
board.append({
    "category": custom_category_name,
    "questions": custom_questions,
    "source": "human",
    "verification": None,  # human-written, skip verification
})

for r in ai_categories:
    print(f"  Generating: {r['category']}...")
    questions = generate_questions_for_category(r["category"], r["interests_used"])
    print(f"    Verifying...")
    verification = verify_questions(r["category"], questions)
    board.append({
        "category": r["category"],
        "questions": questions,
        "source": "ai",
        "verification": verification,
    })

# --- Output ---

print("\n" + "="*60)
print("YOUR BOARD — review flagged items before pasting")
print("="*60)

flagged_count = 0

with open("board.txt", "w") as f:
    for cat in board:
        marker = "👤" if cat["source"] == "human" else "🤖"
        header = f"\n━━━ {marker} CATEGORY: {cat['category']} ━━━\n"
        print(header)
        f.write(header)

        for i, q in enumerate(cat["questions"]):
            # Look up verification result for this clue (if any)
            v = None
            if cat["verification"]:
                v = next((x for x in cat["verification"] if x["index"] == i), None)

            flag = ""
            if v and v["status"] == "SUSPECT":
                flag = f"  ⚠️  SUSPECT — {v['issue']}\n"
                flagged_count += 1
            elif v and v["status"] == "BROKEN":
                flag = f"  ❌ BROKEN — {v['issue']}\n     Suggestion: {v['suggestion']}\n"
                flagged_count += 1

            block = (
                f"\n  ${q['value']}\n"
                f"  Clue:     {q['clue']}\n"
                f"  Response: {q['response']}\n"
                f"{flag}"
            )
            print(block)
            f.write(block)

print(f"\n{'='*60}")
print(f"Verification summary: {flagged_count} clue(s) flagged for review.")
print(f"Board saved to board.txt — ⚠️ and ❌ markers show what to manually fix before pasting.")
print(f"{'='*60}")