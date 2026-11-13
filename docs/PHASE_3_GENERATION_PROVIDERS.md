# Phase 3 — Image and video generation provider layer

The provider contract separates scene prompts and generation requests from
vendor-specific APIs. The default `mock` provider performs no network calls,
creates no media, and costs ₹0; it exists only to validate orchestration and UI
states.

A real image or video provider must have a separately implemented and tested
adapter for its exact API, including authentication, request/response schema,
asynchronous job polling, failure mapping, rate limits, output download,
content safety, and cost visibility. The current OpenAI-compatible image
adapter is an explicit placeholder and does not submit requests. Video APIs
are vendor-specific and are not guessed.

No provider key belongs in the browser or Git history. Real generation stays
disabled until the creator selects a provider and approves any associated
costs. All generated outputs require creator review before timeline insertion.
