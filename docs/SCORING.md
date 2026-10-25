# How scoring works

The agent is judged on money and nothing else. This document explains how the arena turns a deal into a number, because every decision the agent makes is a bet on that number. The official definition is in section 6 of [the brief](../brief/brief.md), and the code that computes it is `total_cost` in `starter-kit/arena_kit/cost.py`. We call that code everywhere instead of writing our own version, so our view of a deal always matches the arena's.


## Step 1: The total cost of a deal

Each case describes a fixed need, such as 15,900 bearing brackets a year for one year. The arena asks what it would cost us, in euros, to cover that need under a given set of terms. The answer is called the total cost, or C.

The largest part of C is simply the price. It is the number of units we commit to buy multiplied by the unit price. Units bought before a new price takes effect are counted at the current price.

If the deal covers less than our need, for example because the contract is shorter than the planning horizon, the missing units are bought at the case's fallback price. On top of that, a fallback risk charge is added, and its size depends on the category goal of the case.

Payment terms matter as well. If we pay earlier than our reference payment period, we lose interest on the money, and that interest is added to C. If we pay later, C goes down.

Freight depends on the Incoterm. Some Incoterms leave the transport cost with us, so the arena adds a cost per unit for them.

Lead time is charged per day. If the supplier needs longer than we can wait, every extra day costs a fixed amount.

Quality is priced by expected defects. The arena multiplies the committed volume by the defect rate the supplier promises, in parts per million, and by the cost of each defect. Any chargeback the supplier agrees to pay per complaint reduces this cost.

Tooling costs and index clauses are added when they apply. An index clause ties the price to a market index such as copper, so the arena prices it along the index path published in the case. An extra index risk charge is added depending on the category goal.

The last part only applies to strategic and bottleneck cases. In those cases the arena charges us for every margin point a deal leaves the supplier below a sustainable margin. Squeezing a critical supplier too hard therefore costs money, even if the unit price looks good. Our costing module, `src/buyer/facts/costing.py`, estimates this charge from the supplier's profile.


## Step 2: Terms we leave out

A deal closes on the accepted term sheet. Any field the term sheet leaves out is filled from the supplier's standard terms, which are printed in the quote document attached to its first e-mail. The rest comes from the case's fixed terms.

This is why the agent always sends complete term sheets. A missing field could quietly close on a standard term that costs us more, such as a short payment period.


## Step 3: From cost to score

The score of a case compares our deal with two reference points. The first is C_open, the total cost of the best opening offer. The second is C_best, the lowest total cost the case allows. It is the cheaper of the best package any supplier would ever accept and our fallback option.

The score is the share of the possible saving that we captured.

```
score = (C_open - C_deal) / (C_open - C_best)
```

The result is clipped to the range from 0 to 1. A deal no better than the opening offer scores 0, and a deal at the best possible package scores 1.

There are three special cases. If the deal breaks one of the buyer's must-haves, the score is 0, whatever the price. If we end the case without a deal, we receive the score of our fallback option, which can be 0. If we abandon a case, it counts as no deal.


## Step 4: A worked example

The brief contains a short example. We need 4,000 parts a year for two years, our interest rate is 8 percent and our reference payment period is 60 days. The supplier opens at €43.20 with payment after 30 days. Over two years that is 8,000 parts, so the price part is €345,600, and paying 30 days early costs another €2,304 in interest. C_open is therefore €347,904.

We negotiate €41.60 with payment after 60 days, which gives a C of €332,800. The best package the supplier would ever accept turns out to be €40.80 at 90 days, which gives a C_best of €324,224.

Our score is (347,904 minus 332,800) divided by (347,904 minus 324,224), which is 0.64.


## Step 5: What this means for the agent

Three habits follow directly from the formula, and the agent is built around them.

First, the agent prices every offer, ours and the supplier's, with the full formula including the supplier's standard terms. It never compares unit prices alone.

Second, the agent trades levers. A longer payment period, a different Incoterm or a quality commitment can be worth more to us than a few cents of price, and sometimes it costs the supplier very little. Sending two or three term sheets that trade these levers against each other shows which ones the supplier values.

Third, the agent never accepts a deal that breaks a must-have or that costs more than our fallback. It checks both with `must_haves_ok` and `total_cost` before every acceptance.


## Step 6: How the final is scored

In the live final, each of the five waves is scored from 0 to 100. A wave's score is the average of its case scores multiplied by 100. The team's total is the sum of the five wave scores, so the maximum is 500. In the Counterpart dashboard, scores are shown on the same 0 to 100 scale.
