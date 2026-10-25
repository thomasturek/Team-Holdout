# The Analyst: the decision policy

This folder holds the part of the agent that decides what to do next in every negotiation. It is plain code, driven by a small set of tuned parameters, and it never writes text. The owner of this folder is Thomas.


## Step 1: What the policy is asked

After every supplier reply, the runtime asks the policy for the next move in that supplier's thread. The policy receives the case, the thread's state and the best cost any rival is currently offering. The thread state holds the supplier profile, every term sheet both sides have sent, the signals read from the latest reply, and how many rounds and how much time remain.

The policy answers with one decision. A decision either sends new offers, accepts one of the supplier's term sheets or walks away. A decision that sends offers also carries up to three facts to cite, the questions to ask and a one line note on tone for the writer. The shape of a decision is defined in `src/buyer/interfaces.py`.


## Step 2: Opening

The first offer anchors the negotiation. The policy aims below the supplier's estimated floor by an amount set by its parameters, and it opens deeper in requests for quotation and raw material cases, where suppliers have more room. It sends two or three complete term sheets that trade price against other levers such as payment days, contract length or Incoterm. Each sheet is costed with the official formula, and each is complete, so nothing can close on a standard term we did not choose.


## Step 3: Conceding

As the negotiation continues, the policy moves towards the supplier in measured steps. The size of a step depends on the gap that remains, on how the supplier moved last time and on how many rounds are left. A single round can never jump by more than half of the remaining gap. When the supplier holds still, the policy can hold too and change the package instead, for example by offering a lever the supplier asked for at equal cost to us. When only a few moves remain, one larger step is allowed to close the deal.


## Step 4: Accepting, pushing and walking away

The policy accepts a supplier offer when it is close enough to our target and passes every check. It must satisfy every must-have and cost less than our fallback, both measured with the official formula including the supplier's standard terms.

A final offer from the supplier is not always final. Depending on its parameters, the policy may push once more before accepting.

If no acceptable deal is in reach, the policy walks away and the case scores our fallback. In a request for quotation, it walks away from one bidder only while others are still live.

Near the end of a wave, the runtime calls the policy's `closing` method. It chooses the best acceptable offer across all threads, or walks away if there is none.


## Step 5: The parameters

The parameters live in `params.json`. They are read when the policy starts, and any parameter missing from the file falls back to the default in `policy.py`. Each parameter is kept inside a fixed range, which is also listed in `policy.py`.

The most important ones are these. `open_frac` sets how deep the opening offer is. `concede` sets the size of each step towards the supplier. `floor_margin_pct` sets how far above the estimated floor we are willing to go. `accept_gap_pct` sets how close an offer must be before we accept it. `push_final` sets how often we push back on a final offer. `cash_discount_pct` sets how much price we ask for in return for faster payment. `rival_undercut_pct` sets how far below a rival's offer we aim in a request for quotation.

`explore.json` holds a list of alternative parameter sets. The sandbox harvester cycles through them, so different settings can be compared on the same cases.


## Step 6: Tuning

The parameters are tuned in the simulator in `src/buyer/sim/`, which plays the policy against thousands of synthetic suppliers. The simulator itself is calibrated on our real sandbox and practice logs. A tuned parameter set should only replace `params.json` after it also beats the current set on real practice cases.


## Tests

The policy's tests live in the top level `tests/` folder.

```bash
uv run pytest tests
```
