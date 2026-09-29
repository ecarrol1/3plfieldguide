# 3PL Field Guide

A standalone directory with 90 sourced provider profiles, four research categories and a buyer worksheet. No ads or promotional tracking.

Hosted staging: https://3plfieldguide.62.171.145.210.sslip.io/ (noindex). The selected custom domain is 3plfieldguide.com; registration and production activation remain pending.

## Preview

```sh
python3 build.py --test
python3 build.py
python3 -m http.server 8791 --bind 127.0.0.1 --directory dist
```

The default build is noindex, blocks crawlers and emits no canonical or sitemap. The home introduces the research and links qualifying categories. `/3pl-companies/` covers the overall inventory; ecommerce fulfillment, Amazon fulfillment and cold-chain logistics have separate buying questions and evidence-based subsets. A category publishes only when at least five records explicitly include its slug. This is an editorial threshold, not a search-engine rule. No service-text inference or automatic location combinations are generated. Filters sit above the cards and also update the optional comparison table. Counts and dates come from records.

## Production preparation

After selecting and approving the real HTTPS domain, pass it as `--site-url` to the generator. This explicitly enables indexing, self-canonicals, an XML sitemap containing only canonical content pages, crawler access and URL-based page/breadcrumb schema. The argument accepts only a domain root, without credentials, path, query, fragment or port. Do not pass a made-up domain to a deployable build.

In Coolify, use this directory as the Docker build context, choose Dockerfile, expose port 80, set the approved host and TLS, and provide the `SITE_URL` build argument. An empty build argument remains a preview. The Nginx configuration returns a real 404 for unknown routes; it does not fall back to the homepage. No Vercel services are used. The repository is deployed through the existing Coolify server; auto-deploy is disabled. Push reviewed changes to main, trigger this application in Coolify, and verify the deployed commit and public routes.

The schema repeats visible identities and descriptions, without ratings, guessed prices or invented directory ownership. Source mappings make field claims traceable; an editor must still verify their meaning. Unknown software, pricing and capacity remain unknown. Source records must contain nonfuture review/observation dates and supporting URLs. Duplicate official URLs fail for review.

The self-check covers invalid deployment URLs, evidence failures, future dates, script escaping and JSON round trips, preview/production directives, canonical sitemap membership and preserving the previous build on a rendering failure. Rendering and staging complete before replacing `dist`; replacement rolls back if the final move fails. Run one build at a time.

Before publishing, revalidate the dataset, confirm the brand and ownership/editorial disclosure, connect a real correction channel, and complete rendered desktop/mobile and container HTTP checks. Source freshness beyond the recorded dates and factual truth require editorial review. Technical eligibility does not establish rankings or AI citations. Google Fonts supplies optional typography.

The evaluation checklist supplies a native print/PDF action, checkboxes and a blank quote-comparison worksheet. Its examples come directly from sourced decision facts. The methodology page discloses automated research and its limits. Both pages enter the production sitemap and remain noindex in preview. Worksheet entries are not submitted or saved. The footer links GitHub Issues for corrections; submitting a correction requires a GitHub account.
