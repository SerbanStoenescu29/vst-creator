"""Run this before the session and send your facilitator the last line.

    python verify.py
"""

import os
import sys


def main() -> int:
    ok = True

    v = sys.version_info
    if v < (3, 11):
        print(f"[FAIL] Python {v.major}.{v.minor}.{v.micro} — need 3.11 or newer")
        ok = False
    else:
        print(f"[ok]   Python {v.major}.{v.minor}.{v.micro}")

    try:
        import langgraph
        print(f"[ok]   langgraph {getattr(langgraph, '__version__', 'installed')}")
    except ImportError:
        print("[FAIL] langgraph missing — run: pip install -r requirements.txt")
        ok = False

    try:
        import tickets
        print(f"[ok]   tickets: {', '.join(tickets.list_ticket_ids())}")
    except Exception as exc:
        print(f"[FAIL] cannot load tickets.py — {exc}")
        ok = False

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("[FAIL] python-dotenv missing — run: pip install -r requirements.txt")
        return 1

    if not os.path.exists(".env"):
        print("[warn] no .env yet — rename .env.example to .env")
    else:
        filled = [k for k in ("OPENAI_API_KEY",)
                  if os.getenv(k)]
        if filled:
            print(f"[ok]   .env has: {', '.join(filled)}")
        else:
            print("[warn] .env found but no keys in it yet — "
                  "your facilitator gives you those in the session")

    print()
    print("READY" if ok else "NOT READY")
    print("(keys can be pasted in during the session — everything else must be ok now)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
