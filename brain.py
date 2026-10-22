import time
from datetime import datetime

from openai import OpenAI, OpenAIError

import config
import tools


class Brain:
    def __init__(self):
        self.providers = []
        if config.BRAIN_API_KEY:
            self.providers.append(self._make_provider("primary", config.BRAIN_BASE_URL,
                                                      config.BRAIN_API_KEY, config.BRAIN_MODEL))
        if config.FALLBACK_BASE_URL and config.FALLBACK_MODEL:
            self.providers.append(self._make_provider("fallback", config.FALLBACK_BASE_URL,
                                                      config.FALLBACK_API_KEY, config.FALLBACK_MODEL))
        self.history: list[dict] = []

    @staticmethod
    def _make_provider(label, base_url, api_key, model):
        client = OpenAI(base_url=base_url, api_key=api_key,
                        timeout=config.REQUEST_TIMEOUT, max_retries=0)
        return {"label": label, "client": client, "model": model}

    @staticmethod
    def _tool_call_dict(call) -> dict:
        data = {"id": call.id, "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments}}
        extra = (getattr(call, "model_extra", None) or {}).get("extra_content")
        if extra:
            data["extra_content"] = extra
        return data

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
        for p in self.providers:
            try:
                return p["client"].chat.completions.create(
                    model=p["model"], messages=messages,
                    tools=tools.schemas(), tool_choice="auto", temperature=0.4,
                )
            except OpenAIError as e:
                print(f"[Brain] {p['label']} ({p['model']}) failed: {type(e).__name__}: {e}")
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
                print(f"[timing] brain call {time.monotonic() - started:.1f}s")

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