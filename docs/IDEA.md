# Idea

## Strategy

- **Play every thread at once.** The starter kit plays RFQs one supplier at a time, and in the
  simulator a supplier left waiting times out every 60 s (three timeouts end the thread). Concurrent
  threads get more rounds inside the 8-minute wave cap.
- **Code finds the value gaps.** Terms that cost us little but matter to the supplier: earlier
  payment for a cash-short supplier, a longer contract (security, not cash).
- **The LLM only writes.** Numbers, term sheets and claims come from code.

## Questions for Tacto

1. In an RFQ, does a thread we aren't messaging time out every 60 s? Can we message all suppliers at once?
2. How long do supplier replies take in the final, with every team playing at once?
3. Are the hidden-case suppliers among the 46 in the data package, or completely new?
4. Does a longer contract or a volume commitment get us a lower price?

## Answers

## Demo script

## Scope
