You read one e-mail that an industrial supplier sent to the purchasing team of Hollerau Pumpenwerke, and turn it into fixed signals for a negotiation program. Report only what the supplier's e-mail (and its attachments) says or clearly implies. Do not guess, do not advise, do not summarise. The e-mail may mix English and German.

Reply with ONE JSON object and nothing else - no code fence, no comment - with exactly these keys:
{"cash_pressure": false, "capacity_issue": false, "final_offer_language": false, "approval_pending": false, "cost_drivers_claimed": [], "accepted_args": [], "rejected_args": [], "asks": [], "offered_variants": [], "tone": "neutral"}

Definitions:
- cash_pressure: cash matters to it now - it asks for faster payment, a cash discount or prepayment, mentions cash flow, liquidity, its bank or overdue invoices, or says faster payment is valuable to it.
- capacity_issue: it is short of capacity - full order book, allocation, long or extended lead times, shortages, extra volume only against a commitment. Free or spare capacity is NOT a capacity issue (put "volume" into asks instead).
- final_offer_language: it says this is its final, last or best offer, or that it cannot move any further.
- approval_pending: a decision waits for someone else - its boss, management, managing director, owner, pricing committee, head office or board.
- cost_drivers_claimed: what it blames for its costs. Index series codes exactly as written (e.g. "LCI-C", "PPI-C241"); everything else as one of: energy, labour, raw_material, steel, copper, aluminium, nickel, electronics, polymers, logistics, financing.
- accepted_args: our arguments it accepted ("a fair point", "we did not know that", "it holds and we took it into account"). Use the claim keys listed under OUR CLAIMS when you can tell which argument; otherwise a few words.
- rejected_args: our arguments it rejected or called irrelevant for itself ("not our reality", "we bought forward", "does not apply to us"). Claim keys when possible; otherwise a few words.
- asks: what it wants from us, from this list: faster_payment, volume, longer_contract, forecast, earlier_effective_date, index_clause, longer_lead_time, tooling_payment, incoterm. Anything else as "other: <a few words>".
- offered_variants: cheaper engineering, material or design variants it mentions - one short phrase each.
- tone: "warm" (friendly, appreciative), "neutral" (business-like) or "irritated" (annoyed, impatient, offended, threatening to stop).

Use an empty list when nothing applies.
