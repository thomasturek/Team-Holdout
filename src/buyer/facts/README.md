# The Scout: data, costing and facts

This folder holds the part of the agent that must always be exactly right. It reads the data package, prices any deal in euros, describes every supplier and prepares the facts we cite in our e-mails. Nothing in this folder guesses. When a number is uncertain, the uncertainty is stated next to it.

The owner of this folder is Felix.


## Step 1: Reading the data

All data enters the agent through `package.py`. It looks in three places, in a fixed order. First it checks the facts that a hidden case brings with it, then the Sunday data release, and finally the original data package in `data/`. The package itself holds `facts.json`, a SQLite database called `world.sqlite`, and the texts of contracts and letters.

The same module provides the guardrail `citable`, which answers whether a data reference may be sent to a supplier. Only references that exist in a published facts file or in the case itself pass this check.


## Step 2: Pricing a deal

`costing.py` wraps the official cost function from the starter kit. It adds one thing the official function cannot do on its own, which is to estimate the charge the arena makes in strategic cases for leaving a supplier below a sustainable margin. That charge needs an estimate of the supplier's full cost. The module uses the cost revealed by a charge we paid in the past where one exists, and a supplier specific estimate otherwise. Rough estimates are deliberately left out, because a wrong estimate does more harm than none.

Every other part of the agent calls this module when it needs a cost, so there is only one view of what a deal is worth.


## Step 3: Describing suppliers

`profile.py` builds a profile for every supplier and every part it supplies. A profile includes the supplier's country and ownership, a type such as family foundry or group with an approval ladder, an estimate of the lowest price it can accept, how much it needs cash, its latest quality scorecard, its standard terms and short notes from its correspondence and the news.

To rebuild every profile and write them to `runs/profiles/all.json`, run the module directly.

```bash
uv run python -m buyer.facts.profile
```

Profiles can be corrected by hand in `overrides.json`. Each correction names the supplier, the field it replaces and the evidence behind it. Corrections apply every time a profile is read, so no rebuild is needed.


## Step 4: Remembering past sessions

`memory.py` records what our own sessions taught us about each supplier. Every finished session reports the cost of the best deal the case allows, and at the terms we closed on, that cost reveals the lowest price the supplier would have accepted. This observed floor is far tighter than any estimate from the data. Because the final uses the same 46 suppliers, a supplier we met in practice is likely to be met again.

`dossier.py` turns those observations into a short plain text brief per supplier for the writer. The brief says who decides, what the supplier cares about and which angle tends to work.

Both are rebuilt from the practice logs with one command each, and the results are committed so that the machine running the final has them.

```bash
uv run python -m buyer.facts.memory
uv run python -m buyer.facts.dossier
```


## Step 5: Building facts we can cite

`claims.py` builds the bank of facts for a case. Each fact is a finished English sentence that contains its figure and its data reference. There are five kinds. A fact can state the twelve month change of an index that drives the part's cost. It can point out that a price letter gave less notice than the contract requires. It can quote the supplier's on-time delivery rate or defect rate. It can show that our past order prices with the supplier were stable or falling. In a request for quotation, it can cite a rival's lower offer.

The module also contains its own copy of the arena's checking rules, so every sentence is verified before it is offered. It respects the arena's limits as well. Each reference counts only once per case, across all suppliers, and at most three checked facts may appear in one message.


## Step 6: Choosing a strategy

`strategy.py` chooses one of five broad ways to play a supplier, based on its profile and, later, on its replies. An aggressive strategy opens deep and moves in small steps. A cooperative strategy trades levers and keeps a friendly tone. A patient strategy matches the supplier's small steps. An escalation strategy asks for the decision to be taken higher when our contact has little authority. A secure strategy closes near the target without pushing, for suppliers we cannot afford to lose. The chosen strategy adjusts the policy's parameters and sets the tone for the writer.


## Step 7: Features for analysis

The `features/` folder builds point in time features over the supplier database for analysis and machine learning. Every feature is described in `features/FEATURES.md`.


## Tests

The tests for this folder live in `tests/` next to the code. The default test run does not include them, so run them by naming the folder.

```bash
uv run pytest src/buyer/facts
```
