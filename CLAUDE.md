# helen-shtab-bot

Telegram bot «Спроси Хелен» (`main.py`, `prompts.py`) plus trading skill packs installed as project skills.

## Trading skill packs

- **Day Trader** (US stocks): `.claude/skills/trader-*`. Working files go to `trader/` (gitignored).
- **HyperGrok** (Hyperliquid crypto perps), v1.7.1: skills `.claude/skills/desk-*`, `hyperliquid-*`, `hypergrok-bootstrap`; roles `.claude/agents/`; tools, hook and docs in `hypergrok/`.
  - Where a HyperGrok skill says `scripts/<tool>.py`, run `python3 hypergrok/scripts/<tool>.py`.
  - The desk's `/workspace/trading-desk/` is `trading-desk/` here (gitignored). `/workspace/hypergrok/` is `hypergrok/` plus `.claude/`.
  - `.claude/settings.json` runs `hypergrok/hooks/exchange_write_gate.py` before Bash commands: it asks for confirmation on anything that looks like a Hyperliquid exchange write. It never approves.
  - Engagement level: **1, research desk** — public data only, no API wallet, no testnet or mainnet sends. Moving up a level is the user's decision, stated in chat.

No pack places an order on its own. Every order needs the pack's risk check and the user's explicit yes for that exact order.
