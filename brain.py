import time
from datetime import datetime

from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError

import config
import tools


class Brain:
    def __init__(self):
        self.providers = []
        for name in config.BRAIN_ORDER:
            cfg = config.PROVIDERS.get(name)
            if not cfg or not cfg["api_key"] or not cfg["model"]:
                if cfg is not None and name != "ollama":
                    print(f"[Brain] {name}: no API key in .env, skipping")
                continue
            self.providers.append({
                "label": name, "model": cfg["model"], "skip_until": 0.0,
                "keep_extra": "googleapis" in cfg["base_url"],  # Gemini's thought signatures
                "client": OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"],
                                 timeout=cfg["timeout"], max_retries=0),
            })
        print("[Brain] order: " + " -> ".join(f"{p['label']} ({p['model']})" for p in self.providers))
        self.history: list[dict] = []
        self.last_provider = ""

    @staticmethod
    def _tool_call_dict(call) -> dict:
        data = {"id": call.id, "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments}}
        extra = (getattr(call, "model_extra", None) or {}).get("extra_content")
        if extra:
            data["extra_content"] = extra
        return data

    @staticmethod
    def _without_extra(messages: list[dict]) -> list[dict]:
        cleaned = []
        for m in messages:
            if m.get("tool_calls"):
                m = {**m, "tool_calls": [{k: v for k, v in c.items() if k != "extra_content"}
                                         for c in m["tool_calls"]]}
            cleaned.append(m)
        return cleaned

    def _system_prompt(self) -> str:
        facts = tools.load_facts()
        facts_text = "\n".join(f"- {f}" for f in facts) if facts else "(nothing saved yet)"
        now = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
        return (
            "You are V.E.C.T.O.R., a voice assistant running on the user's Windows laptop. "
            f"Address the user as '{config.USER_TITLE}'.\n"
            "Your replies are spoken aloud: one or two short sentences, plain words, "
            "no markdown, no lists, no emojis.\n"
            "When the user wants something done on the laptop, use a tool instead of describing it. "
            "After a tool succeeds, confirm in a few words. Never claim you did something unless a "
            "tool result confirmed it. If a tool fails, say so honestly.\n"
            "If a request is unclear, ask one short question.\n"
            f"Current date and time: {now}.\n"
            f"Things you remember about the user:\n{facts_text}"
        )

    def _chat(self, messages):
        last_error = None
        now = time.monotonic()
        # providers that failed recently go to the back instead of costing a timeout every turn
        ready = [p for p in self.providers if p["skip_until"] <= now]
        resting = [p for p in self.providers if p["skip_until"] > now]
        for p in ready + resting:
            try:
                msgs = messages if p["keep_extra"] else self._without_extra(messages)
                reply = p["client"].chat.completions.create(
                    model=p["model"], messages=msgs,
                    tools=tools.schemas(), tool_choice="auto", temperature=0.4,
                )
                self.last_provider = p["label"]
                return reply
            except OpenAIError as e:
                if isinstance(e, RateLimitError):
                    retry = e.response.headers.get("retry-after") if getattr(e, "response", None) else None
                    wait = float(retry) if retry and retry.replace(".", "", 1).isdigit() else config.QUOTA_COOLDOWN_SECONDS
                    reason = "out of quota"
                elif isinstance(e, APIConnectionError):
                    wait, reason = config.OFFLINE_COOLDOWN_SECONDS, "not reachable"
                else:
                    wait, reason = 60, "error"
                p["skip_until"] = time.monotonic() + wait
                print(f"[Brain] {p['label']} ({p['model']}) {reason}, resting {wait / 60:.0f} min: "
                      f"{type(e).__name__}: {str(e)[:200]}")
                last_error = e
        raise RuntimeError(f"All brains failed: {last_error}")

    def ask(self, user_text: str) -> str:
        if not self.providers:
            return "I have no brain configured. Please add an API key to the dot env file."

        messages = [{"role": "system", "content": self._system_prompt()}]
        messages += self.history
        messages.append({"role": "user", "content": user_text})

        reply = ""
        try:
            for _ in range(config.MAX_TOOL_ROUNDS):
                started = time.monotonic()
                msg = self._chat(messages).choices[0].message
                print(f"[timing] brain call {time.monotonic() - started:.1f}s via {self.last_provider}")

                if not msg.tool_calls:
                    reply = (msg.content or "").strip()
                    break

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [self._tool_call_dict(c) for c in msg.tool_calls],
                })
                for call in msg.tool_calls:
                    result = tools.run_tool(call.function.name, call.function.arguments)
                    print(f"[tool] {call.function.name}({call.function.arguments}) -> {result}")
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
            else:
                reply = f"That took too many steps, {config.USER_TITLE}. Could you simplify the request?"
        except RuntimeError as e:
            print(f"[Brain] {e}")
            return f"I can't reach my brain right now, {config.USER_TITLE}."

        reply = reply or f"Done, {config.USER_TITLE}."
        self.history += [{"role": "user", "content": user_text},
                         {"role": "assistant", "content": reply}]
        self.history = self.history[-2 * config.HISTORY_TURNS:]
        return reply