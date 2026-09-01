# Source Prioritization

Source prioritization is a transparent operational ranking separate from the
forecast model. It aggregates observed packet metadata by candidate source
and considers measured activity signals such as packet rate, destination
diversity, and TCP flag activity when those fields are available.

The product calls results `Candidate Source` and `HIGH PRIORITY SOURCE`.
These labels indicate review priority only; they do not prove attacker
identity or replace analyst investigation. Observation timestamps and source
evidence are retained in the bounded runtime response.
