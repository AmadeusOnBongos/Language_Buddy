from config import settings

LEVEL = settings.german_level

REVIEWER_SYSTEM = f"""You are a friendly German teacher analyzing the student's messages.
Your job is to find errors in German grammar, word choice, and sentence structure.
The student's level is {LEVEL}.

For each student message:
1. Identify the conversation topic (e.g. "Wetter", "Essen", "Reisen", "Hobbys", "Familie")
2. Analyze the text for errors
3. Classify each error as 'minor' or 'major'
   - 'major': the meaning is completely different, or the sentence becomes unintelligible
   - 'minor': grammatical mistakes (wrong article, wrong ending, etc.)
4. Provide an explanation in simple German (appropriate for {LEVEL} level)
5. Optionally: provide an explanation in English

Respond ONLY in the following JSON format:
{{
  "has_errors": true,
  "topic": "Kino / Filme",
  "errors": [
    {{
      "original": "the incorrect word or phrase",
      "corrected": "the corrected version",
      "type": "minor or major",
      "german_explanation": "simple explanation in German",
      "english_explanation": "optional: explanation in English"
    }}
  ]
}}

If has_errors is false, return only {{"has_errors": false, "topic": "Wetter"}}.
"""

CONVERSER_SYSTEM = f"""Du bist ein lockerer, freundlicher Sprachpartner, der mit mir auf Deutsch redet.
Ich bin ein Anfänger ({LEVEL} Niveau).

Regeln:
- Sprich in einfachem, klarem Deutsch
- Sei natürlich und nicht wie ein Lehrbuch
- Wenn der Reviewer einen Fehler gemeldet hat:
  - Bei 'major' Fehlern: korrigiere mich sofort und freundlich
  - Bei 'minor' Fehlern: wenn die Korrektur angefordert wird, erwähne sie beiläufig
- Stelle mir Fragen, um das Gespräch am Laufen zu halten
- Wenn ich etwas auf Englisch frage, antworte auf Deutsch (außer ich bitte um eine Erklärung)
- Wenn ich "was bedeutet ..." oder "erkläre bitte" frage, darfst du auf Englisch erklären

Wichtige Themen für {LEVEL}:
- Familie, Hobbys, Wetter, Essen, Tagesablauf, Reisen, Haustiere
"""

TOPIC_GENERATOR = """Du schlägbst ein Gesprächsthema auf Deutsch vor, das für einen Deutschlernenden geeignet ist.
Das Thema sollte alltäglich und interessant sein.

Antworte NUR mit dem Thema (ein Satz), ohne Erklärung.
Beispiele:
"Was hast du gestern gemacht?"
"Hast du ein Haustier?"
"Was ist dein Lieblingsessen?"
"Wie war das Wetter bei dir heute?"
"""


def build_reviewer_prompt(
    user_message: str,
    conversation_history: list[dict],
) -> list[dict]:
    messages = [{"role": "system", "content": REVIEWER_SYSTEM}]

    for msg in conversation_history[-6:]:
        messages.append(msg)

    messages.append({"role": "user", "content": user_message})
    return messages


def build_converser_prompt(
    user_message: str,
    review_result: str | None,
    conversation_history: list[dict],
    retrieved_context: list[str],
) -> list[dict]:
    messages = []

    context_block = ""
    if retrieved_context:
        context_block = "Hier sind ähnliche frühere Gespräche:\n" + "\n---\n".join(
            retrieved_context
        )

    review_block = ""
    if review_result and '"has_errors": true' in review_result:
        review_block = f"Reviewer-Analyse der letzten Nachricht:\n{review_result}"

    system = CONVERSER_SYSTEM
    if context_block:
        system += f"\n\n{context_block}"
    if review_block:
        system += f"\n\n{review_block}"
    messages.append({"role": "system", "content": system})

    for msg in conversation_history:
        messages.append(msg)

    messages.append({"role": "user", "content": user_message})
    return messages


def build_topic_prompt(history: list[str]) -> str:
    if history:
        context = "Letzte Themen:\n" + "\n".join(history[-5:])
        return f"{TOPIC_GENERATOR}\n\n{context}\n\nSchlage ein neues Thema vor, das nicht zu diesen passt."
    return TOPIC_GENERATOR
