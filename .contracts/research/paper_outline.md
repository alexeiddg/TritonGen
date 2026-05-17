# TritonGen Working Paper Outline

## Current Results Scope

The current iteration analyzes a temporary 2² subset over G and C: none, G, C,
and G+C.

Current results should be described as 2² subset analysis over none/G/C/G+C.
P-containing cells are deferred for this iteration and are not included in
current paper-claiming outputs. This is a current-status scope statement, not a
methodology realignment.

## G Enforcement Method Paragraph

G consists of two enforcement layers. During generation, XGrammar applies
token-level masking against a context-free grammar defined in GBNF. After
generation, a semantic validator performs additional structural and surface
checks that the context-free grammar cannot express. A generation is counted as
G-accepting only if it passes both layers; rows that pass decoding but fail
semantic validation are recorded as grammar-rejected with explicit
failure-layer attribution.

Preferred short label: grammar-guided decoding plus offline semantic
post-validation.

## Planned Full Factorial Extension

The full 2³ factorial over G, C, and P remains the defined project goal.
Planned full-factorial completion adds the P-containing cells: P, G+P, C+P, and
G+C+P. Current 2² outputs must not be described as completion of the full
factorial.
