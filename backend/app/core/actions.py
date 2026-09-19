"""Canonical tool names used by the policy engine."""

READ_EMAIL = "read_email"
DRAFT_EMAIL = "draft_email"
SEND_EMAIL = "send_email"
DELETE_FILE = "delete_file"
ACCESS_FILE = "access_file"
OVERRIDE_POLICY = "override_policy"

_ALIASES: dict[str, str] = {
    "read_email": READ_EMAIL,
    "read_mail": READ_EMAIL,
    "draft_email": DRAFT_EMAIL,
    "draft_reply": DRAFT_EMAIL,
    "draft_mail": DRAFT_EMAIL,
    "send_email": SEND_EMAIL,
    "send_mail": SEND_EMAIL,
    "send_file": SEND_EMAIL,
    "access_file": ACCESS_FILE,
    "open_file": ACCESS_FILE,
    "read_file": ACCESS_FILE,
    "delete_file": DELETE_FILE,
    "delete": DELETE_FILE,
    "override_policy": OVERRIDE_POLICY,
    "update_policy": OVERRIDE_POLICY,
    "set_policy": OVERRIDE_POLICY,
    "disable_veil": OVERRIDE_POLICY,
    "bypass_policy": OVERRIDE_POLICY,
}

SIDE_EFFECTING_ACTIONS = frozenset({SEND_EMAIL, DELETE_FILE, OVERRIDE_POLICY})
PROHIBITED_FOR_UNTRUSTED = SIDE_EFFECTING_ACTIONS
LLM_PROPOSABLE_TOOLS = frozenset(
    {READ_EMAIL, DRAFT_EMAIL, SEND_EMAIL, ACCESS_FILE, DELETE_FILE}
)


def canonicalize_action(tool_name: str) -> str:
    key = (tool_name or "").strip().lower()
    return _ALIASES.get(key, key)
