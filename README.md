# Build the Loop — starter folder

Session 1 of the ASA LangGraph training. **90 minutes, hands-on.**

You are going to build an AI application that writes a support reply, judges
its own work, and rewrites it until the answer is good enough — or gives up
and hands the ticket to a human.

**You will not write any code.** You will describe the application to Claude
Code and it will build it. The skill being practised is the describing.

## What's in here

Starter files — these came with the folder:

| File | What it is |
|---|---|
| `tickets.py` | Three sample support tickets. Everyone uses the same three, so results can be compared. **Don't change this file.** |
| `.env.example` | Rename to `.env`. Your facilitator gives you the two key values in the session. |
| `requirements.txt` | What to install. |
| `verify.py` | Proves your setup works. |

The application — this is the part you build by describing it:

| File | What it is |
|---|---|
| `main.py` | The agent: state, seven nodes, and the conditional edge that loops. Runs on its own from the terminal. |
| `app.py` | Web UI that drives `main.py` and draws each step as it happens. |
| `ui.py` | Design tokens, CSS, and the graph diagram. Presentation only. |
| `run.ps1`, `run.cmd` | Start either one from the venv, creating the venv if it's missing. |

## Setup — do this before the session

```
python --version      # need 3.11 or newer
claude --version      # Claude Code, installed and signed in
```

Rename `.env.example` to `.env` (leave the key lines empty for now):

```
copy .env.example .env      # Windows
cp .env.example .env        # macOS / Linux
```

Then create the virtual environment and install into it:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
.venv/bin/python -m pip install -r requirements.txt           # macOS / Linux

.venv\Scripts\python.exe verify.py
```

Send your facilitator the last line. It must say `READY`. The two API keys
get pasted in during the session — everything else has to work beforehand.

Everything runs from `.venv`, so nothing gets installed into your system
Python. `run.ps1` and `run.cmd` build the venv for you if it isn't there yet.

## Run it

```
.\run.ps1                  # web UI at http://localhost:8501
.\run.ps1 TICKET-001       # one ticket, in the terminal
```

`run.cmd` takes the same arguments if PowerShell's execution policy gets in
the way. To skip the scripts entirely:

```
.venv\Scripts\python.exe -m streamlit run app.py
.venv\Scripts\python.exe main.py TICKET-001
```

## In the session

1. Screenshot the architecture diagram from the student guide and save it in
   this folder as `architecture.png`.
2. Paste the two keys your facilitator gives you into `.env`.
3. Run `claude` in this folder.
4. Follow the student guide from step 1.

## Two rules

- **Don't edit code by hand.** Anything you want changed, ask for it.
- **When it breaks,** paste the error into Claude Code and say "this failed,
  fix it and run it again." That loop is the skill.

## Web app / Docker (EC2)

1. On the EC2 instance install Docker (`sudo dnf install -y docker docker-compose-plugin && sudo systemctl enable --now docker` on Amazon Linux 2023).
2. Clone the repo and create `.env` with `OPENAI_API_KEY=...` (optionally `OPENAI_MODEL`, `LANGSMITH_*`).
3. `docker compose up -d --build`
4. Open port 80 in the instance's security group and browse to `http://<ec2-public-ip>/`.

Local run: `pip install -r requirements.txt && uvicorn server:app --port 8000`.
Conversations are held in memory (single worker); a restart clears them.
