# The simulator

This folder holds a synthetic supplier and the tools to tune the policy against it. Real practice sessions are limited to 200 a day, so we cannot learn a strategy from them alone. Instead, we model how suppliers behave, check that model against real sessions, and tune the policy against thousands of simulated negotiations. The owner of this folder is Thomas.


## Step 1: The synthetic supplier

`supplier.py` contains the synthetic supplier. Each one is described by a set of hidden settings. These include its full cost, the margin it opens with, the lowest margin it will accept, what money is worth to it, how quickly it concedes, how many rounds it waits before declaring a final offer, and how likely it is to walk away after a final offer that we refuse.

The supplier answers our term sheets the way the practice suppliers did. It makes one large first step, each later step is smaller than the last, and many suppliers then stop moving altogether. It values non price terms, such as faster payment, with the same formula the arena uses, and a valuable term can buy one more step on price.


## Step 2: A population of suppliers

`population.py` draws the hidden settings for a new supplier at random, each from a range. The default ranges are written in the code, and calibrated ranges are stored in `ranges.json`. Drawing many suppliers gives a population that covers the kinds of behaviour the policy may meet.


## Step 3: Playing an episode

`env.py` plays one negotiation, called an episode. It takes a real case file, draws a supplier for it, lets the policy and the synthetic supplier exchange offers until one side ends it, and scores the result with the official cost formula. The case files come from `runs/cases/`, which the harvester fills.


## Step 4: Calibrating on real sessions

`calibrate.py` compares the simulator with reality. It reads our logged sandbox and practice sessions, measures how real suppliers behaved, for example how much they moved in their first reply and how often they held still, and adjusts the population ranges until the simulated suppliers behave the same way.

```bash
uv run python -m buyer.sim.calibrate
uv run python -m buyer.sim.calibrate --save
```

The first form only prints the result. The second also writes the new ranges to `ranges.json`.

`metrics.py` measures how well the simulator predicts real negotiations. It replays logged threads in the simulator and reports how far the simulated replies are from the real ones, and whether a parameter set that scores better in simulation also scores better in reality.

```bash
uv run python -m buyer.sim.metrics --sets sandbox practice
```


## Step 5: Tuning the policy

`train.py` searches for better policy parameters. It starts from the current `params.json`, tries a population of nearby parameter sets, keeps the best quarter, and repeats. Each candidate is scored over many episodes on the real case files.

```bash
uv run python -m buyer.sim.train --iters 15 --pop 32 --episodes 80
uv run python -m buyer.sim.train --save
```

The first form only prints the result. The second also writes the best parameters to `src/buyer/policy/params.json`. A new parameter set should still be checked on real practice cases before it is kept.
