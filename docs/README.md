# Documentation

This folder explains the project in more depth than the main README. Each document covers one subject, and they are meant to be read in the order below. If you are new to the project, start with the main [README](../README.md) and then come back here.


## Reading order

Start with [How scoring works](SCORING.md). Everything the agent does is aimed at a lower total cost, so it helps to understand exactly how the arena prices a deal before reading anything else.

Next, read [Architecture](ARCHITECTURE.md). It describes the four parts of the agent, how they talk to each other, and what a single move looks like from the moment a supplier replies until our answer goes out.

Then read [Running the agent](RUNNING.md). It is the practical guide. It covers setup, the sandbox, practice sessions, the live final, the harvester, and what to do when something goes wrong.

Finally, [Run logs](LOGS.md) describes the format of the log files in detail. You only need it if you want to analyse past sessions with your own scripts.


## Documentation inside the code

Each part of the agent also has its own README next to its code, which describes the files in that folder and how to use them.

The Scout is described in [src/buyer/facts/README.md](../src/buyer/facts/README.md). The Analyst is described in [src/buyer/policy/README.md](../src/buyer/policy/README.md), and its simulator in [src/buyer/sim/README.md](../src/buyer/sim/README.md). The Diplomat is described in [src/buyer/llm/README.md](../src/buyer/llm/README.md). The Operator is described in [src/buyer/runtime/README.md](../src/buyer/runtime/README.md). The Counterpart dashboard is described in [frontend/README.md](../frontend/README.md).


## Documents from Tacto

The rules of the challenge come from the organisers and are kept unchanged. The challenge itself is in [CHALLENGE.md](../CHALLENGE.md), the full brief is in [brief/brief.md](../brief/brief.md), the API reference is in [brief/api.md](../brief/api.md), and the submission instructions are in [brief/submission.md](../brief/submission.md). The data package is described in [data/README.md](../data/README.md).
