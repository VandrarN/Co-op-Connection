import json, os, sys, random, time, secrets
from typing import Dict, List

def resource_path(rel_path: str) -> str:
    rel = rel_path.replace("\\", os.sep).replace("/", os.sep)
    bases = []
    for b in (
        getattr(sys, "_MEIPASS", None),
        os.path.abspath(os.path.dirname(__file__)) if "__file__" in globals() else None,
        os.getcwd(),
        "/data/data/org.python/assets",
    ):
        if b and b not in bases:
            bases.append(b)
    for base in bases:
        # pygbag unpacks app files under an assets/ directory in the browser.
        # Try both the normal project-relative path and the browser archive path.
        for candidate in (
            os.path.join(base, rel),
            os.path.join(base, "assets", rel),
            os.path.join(base, "assets", os.path.basename(rel)),
        ):
            if os.path.exists(candidate):
                return candidate
    target = os.path.basename(rel)
    for base in bases:
        try:
            for root, _dirs, files in os.walk(base):
                if target in files:
                    return os.path.join(root, target)
        except Exception:
            pass
    return os.path.join(bases[0] if bases else os.getcwd(), rel)

class ContentManager:
    """
    Loads card texts from content/*.json (list of strings).
    Keeps per-deck shuffled queues to avoid repeats until exhausted.

    ZIP-aligned upgrade:
    - Every app launch creates a fresh per-session RNG seed,
      so each deck order is randomized anew for each session.
    - Within a session, behavior remains the same: no repeats until exhaustion,
      then reshuffle and continue.
    """
    def __init__(self, content_dir="content"):
        self.content_dir = content_dir
        self.decks: Dict[str, List[str]] = {}
        self.queues: Dict[str, List[str]] = {}
        self.fun_universal: List[str] = []
        self.fun_online: List[str] = []
        self.online_fun_enabled = False

        # Fresh session seed each launch (time + crypto randomness).
        self.session_seed = (time.time_ns() ^ secrets.randbits(64)) & ((1 << 64) - 1)
        self.rng = random.Random(self.session_seed)

    def _load_list(self, filename: str) -> List[str]:
        path = resource_path(os.path.join(self.content_dir, filename))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise ValueError(f"{filename} must be a JSON list of strings.")
        return data

    def load_all(self):
        # Questions
        self.decks["CASUAL_Q"] = self._load_list("casual.json")
        self.decks["SOUL_Q"]   = self._load_list("soul.json")
        self.fun_universal = self._load_list("fun.json")
        try:
            self.fun_online = self._load_list("fun_online.json")
        except FileNotFoundError:
            self.fun_online = []
        self.decks["FUN_Q"] = list(self.fun_universal)
        self.decks["HEART_SOFT_Q"]   = self._load_list("heart_soft.json")
        self.decks["HEART_WARM_Q"]   = self._load_list("heart_warm.json")
        self.decks["HEART_FLIRTY_Q"] = self._load_list("heart_flirty.json")
        self.decks["COLD_Q"] = self._load_list("cold.json")
        self.decks["HOT_Q"] = self._load_list("hot.json")

        # Static player-authored prompt decks
        self.decks["ASSUMPTION_Q"] = ["Make an assumption about the other player."]
        self.decks["FREE_Q"] = ["Create your own question or challenge."]

        # Consequences
        self.decks["CASUAL_C"] = self._load_list("consequence_casual.json")
        self.decks["SOUL_C"]   = self._load_list("consequence_soul.json")
        self.decks["FUN_C"]    = self._load_list("consequence_fun.json")
        self.decks["HEART_C"]  = self._load_list("consequence_heart.json")

        # Heart consequence tiers (optional; falls back to consequence_heart.json)
        try:
            self.decks["HEART_SOFT_C"] = self._load_list("consequence_heart_soft.json")
            self.decks["HEART_WARM_C"] = self._load_list("consequence_heart_warm.json")
            self.decks["HEART_FLIRTY_C"] = self._load_list("consequence_heart_flirty.json")
        except FileNotFoundError:
            pass

        # init queues
        for k in self.decks:
            self._reshuffle(k)

    def set_online_fun_enabled(self, enabled: bool):
        """Toggle the optional online/environment Fun prompts.

        When disabled, FUN_Q only uses universal prompts that work anywhere.
        When enabled, environment/object prompts are added to the Fun pool.
        """
        enabled = bool(enabled)
        if self.online_fun_enabled == enabled and "FUN_Q" in self.decks:
            return
        self.online_fun_enabled = enabled
        merged = list(self.fun_universal)
        if enabled:
            merged.extend(self.fun_online)
        self.decks["FUN_Q"] = merged
        self._reshuffle("FUN_Q")

    def _reshuffle(self, key: str):
        q = list(self.decks[key])
        self.rng.shuffle(q)
        self.queues[key] = q

    def _draw(self, key: str) -> str:
        q = self.queues.get(key, [])
        if not q:
            self._reshuffle(key)
            q = self.queues[key]
        return q.pop()

    def get_question(self, category: str, heart_tier: str = "SOFT") -> str:
        if category == "CASUAL":
            return self._draw("CASUAL_Q")
        if category == "SOUL":
            return self._draw("SOUL_Q")
        if category == "FUN":
            return self._draw("FUN_Q")
        if category == "HEART":
            tier = heart_tier.upper()
            if tier == "SOFT":
                return self._draw("HEART_SOFT_Q")
            if tier == "WARM":
                return self._draw("HEART_WARM_Q")
            return self._draw("HEART_FLIRTY_Q")
        if category == "COLD":
            return self._draw("COLD_Q")
        if category == "HOT":
            return self._draw("HOT_Q")
        if category == "ASSUMPTION":
            return self._draw("ASSUMPTION_Q")
        if category == "FREE":
            return self._draw("FREE_Q")
        # WILDCARD never draws directly (user chooses a deck)
        return "(Missing category)"

    def get_consequence(self, category: str, heart_tier: str = "SOFT") -> str:
        if category == "CASUAL":
            return self._draw("CASUAL_C")
        if category == "SOUL":
            return self._draw("SOUL_C")
        if category == "FUN":
            return self._draw("FUN_C")
        if category == "HEART":
            tier = heart_tier.upper()
            if tier == "SOFT" and "HEART_SOFT_C" in self.decks:
                return self._draw("HEART_SOFT_C")
            if tier == "WARM" and "HEART_WARM_C" in self.decks:
                return self._draw("HEART_WARM_C")
            if tier == "FLIRTY" and "HEART_FLIRTY_C" in self.decks:
                return self._draw("HEART_FLIRTY_C")
            return self._draw("HEART_C")
        if category in ("COLD", "HOT", "ASSUMPTION", "FREE"):
            return "Create a playful consequence that fits this card, or answer anyway."
        return "(Missing category)"


SUPPORTED_FUTURE_DECKS = ["HOT", "ASSUMPTION", "COLD", "FREE"]
