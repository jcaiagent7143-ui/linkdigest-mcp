# Privacy Policy

Last updated: September 5, 2026

This plugin connects a Dify workspace to the LinkDigest API at `https://linkdigest.dev`.

## Data transmitted

When the tool runs, it sends to `linkdigest.dev` over HTTPS:

- the URL supplied to the tool;
- the requested output format; and
- the LinkDigest API key supplied in the provider credential, as an `Authorization: Bearer` header.

Nothing else. The plugin does not read workflow variables it was not given, and it contacts no other host.

## Storage

The plugin persists nothing. Results are returned directly to the invoking workflow.

On the LinkDigest side, digests are cached for up to 30 days so a repeated link is served free; the media itself (video, images) is never stored or served. See https://linkdigest.dev/privacy for the service's own policy, including what it stores and who it shares data with.

## Third-party processing

Reading a post involves fetching it from its platform and running transcription and image models. That happens on LinkDigest's servers under its published terms. Do not submit links you are not permitted to process.

## Contact

apify@linkdigest.dev
