# Architecture

This document explains how the buyer agent is put together. It starts with the idea behind the design, then walks through the four parts one at a time, and ends by following a single move through the whole system.


## Step 1: The idea behind the design

A negotiation looks like a conversation, so it is tempting to hand the whole thing to a language model. We decided against that. A language model is good at reading and writing e-mails, but it is not reliable with numbers, and in this challenge a single wrong number can lose a case. A price typed into the wrong field, a fact cited with the wrong figure or an acceptance of an offer that breaks a must-have each costs real points.

So the work is split by what each tool does best. Plain code knows the rules and does all the arithmetic. A tuned policy, which is also plain code, decides the strategy. The language model only reads the supplier's prose and writes ours, and it is never allowed to choose a number, a term or whether to accept.

This split is the most important rule in the project, and the code enforces it in several places.


## Step 2: The four parts

The agent has four parts. Each part has one owner on the team and lives in its own folder under `src/buyer/`.

```
   case files, supplier e-mails
              |
              v
   SCOUT    facts/      data, costing, supplier profiles, verified facts
              |
              v
   ANALYST  policy/     decides the next move: offers, accept or walk away
              |
              v
   DIPLOMAT llm/        reads supplier e-mails, writes ours around the decision
              |
              v
   OPERATOR runtime/    talks to the arena, runs every thread at once, logs everything
```

The parts talk to each other through a small set of data classes, which are defined in `src/buyer/interfaces.py`. These classes are the contract between the team members. A supplier profile flows from the Scout to the other parts. A list of signals flows from the Diplomat to the Analyst after each supplier reply. A decision flows from the Analyst to the Diplomat and the Operator. A claim, which is a fact we can cite, flows from the Scout through the Analyst into the e-mail.


## Step 3: The Scout

The Scout lives in `src/buyer/facts/` and is responsible for everything that must be exactly right.

It begins with the data package that Tacto publishes, which describes 46 suppliers in detail. The package holds contracts, purchase orders, quality scorecards, correspondence, news and the market indices that drive each supplier's costs. The Scout reads all of this through one front door, `package.py`, which also merges the Sunday data release and any facts that a hidden case brings with it.

From the data the Scout builds a profile of every supplier. The profile estimates the lowest price the supplier can accept, how much it needs cash, whether it approves prices in one step or through a ladder of managers, and how good its quality has been. It also remembers what our own past sessions revealed about each supplier, because a supplier met in practice is likely to appear again in the final.

The Scout also builds a bank of facts that we can cite. Examples are the real twelve month change of a steel index, a supplier's defect rate over the last four quarters, or the fact that a price letter gave less notice than the contract requires. Each fact is a finished English sentence that contains its own figure and its data reference. The Scout checks every sentence against its own copy of the arena's rules, so a cited fact is confirmed rather than contradicted.

Finally, the Scout chooses a broad strategy for each supplier, such as patient, cooperative or aggressive, based on what the profile and the replies show.


## Step 4: The Analyst

The Analyst lives in `src/buyer/policy/` and makes every decision.

After each supplier reply, the Analyst looks at the state of the thread. That state holds the case, the supplier profile, every offer made so far by both sides, the signals the Diplomat read from the latest reply, and how many rounds and how much time are left. From this it returns one decision. It can send new offers, accept one of the supplier's term sheets, or walk away.

When it sends offers, it builds two or three complete term sheets. Each one has a price and values for the other negotiable terms, and each is costed with the official formula. The sheets trade levers against each other so that the supplier's reply tells us which levers it values. The Analyst also picks up to three facts from the Scout's bank to cite, and it never reuses a fact that was already cited in the case.

The Analyst's behaviour is controlled by a small set of parameters, stored in `src/buyer/policy/params.json`. They control how far below the supplier's floor to open, how quickly to concede, how close an offer must come before we accept it, and when to push back on a final offer. The parameters are tuned in the simulator described in `src/buyer/sim/README.md` and checked against real sessions.


## Step 5: The Diplomat

The Diplomat lives in `src/buyer/llm/` and handles language.

Its first job is reading. Each supplier e-mail is turned into a fixed set of signals. The signals record whether the supplier mentions cash pressure or a capacity problem, whether it uses final offer language, whether an approval is pending, which of our arguments it accepted or rejected, and what it asks for in return. Fast keyword rules produce these signals in milliseconds, and a language model refines them in the background when it answers in time.

Its second job is writing. The model writes only the prose of our reply, with placeholders where the facts, the offers and the questions belong. Code then fills those placeholders with the exact sentences and term sheets from the decision. A guard checks the finished e-mail and rejects any figure the model wrote itself. If the model is slow, unavailable or produces something the guard rejects, a template writer produces a safe e-mail from the same decision.


## Step 6: The Operator

The Operator lives in `src/buyer/runtime/` and runs everything.

The arena gives each supplier thread 60 seconds to answer after a supplier reply, and three missed deadlines in a row end the thread. The starter kit plays one supplier at a time, which would let the other suppliers in a request for quotation time out. The Operator therefore gives every supplier thread its own worker and its own clock, and all threads of a case run at the same time while sharing what they know. That way the Analyst can cite a rival's offer to another bidder.

Every move has a budget of 25 seconds from the supplier's reply. If a decision has not come back after 40 seconds, the worker sends a short holding message without any numbers instead of letting the thread time out.

Ending a case is handled with extra care. When the Analyst accepts or walks away, the Operator keeps checking with the arena until the end is confirmed, and it never sends two final actions without an answer in between.

The Operator also contains the runners for the sandbox, practice and the live final, and the harvester that plays the sandbox without stopping. It logs every event of every session to disk, and those logs feed both the simulator and the Counterpart dashboard.


## Step 7: One move, from reply to answer

It helps to see the parts work together on one move.

A supplier's reply arrives in one of the Operator's thread workers. The worker stores the reply, starts downloading any attachments in the background, and asks the agent for the next move.

The agent first reads the reply with the Diplomat's keyword rules, which takes milliseconds. At the same time it starts the language model reader in the background.

The Analyst then decides. It updates the thread state with the new offer and signals, costs the supplier's term sheets, checks the must-haves and the fallback, and returns a decision.

The Diplomat writes the e-mail around that decision. The language model writes the prose, code inserts the facts and term sheets, and the guard checks the result.

The worker sends the message to the arena and logs the decision, the timing and the message. The whole move normally takes a few seconds, well inside the 25 second budget.


## Step 8: Safety rules

A few rules hold everywhere, and each is enforced in code rather than left to the model.

The agent never accepts a term sheet that breaks a must-have or costs more than our fallback. It never sends a data reference that does not exist in the data package, the Sunday release or the case. The language model never produces a number that reaches a term sheet. The agent never reads the arena's event feed, screen, leaderboard or results. There is one API key and one shared, rate limited client per process.
