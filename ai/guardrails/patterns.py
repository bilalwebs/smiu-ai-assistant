"""Maintainable guardrail rule/pattern lists (AI_ARCHITECTURE.md §26.1-26.2).

Purpose:
    A small rule/pattern abstraction instead of one hardcoded phrase list
    (§26.2): each rule names a category, a stable machine code, a compiled
    word-boundary regex, and the safe user-facing fallback. Rules are evaluated
    in precedence order — the first matching rule decides. Adding a rule is a
    one-line list entry; no detector logic changes.

    Input rules (``_INPUT_RULES``) implement §26.1 prompt-injection prevention,
    §26.2 jailbreak/role-play/authority-invocation detection, and §26.3 unsafe/
    restricted/out-of-scope handling. Output rules (``_OUTPUT_RULES``)
    implement §26.4 output filtering: unsafe content, prohibited disclosures,
    hidden-prompt leakage, unsafe instructions, exam-integrity violations,
    assistant authority claims, and sensitive-data leakage (§37.4, §37.7).

    Safety precedence (§25-26, §37.2): hard safety categories (harassment,
    private data, cheating, system-prompt extraction) are ordered ahead of
    jailbreak/injection and restricted/out-of-scope rules, so an attack that
    also contains a direct safety violation is reported as that violation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai.guardrails.results import GuardrailCategory

# --- Safe user-facing fallbacks (§26.4) ---------------------------------------
# Short, professional, student-first responses (AI_ARCHITECTURE.md §25.3).
# These never reveal detection internals (matched pattern, category, rules).

_FALLBACK_HATE = (
    "I can't help with that. Please keep the conversation respectful and "
    "focused on university support."
)

_FALLBACK_PRIVATE = (
    "I can't disclose another person's private information. If you need help "
    "with your own records, please contact the Registrar's Office."
)

_FALLBACK_CHEATING = (
    "I can't help with cheating or unauthorized exam content. Please review "
    "the university's examination policy, or contact the Examination "
    "Department for official guidance."
)

_FALLBACK_SYSTEM_PROMPT = (
    "I can't share my internal instructions. I'm happy to help with "
    "admissions, examinations, or general university questions."
)

_FALLBACK_JAILBREAK = (
    "I'm here to help with university questions. Please ask about admissions, "
    "examinations, or campus services."
)

_FALLBACK_INJECTION = (
    "I can only help with SMIU admissions, examinations, and general "
    "university questions. Please ask your question directly."
)

_FALLBACK_RESTRICTED = (
    "That topic is outside what I can help with. Please contact the relevant "
    "university department for official guidance."
)

_FALLBACK_OUT_OF_SCOPE = (
    "I can only help with admissions, examinations, and general university "
    "questions. For anything else, please contact the relevant university "
    "department."
)

_FALLBACK_UNSAFE_OUTPUT = (
    "I can't provide that response. If you have questions about admissions, "
    "examinations, or university services, I'm happy to help."
)


@dataclass(frozen=True)
class GuardrailRule:
    """One declarative detection rule (§26.2).

    ``pattern`` is matched (case-insensitively) anywhere in the checked text;
    ``code`` is the stable machine code reported in ``GuardrailDecision.reason``
    (internal only); ``fallback`` is the safe user-facing response.
    """

    category: GuardrailCategory
    code: str
    pattern: re.Pattern[str]
    fallback: str


def _match(phrase: str) -> re.Pattern[str]:
    """Compile a word-boundary, case-insensitive pattern for ``phrase``.

    A trailing ``*`` matches the stem as a prefix (``cheat*`` matches cheat,
    cheating, cheated); otherwise the phrase must appear as a whole word/phrase.
    """
    if phrase.endswith("*"):
        return re.compile(rf"\b{re.escape(phrase[:-1])}\w*", re.IGNORECASE)
    return re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)


def _rule(category: GuardrailCategory, code: str, phrase: str, fallback: str) -> GuardrailRule:
    """Build a rule from a plain-text phrase (word-boundary matching)."""
    return GuardrailRule(category, code, _match(phrase), fallback)


def _rules(
    category: GuardrailCategory,
    fallback: str,
    phrases: tuple[tuple[str, str], ...],
) -> tuple[GuardrailRule, ...]:
    """Build a group of rules that share a category and fallback.

    ``phrases`` is a ``(code, phrase)`` sequence; rule order within the group
    is preserved (precedence = first match wins).
    """
    return tuple(_rule(category, code, phrase, fallback) for code, phrase in phrases)


_INPUT_RULES: tuple[GuardrailRule, ...] = (
    # --- harassment / hate (§25.1, §26.3) -----------------------------------
    *_rules(
        GuardrailCategory.HATE_HARASSMENT,
        _FALLBACK_HATE,
        (
            ("hate.kill_self", "kill yourself"),
            ("hate.kill_threat", "i will kill you"),
            ("hate.slur_idiot", "idiot"),
            ("hate.slur_stupid", "stupid"),
            ("hate.insult", "shut up"),
            ("hate.hate_speech", "hate speech"),
            ("hate.racist", "racist"),
        ),
    ),
    # --- personal data of others (§25.2, §37.6) ------------------------------
    *_rules(
        GuardrailCategory.PRIVATE_DATA,
        _FALLBACK_PRIVATE,
        (
            ("privacy.another_student", "another student"),
            ("privacy.other_student", "other student"),
            ("privacy.someone_else", "someone else"),
            ("privacy.another_person", "another person"),
            ("privacy.friends_records", "my friend's"),
            ("privacy.third_party_result", "his result"),
            ("privacy.third_party_result", "her result"),
            ("privacy.third_party_marks", "his marks"),
            ("privacy.third_party_marks", "her marks"),
            ("privacy.roll_number_of", "roll number of"),
            ("privacy.cnic_of", "cnic of"),
        ),
    ),
    # --- academic misconduct / exam integrity (§25.2, §26.3) ------------------
    *_rules(
        GuardrailCategory.CHEATING,
        _FALLBACK_CHEATING,
        (
            ("cheating.cheat", "cheat"),
            ("cheating.hack", "hack"),
            ("cheating.leak", "leak"),
            ("cheating.forged", "forged"),
            ("cheating.answer_key", "answer key"),
            ("cheating.exam_answers", "exam answers"),
            ("cheating.write_exam", "write my exam"),
            ("cheating.do_exam", "do my exam"),
            ("cheating.change_grade", "change my grade"),
            ("cheating.change_result", "change my result"),
            ("cheating.fake_result", "fake result"),
            ("cheating.impersonate", "impersonate"),
        ),
    ),
    # --- hidden system prompt / internal instructions (§26.2, §37.2) ----------
    *_rules(
        GuardrailCategory.SYSTEM_PROMPT_REQUEST,
        _FALLBACK_SYSTEM_PROMPT,
        (
            ("prompt.system_prompt", "system prompt"),
            ("prompt.system_instructions", "system instructions"),
            ("prompt.your_instructions", "your instructions"),
            ("prompt.your_hidden", "your hidden"),
            ("prompt.initial_prompt", "initial prompt"),
            ("prompt.developer_instructions", "developer instructions"),
            ("prompt.show_me", "show me your prompt"),
            ("prompt.repeat", "repeat your prompt"),
            ("prompt.reveal", "reveal your prompt"),
        ),
    ),
    # --- jailbreak / role-play / authority invocation (§26.2) ----------------
    *_rules(
        GuardrailCategory.JAILBREAK,
        _FALLBACK_JAILBREAK,
        (
            ("jailbreak.ignore_previous", "ignore previous instructions"),
            ("jailbreak.ignore_system", "ignore system instructions"),
            ("jailbreak.override", "override your"),
            ("jailbreak.bypass", "bypass your safety"),
            ("jailbreak.no_rules", "no rules"),
            ("jailbreak.unrestricted", "unrestricted mode"),
            ("jailbreak.dan_mode", "dan mode"),
            ("jailbreak.roleplay", "roleplay as"),
            ("jailbreak.roleplay", "role-play"),
            ("jailbreak.pretend", "pretend you are"),
            ("jailbreak.do_anything", "do anything now"),
            ("jailbreak.disable_guardrails", "disable your guardrails"),
        ),
    ),
    # --- prompt injection (§26.1) --------------------------------------------
    *_rules(
        GuardrailCategory.PROMPT_INJECTION,
        _FALLBACK_INJECTION,
        (
            ("injection.ignore_above", "ignore the above"),
            ("injection.disregard", "disregard all instructions"),
            ("injection.you_are_now", "you are now"),
            ("injection.new_instructions", "new instructions"),
            ("injection.system_instruction", "system instruction:"),
            ("injection.system_prompt", "system prompt:"),
            ("injection.follow_these", "follow these instructions"),
            ("injection.act_as", "act as a"),
            ("injection.ignore_rules", "ignore your rules"),
        ),
    ),
    # --- restricted topics (§25.1-25.2) --------------------------------------
    *_rules(
        GuardrailCategory.RESTRICTED_TOPIC,
        _FALLBACK_RESTRICTED,
        (
            ("restricted.legal", "legal advice"),
            ("restricted.lawsuit", "lawsuit"),
            ("restricted.medical", "medical advice"),
            ("restricted.diagnose", "diagnose"),
            ("restricted.prescription", "prescription"),
            ("restricted.financial", "financial advice"),
            ("restricted.tax", "tax advice"),
            ("restricted.investment", "investment advice"),
            ("restricted.loan", "loan"),
            ("restricted.immigration", "immigration advice"),
            ("restricted.visa", "visa"),
        ),
    ),
    # --- out of scope (§26.3) ------------------------------------------------
    *_rules(
        GuardrailCategory.OUT_OF_SCOPE,
        _FALLBACK_OUT_OF_SCOPE,
        (
            ("scope.weather", "weather"),
            ("scope.recipe", "recipe"),
            ("scope.cooking", "cooking"),
            ("scope.movie", "movie"),
            ("scope.cricket", "cricket"),
            ("scope.football", "football"),
            ("scope.gaming", "gaming"),
            ("scope.politics", "politics"),
            ("scope.election", "election"),
            ("scope.horoscope", "horoscope"),
            ("scope.joke", "tell me a joke"),
            ("scope.story", "tell me a story"),
            ("scope.celebrity", "celebrity"),
        ),
    ),
)


_OUTPUT_RULES: tuple[GuardrailRule, ...] = (
    # --- unsafe / abusive output (§26.4, §26.5) ------------------------------
    *_rules(
        GuardrailCategory.UNSAFE_OUTPUT,
        _FALLBACK_UNSAFE_OUTPUT,
        (
            ("unsafe.hate", "kill yourself"),
            ("unsafe.threat", "i will kill you"),
            ("unsafe.slur", "idiot"),
            ("unsafe.slur", "stupid"),
            ("unsafe.slur", "shut up"),
            ("unsafe.hate", "hate speech"),
        ),
    ),
    # --- sensitive-data / prohibited disclosures (§37.4, §37.7) --------------
    *_rules(
        GuardrailCategory.SENSITIVE_DATA,
        _FALLBACK_UNSAFE_OUTPUT,
        (
            ("sensitive.another_student", "another student"),
            ("sensitive.other_student", "other student"),
            ("sensitive.someone_else", "someone else"),
            ("sensitive.roll_number_of", "roll number of"),
            ("sensitive.roll_no_of", "roll no of"),
            ("sensitive.cnic_of", "cnic of"),
            ("sensitive.third_party_result", "his result"),
            ("sensitive.third_party_result", "her result"),
            ("sensitive.api_key", "api key"),
            ("sensitive.secret_key", "secret key"),
        ),
    ),
    # --- exam-integrity violations in output (§25.1, §26.4) ------------------
    *_rules(
        GuardrailCategory.CHEATING,
        _FALLBACK_UNSAFE_OUTPUT,
        (
            ("cheating.how_to_cheat", "here's how to cheat"),
            ("cheating.how_to_cheat", "here is how to cheat"),
            ("cheating.leaked_paper", "leaked paper"),
            ("cheating.exam_answers_are", "the exam answers are"),
            ("cheating.help_cheat", "i can help you cheat"),
        ),
    ),
    # --- assistant claiming official authority (§25.1, §26.4) ----------------
    *_rules(
        GuardrailCategory.AUTHORITY_CLAIM,
        _FALLBACK_UNSAFE_OUTPUT,
        (
            ("authority.i_am_registrar", "i am the registrar"),
            ("authority.i_am_official", "i am an official"),
            ("authority.i_am_university", "i am the university"),
            ("authority.i_approve", "i approve your"),
            ("authority.i_am_authorized", "i am authorized"),
        ),
    ),
    # --- hidden/system-prompt leakage (§26.4, §37.2) -------------------------
    *_rules(
        GuardrailCategory.SENSITIVE_DATA,
        _FALLBACK_UNSAFE_OUTPUT,
        (
            ("leak.system_prompt", "my system prompt"),
            ("leak.internal_instructions", "my internal instructions"),
            ("leak.developer", "my developer instructions"),
        ),
    ),
)
