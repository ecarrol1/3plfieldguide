#!/usr/bin/env python3
"""Build a local, noindex directory pilot from reviewed provider records."""
import html
import json
from pathlib import Path
import sys
import shutil
import re
import copy
import argparse
import tempfile
import os
import ipaddress
from datetime import date
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist"
CATEGORIES = {
    "3pl-companies": (
        "3PL companies", "Compare 3PL companies by what they handle.",
        "Third-party logistics providers handle work such as inventory storage, order fulfillment and distribution. Compare their published services against your sales channels and product requirements.",
        "Start with your order mix, product dimensions, retail requirements and returns workflow. Ask which facilities can perform the required work and which charges sit outside the quoted fulfillment fee.",
        "Includes organizations explicitly researched for third-party fulfillment or logistics services. A listing does not establish support for every product, location or channel. This is not a freight-rate comparison."
    ),
    "ecommerce-fulfillment": (
        "Ecommerce fulfillment companies", "Compare ecommerce fulfillment companies.",
        "Ecommerce fulfillment providers store inventory, pick and pack customer orders and arrange shipment. Compare published parcel-fulfillment services, returns handling and platform connections.",
        "Bring an order sample: items per order, parcel dimensions, destinations, seasonal peaks and return rates. Confirm order cutoffs, packaging charges, inventory synchronization and how exceptions reach your team.",
        "Includes providers explicitly classified from evidence of ecommerce fulfillment. General warehousing or freight transport alone does not qualify. A named platform connection is not proof of support for every edition or workflow."
    ),
    "amazon-fulfillment": (
        "Amazon fulfillment providers", "Compare Amazon prep and fulfillment providers.",
        "Amazon logistics services can mean FBA preparation, inventory replenishment or fulfillment of seller-fulfilled orders. Compare the provider's stated scope before treating these as interchangeable services.",
        "Specify FBA prep and inbound requirements, or seller-fulfilled order handling, before requesting a quote. Confirm labeling, cartons, shipment plans, returns and responsibility for compliance changes. Ask whether prep is standalone or limited to existing fulfillment clients.",
        "Includes providers explicitly researched for Amazon-related fulfillment or preparation. A marketplace integration alone does not qualify. Inclusion is not Amazon certification, an endorsement or a guarantee of seller-program eligibility."
    ),
    "cold-chain-logistics": (
        "Cold chain logistics companies", "Compare cold-chain logistics companies.",
        "Cold chain logistics providers handle temperature-sensitive storage, transport or fulfillment. Compare the published service scope, then verify temperatures, product restrictions and facility coverage for your shipment.",
        "Provide the required temperature band, product type, lane and storage duration. Ask about monitoring, excursion handling, packaging validation and responsibility at each handoff. Confirm capabilities at the exact facility and route rather than assuming company-wide coverage.",
        "Includes providers explicitly researched for temperature-controlled logistics. Standard ambient storage does not qualify. A cold-chain claim does not by itself establish pharmaceutical qualification, food certification or a particular temperature band."
    )
}


def published_categories(providers):
    return {slug: [p for p in providers if slug in p["categories"]] for slug in CATEGORIES if sum(slug in p["categories"] for p in providers) >= 5}


E = html.escape
CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap');
:root{--paper:#f4f1e8;--ink:#183d33;--muted:#53625a;--line:#d2d8c9;--lime:#d6e78b}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 'DM Sans',sans-serif}
a{color:inherit;text-underline-offset:4px}a:hover{color:#607828}button,input,select{font:inherit}button,a,input,select{touch-action:manipulation}
:focus-visible{outline:3px solid #a06120;outline-offset:4px}h1,h2,h3,p{margin:0}h1,h2,h3{font-weight:400}h1,h2,.serif{font-family:'Newsreader',Georgia,serif}
.wrap{max-width:1320px;margin:auto;padding:0 52px}.skip{position:absolute;top:-80px;background:white;padding:12px;z-index:10}.skip:focus{top:0}
.preview{background:#dfe6d2;border-bottom:1px solid #c8d2bb;padding:8px 24px;text-align:center;font-size:12px;letter-spacing:.03em}
header{padding:28px 0;border-bottom:1px solid var(--line)}.head{display:flex;align-items:center;justify-content:space-between;gap:24px}.brand{text-decoration:none;font-family:'Newsreader',Georgia,serif;font-size:28px;line-height:1.1}.brand span{display:block;font:10px/1.5 'DM Sans',sans-serif;text-transform:uppercase;letter-spacing:.17em;margin-top:8px}.head nav{display:flex;gap:28px;font-size:13px}.head nav a{text-decoration:none}
.hero{display:grid;grid-template-columns:1fr .43fr;gap:80px;padding:65px 0 54px;align-items:end}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.15em;font-weight:600;margin-bottom:19px}.hero h1{font-size:clamp(42px,5.3vw,76px);line-height:.99;letter-spacing:-.04em;max-width:800px}.hero h1 em{font-weight:400;color:#637642}.hero p{font-size:15px;max-width:380px}.hero-note{border-top:1px solid var(--ink);padding-top:18px;margin-top:23px;color:var(--muted);font-size:12px}
.button{display:inline-block;padding:12px 18px;background:var(--lime);color:var(--ink);font-size:13px;text-decoration:none;white-space:nowrap;border:1px solid transparent}.button:hover{background:#e6f4ab;color:var(--ink)}
.comparison{overflow-x:auto;margin:30px 0}.comparison table{border-collapse:collapse;width:100%;min-width:700px;font-size:13px}.comparison th,.comparison td{text-align:left;vertical-align:top;padding:15px;border-bottom:1px solid var(--line)}.comparison th{font-size:11px}.comparison caption{text-align:left;font-size:24px;margin-bottom:15px}.comparison td small{display:block;margin-top:8px}.category-nav{display:flex;flex-wrap:wrap;gap:25px;padding:22px 0 0;font-size:13px}.category-nav a{text-decoration:none;border-bottom:1px solid var(--ink);padding-bottom:4px}.catalog{padding:49px 0 64px}.section-head{display:flex;align-items:baseline;justify-content:space-between;gap:20px;margin-bottom:24px}.section-head h2{font-size:36px;letter-spacing:-.02em}.section-head p{font-size:12px;color:var(--muted)}.filters{display:grid;grid-template-columns:1.3fr 1fr 1fr auto;gap:15px;margin-bottom:25px;padding-bottom:24px;border-bottom:1px solid var(--line)}label{display:block;font-size:11px;margin-bottom:7px;font-weight:600}input,select{width:100%;height:46px;border:1px solid #afbaaa;border-radius:0;background:transparent;color:var(--ink);padding:9px 12px;min-width:0}input::placeholder{color:#68766b}.reset{align-self:end;background:none;height:46px;border:0;text-decoration:underline;font-size:12px;cursor:pointer;color:var(--ink);padding:0 10px}.results{font-size:12px;margin-bottom:18px;color:var(--muted)}
.provider{display:grid;grid-template-columns:.55fr 1fr .65fr;gap:36px;padding:29px 0;border-top:1px solid var(--line);align-items:start}.provider[hidden]{display:none}.provider-name{font-family:'Newsreader',Georgia,serif;font-size:28px;line-height:1.15;text-decoration:none}.provider-index{display:block;font-size:10px;letter-spacing:.08em;color:#737f71;margin-bottom:9px}.provider p{font-size:13px;line-height:1.65}.tags{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}.tag{font-size:10px;border:1px solid #c9d1bf;padding:2px 7px;color:#42523d}.provider-link{font-size:12px;display:inline-block;margin-top:13px}.meta{font-size:11px;color:var(--muted)}.meta b{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--ink);margin-bottom:5px;font-weight:600}.meta p{font-size:12px}.flag{font-size:10px;color:#795118;background:#e9dfc9;padding:3px 7px;display:inline-block;margin-top:12px}.empty{padding:40px;border:1px solid var(--line);font-size:15px}
.method{border-top:1px solid var(--ink);padding:35px 0 45px;display:grid;grid-template-columns:1fr 2fr;gap:50px}.method h2{font-size:32px}.method p{font-size:13px;max-width:770px}.method p+p{margin-top:12px}
footer{border-top:1px solid var(--line);padding:28px 0 35px;font-size:11px;color:var(--muted)}.foot{display:flex;justify-content:space-between;gap:30px}.crumb{font-size:12px;margin-top:32px}.detail-hero{padding:35px 0 45px;max-width:880px}.detail-hero h1{font-size:64px;line-height:1.08;letter-spacing:-.04em;margin-bottom:22px}.detail-hero>p{font-size:19px}.detail-grid{display:grid;grid-template-columns:1.65fr 1fr;gap:60px;margin-bottom:50px}.facts{display:grid;grid-template-columns:1fr 1fr;gap:28px 35px}.fact{border-top:1px solid var(--line);padding-top:16px}.fact h2{font:11px 'DM Sans',sans-serif;text-transform:uppercase;letter-spacing:.1em;margin-bottom:13px}.fact p,.fact li{font-size:14px}.fact ul{padding-left:18px;margin:0}.source-box{padding:25px;border:1px solid #b9c5ae}.source-box h2{font-size:28px;margin-bottom:14px}.source-box p,.source-box li{font-size:12px}.source-box ul{padding-left:17px}.source-box a{overflow-wrap:anywhere}.source-box .button{margin-top:18px}.note{border-left:3px solid #aa7936;padding-left:15px;font-size:12px;margin:22px 0}
.worksheet{max-width:1000px}.worksheet-section{border-top:1px solid var(--line);padding:28px 0}.worksheet-section h2{font-size:30px;margin-bottom:15px}.worksheet-section h3{font:600 15px/1.4 'DM Sans',sans-serif;margin-bottom:10px}.worksheet-section p+p{margin-top:14px}.check{display:flex;gap:12px;align-items:flex-start;font-size:14px;font-weight:400;margin:15px 0}.check input{width:18px;height:18px;flex:0 0 18px;margin-top:3px}.blank-sheet td{height:58px;min-width:130px}.blank-sheet th{width:26%}@media print{body{background:white;color:black;font-size:11pt}.wrap{max-width:none;padding:0}header,footer,.preview,.skip,.no-print{display:none!important}.worksheet{max-width:none}.detail-hero{padding:10px 0 20px}.detail-hero h1{font-size:32pt}.worksheet-section{padding:15px 0}.worksheet-section h2{font-size:19pt;break-after:avoid}.check,.fact,tr{break-inside:avoid}.facts{display:block}.fact{margin:12px 0}.comparison{overflow:visible}.comparison table{min-width:0;font-size:9pt}.blank-sheet td{min-width:0;height:48px}a{color:black}.worksheet .meta{font-size:9pt}main{animation:none!important}}
@media(prefers-reduced-motion:no-preference){main{animation:arrive .45s ease-out}@keyframes arrive{from{opacity:.4;transform:translateY(8px)}to{opacity:1;transform:none}}}
@media(max-width:800px){.wrap{padding:0 25px}.hero{grid-template-columns:1fr;gap:25px;padding:44px 0 34px}.hero p{max-width:600px}.hero-note{margin-top:16px}.head nav{gap:15px}.filters{grid-template-columns:1fr 1fr}.filters>div:first-child{grid-column:1/-1}.reset{text-align:left}.provider{grid-template-columns:1fr 1.7fr;gap:20px}.provider .meta{grid-column:2}.method{gap:25px;grid-template-columns:1fr}.detail-grid{grid-template-columns:1fr;gap:30px}.detail-hero h1{font-size:48px}}
@media(max-width:500px){.wrap{padding:0 20px}header{padding:22px 0}.brand{font-size:23px}.head nav{font-size:11px;gap:14px}.head{flex-wrap:wrap}.head nav a:first-child{display:inline}.hero h1{font-size:47px}.section-head{display:block}.section-head p{margin-top:7px}.section-head h2{font-size:32px}.filters{gap:13px}.filters label{font-size:10px}.filters select{font-size:12px;padding:8px}.provider{grid-template-columns:1fr;gap:14px}.provider .meta{grid-column:1}.provider-name{font-size:29px}.provider-index{display:inline;margin-right:10px}.provider .meta b{margin-top:3px}.foot{display:block}.foot p+p{margin-top:12px}.facts{grid-template-columns:1fr}.detail-hero>p{font-size:17px}.preview{font-size:10px}.catalog{padding-top:35px}}
"""


def site_root(value):
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.port
            or not re.fullmatch(r"[a-zA-Z0-9.-]+", parsed.hostname)
            or "." not in parsed.hostname or parsed.hostname.endswith(".")
            or any(not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?", label) for label in parsed.hostname.split("."))):
        raise ValueError("--site-url must be an HTTPS domain root with no path, port, credentials, query or fragment")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise ValueError("Use a domain, not an IP address")
    return "https://" + parsed.hostname.lower()


def page(title, content, description, path="/", site_url=None, entity=None, collection=False, parent_category="3pl-companies"):
    directives = "index,follow" if site_url else "noindex,nofollow"
    canonical = f'<link rel="canonical" href="{E(site_url + path)}">' if site_url else ''
    banner = '' if site_url else '<div class="preview">Local research preview · Provisional name · Not published</div>'
    if site_url:
        crumbs = [("Home", "/")]
        if path in ("/methodology/", "/3pl-evaluation-checklist/"):
            crumbs.append((title, path))
        elif path != "/":
            crumbs.append((CATEGORIES[parent_category][0], f"/{parent_category}/"))
        if path.startswith("/providers/"):
            crumbs.append((title, path))
        schema = {"@context":"https://schema.org", "@type":"CollectionPage" if collection else "WebPage", "@id":site_url+path+"#page", "url":site_url+path, "name":title, "description":description, "breadcrumb":{"@type":"BreadcrumbList", "itemListElement":[{"@type":"ListItem", "position":i, "name":name, "item":site_url+route} for i,(name,route) in enumerate(crumbs,1)]}}
        if entity:
            schema["mainEntity"] = entity
        content += jsonld(schema)
    elif entity:
        content += jsonld({"@context":"https://schema.org", **entity})
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="{directives}">{canonical}<meta name="description" content="{E(description)}"><title>{E(title)} | 3PL Field Guide</title><style>{CSS}</style></head><body><a class="skip" href="#main">Skip to content</a>{banner}<div class="wrap"><header><div class="head"><a href="/" class="brand">3PL Field Guide<span>Fulfillment research for operators</span></a><nav aria-label="Main navigation"><a href="/3pl-companies/">Browse providers</a><a href="/3pl-evaluation-checklist/">Buyer checklist</a><a href="/methodology/">Methodology</a></nav></div></header><main id="main">{content}</main><footer><div class="foot"><p>3PL Field Guide</p><p><a href="/methodology/">Research methodology</a> · <a href="/3pl-evaluation-checklist/">Evaluation worksheet</a></p></div></footer></div></body></html>'''


def landing(providers, site_url=None):
    description = "Research third-party logistics providers using published services, source-linked facts and explicit unknowns."
    categories = published_categories(providers)
    browse = ''.join(f'<section class="method"><h2><a href="/{slug}/">{E(CATEGORIES[slug][0])}</a></h2><div><p>{E(CATEGORIES[slug][2])}</p><p class="meta">{len(members)} researched providers</p><p><a class="button" href="/{slug}/">Compare providers →</a></p></div></section>' for slug,members in categories.items())
    preview_note = '<p>The directory name is provisional. A correction submission channel has not yet been connected.</p>' if not site_url else ''
    content = f'''<section class="hero"><div><div class="eyebrow">Fulfillment research</div><h1>Know what to ask before the quote.</h1></div><div><p>{description}</p><div class="hero-note">{len(providers)} researched providers. Records reviewed from {E(min(p["read_date"] for p in providers))} to {E(max(p["read_date"] for p in providers))}.</div></div></section>{browse}<section class="method" id="about"><h2>How we research.</h2><div><p>We read official provider pages and attach sources and observation dates to the facts used in comparisons. Providers appear alphabetically. We do not assign ratings or independently certify their claims.</p><p>Unknown pricing, capacity and service details stay unknown. Coverage reflects the researched records and is not a complete market census. Confirm the requirements and commercial terms for your own operation directly with the provider.</p>{preview_note}</div></section>'''
    return page("Fulfillment research", content, description, site_url=site_url)


def checklist(providers, site_url=None):
    examples = []
    for provider_id, label, question in [
        ("shipbob", "API constraint", "Can this integration handle the retailer's compliance workflow?"),
        ("fulfillrite", "Minimum charges", "What is excluded from the minimum charge?"),
        ("red-stag-fulfillment", "Product fit", "Does the product category include our exact SKU?"),
        ("stord", "Network distinction", "Who operates the facility that will hold our stock?")
    ]:
        provider = next((p for p in providers if p["id"] == provider_id), None)
        fact = next((f for f in provider["decision_facts"] if f["label"].casefold() == label.casefold()), None) if provider else None
        if fact:
            examples.append(f'<div class="fact"><h3>{E(question)}</h3><p><a href="/providers/{E(provider_id)}/">{E(provider["name"])}</a>: {E(fact["value"])}</p><p class="meta">{evidence(fact)}</p></div>')
    sections = [
        ("1. Define the shipment", ["Provide SKU dimensions, weights, storage conditions, shelf life and any handling restrictions.", "Provide monthly orders, items per order, peak-day volume and destination mix. Separate parcel, pallet, wholesale, marketplace and direct-to-consumer flows.", "Name the required launch date and the inventory-transfer constraints. Ask what is confirmed versus still subject to capacity approval."]),
        ("2. Confirm the service at the facility", ["Identify the actual proposed facilities and which are owned, leased or operated by a partner.", "For temperature-sensitive goods, specify the temperature band, monitoring, excursion handling and transfer responsibility.", "Request written exclusions for products, destinations and activities. Ask for evidence tied to the proposed facility when a credential or specialist capability matters."]),
        ("3. Test the order workflow", ["Name your storefront, ERP, order-management system and retailer requirements. Confirm the supported version and data exchanged, rather than relying on a logo.", "For Amazon, distinguish FBA prep and replenishment from seller-fulfilled orders. Ask whether prep requires an existing fulfillment account.", "Walk through an ordinary order, cancellation, out-of-stock exception, return and retail-compliant shipment. Identify who owns each failure and how it is escalated."]),
        ("4. Make quotes comparable", ["Give every provider the same order and inventory assumptions. Ask for a line-item quote covering receiving, storage, picks, packaging, postage, minimums, account fees, integrations, returns and extra work.", "Ask what the minimum covers, which fees count toward it, and which are additional. A minimum is not a total monthly cost.", "Request the same normal-volume and peak-volume scenarios. Record quote validity, annual increases, contract term and inventory-removal charges."]),
        ("5. Agree the operating terms", ["Document receiving lead times, order cutoffs, dispatch commitments, inventory accuracy definitions and peak exceptions.", "Ask how service failures are measured, disputed and credited. A marketing guarantee is not the executed agreement.", "Confirm the support owner, escalation path, reporting cadence, implementation milestones and exit plan before signing."])
    ]
    checks = ''.join('<section class="worksheet-section"><h2>'+E(title)+'</h2>'+''.join(f'<label class="check"><input type="checkbox"> <span>{E(text)}</span></label>' for text in tasks)+'</section>' for title,tasks in sections)
    worksheet_rows = ''.join(f'<tr><th scope="row">{E(label)}</th><td></td><td></td><td></td></tr>' for label in ["Provider / contact", "Proposed facility", "Required service confirmed", "Product exclusions", "Integration test result", "Normal-month quote / scope", "Peak-month quote / scope", "Minimum and extra charges", "Launch date confirmed", "Open questions / evidence needed", "Decision / next action"])
    description = "A printable 3PL evaluation checklist and quote-comparison worksheet for fulfillment buyers, with sourced examples of operating constraints."
    content = f'''<article class="worksheet"><section class="detail-hero"><div class="eyebrow">Buyer worksheet · 3PL Field Guide editorial project</div><h1>Ask for a comparable answer.</h1><p>Use this checklist to prepare one brief for every shortlisted 3PL. Write down confirmed facts, unresolved questions and quote assumptions before comparing prices.</p><p class="meta">Examples drawn from records reviewed through {E(max(p["read_date"] for p in providers))}. The checklist is editorial guidance; provider examples are published claims.</p><p class="no-print" style="margin-top:20px"><button class="button" type="button" onclick="window.print()">Print or save as PDF</button></p><p class="meta no-print">Tick boxes in this browser, or print a blank copy. Entries are not submitted or saved by this page.</p></section>{checks}<section class="worksheet-section"><h2>Why the details matter</h2><div class="facts">{''.join(examples)}</div></section><section class="worksheet-section"><h2>Compare the same scope</h2><p>Use one column per provider. Leave an answer unconfirmed until the provider supplies the requested evidence or written term.</p><div class="comparison"><table class="blank-sheet"><caption>Shortlist worksheet</caption><thead><tr><th scope="col">Decision field</th><th scope="col">Provider A</th><th scope="col">Provider B</th><th scope="col">Provider C</th></tr></thead><tbody>{worksheet_rows}</tbody></table></div></section><p class="no-print"><a href="/3pl-companies/">Return to the provider comparison →</a></p></article>'''
    return page("3PL evaluation checklist", content, description, path="/3pl-evaluation-checklist/", site_url=site_url)


def methodology(providers, site_url=None):
    description = "How 3PL Field Guide collects provider evidence, handles unknowns and builds comparisons without ratings or independent performance claims."
    content = f'''<article class="worksheet"><section class="detail-hero"><div class="eyebrow">3PL Field Guide editorial project</div><h1>What a listing establishes.</h1><p>A listing records what a provider publishes about its services. It does not establish that we have used, tested or endorsed that provider.</p></section><section class="worksheet-section"><h2>Who maintains the research</h2><p>This directory is maintained as the 3PL Field Guide editorial project. This edition was assembled with automated research and source-based extraction. It is not presented as a panel of logistics experts, an independent facility audit or a collection of customer reviews.</p></section><section class="worksheet-section"><h2>Sources and observations</h2><p>We use official provider pages and documentation for identity, services, audiences, integrations and operating constraints. Decision facts carry a source URL and observation date. An observation date records when the source was reviewed; it does not establish when the provider last changed the claim.</p><p>Current coverage includes {len(providers)} organizations, with records reviewed from {E(min(p["read_date"] for p in providers))} through {E(max(p["read_date"] for p in providers))}. The directory is not a complete market census. Published performance claims have not been independently tested or validated through provider interviews.</p></section><section class="worksheet-section"><h2>Inclusion and ordering</h2><p>Providers qualify for a category through an explicit research classification supported by source pages. Ecommerce fulfillment, Amazon preparation and cold-chain logistics describe different requirements; a general logistics label does not establish all of them.</p><p>Each published category currently requires at least five researched alternatives and its own buyer guidance. This is an editorial publication rule, not a search-engine requirement. Providers are listed alphabetically, without star ratings or paid rankings.</p></section><section class="worksheet-section"><h2>What remains unknown</h2><p>Missing prices, current capacity, start dates and unsupported integrations remain unconfirmed. We do not infer a facility's capability from a company-wide claim, a certification from a logo, or retailer compliance from the presence of an API.</p><p>A published minimum is shown with its scope and source. It is not substituted for a complete fulfillment quote. Buyers should confirm current terms directly with providers using the <a href="/3pl-evaluation-checklist/">evaluation worksheet</a>.</p></section><section class="worksheet-section"><h2>Updates and corrections</h2><p>Sources can change after observation. Automated validation detects missing evidence references, malformed dates and some inconsistent values; it cannot prove the underlying service claim. Changes need source review before they can become directory facts.</p><p>A public correction intake is not available in this edition. No submission form or monitored address is implied. Consult the linked official source and confirm discrepancies with the provider before relying on a listing.</p></section></article>'''
    return page("Research methodology", content, description, path="/methodology/", site_url=site_url)


def list_items(values):
    return "<ul>" + "".join(f"<li>{E(v)}</li>" for v in values) + "</ul>" if values else "<p>Not confirmed in reviewed sources.</p>"


def jsonld(value):
    return '<script type="application/ld+json">' + json.dumps(value, ensure_ascii=False).replace('<', r'\u003c') + '</script>'


def organization(p):
    return {"@type": "Organization", "name": p["name"], "url": p["website"], "description": p["description"]}


def evidence(fact):
    return f'<small><a href="{E(fact["source_url"])}">Source</a> · Observed {E(fact["observed_on"])} · {E(fact["evidence_type"])}</small>'


def decision_facts(p):
    return ''.join(f'<div class="fact"><h2>{E(f["label"])}</h2><p>{E(f["value"])}</p><p class="meta">{evidence(f)}</p></div>' for f in p["decision_facts"])


def field_sources(p, field):
    return ' · '.join(f'<a href="{E(u)}">Source</a>' for u in p["evidence_by_field"].get(field, []))


def pricing(p):
    price = f'<p>{E(p["public_pricing"])}</p>' if p["public_pricing"] else ''
    references = set(p["evidence_by_field"].get("public_pricing", []))
    facts = [f for f in p["decision_facts"] if any(word in f["label"].lower() for word in ("minimum", "pricing", "price", "charge"))]
    references.update(f["source_url"] for f in facts)
    sources = ' · '.join(f'<a href="{E(u)}">Pricing source</a>' for u in sorted(references))
    return price + f'<p>{E(p["pricing_note"])}</p>' + (f'<small>{sources} · Reviewed {E(p["read_date"])}</small>' if sources else '')


def comparison(providers):
    rows = []
    for p in providers:
        cells = ''.join('<td>'+list_items(p[field])+f'<small>{field_sources(p, field)}'+(f' · Reviewed {E(p["read_date"])}' if p[field] else '')+'</small></td>' for field in ["services", "audience", "software"])
        rows.append(f'<tr data-provider="{E(p["id"])}"><th scope="row"><a href="/providers/{E(p["id"])}/">{E(p["name"])}</a></th>{cells}<td>{pricing(p)}</td></tr>')
    return '<div class="comparison" tabindex="0" role="region" aria-label="Provider comparison, scroll horizontally on smaller screens"><table><caption>Published services, audiences and integrations</caption><thead><tr><th scope="col">Provider</th><th scope="col">Services</th><th scope="col">Stated audience</th><th scope="col">Named software or integrations</th><th scope="col">Pricing</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def details(p, site_url=None, categories=None):
    categories = categories or {"3pl-companies": []}
    qualifying = [slug for slug in categories if slug in p["categories"]]
    parent_category = qualifying[0] if qualifying else "3pl-companies"
    category_links = '<nav class="category-nav" aria-label="Related categories">'+''.join(f'<a href="/{slug}/">{E(CATEGORIES[slug][0])}</a>' for slug in qualifying)+'</nav>'
    sources = ''.join(f'<li><a href="{E(u)}">{E(urlparse(u).netloc + urlparse(u).path)}</a></li>' for u in p["source_urls"])
    filter_facts = ''.join(f'<div class="fact"><h2>{E(field.replace("_", " "))}</h2>{list_items(p[field]) if isinstance(p[field],list) else "<p>"+E(p[field])+"</p>"}<p class="meta">'+ ' · '.join(f'<a href="{E(u)}">Source</a>' for u in p["evidence_by_field"][field])+f' · Reviewed {E(p["read_date"])}</p></div>' for field in ["services","audience","delivery_model"] + (["software"] if p["software"] else []))
    note = f'<p class="note">{E(p["review_note"])}</p>' if p.get("review_note") else ''
    content = f'''<p class="crumb"><a href="/{parent_category}/">← {E(CATEGORIES[parent_category][0])}</a></p><section class="detail-hero"><div class="eyebrow">Provider profile · Reviewed {E(p["read_date"])}</div><h1>{E(p["name"])}</h1><p>{E(p["description"])}</p>{note}{category_links}</section><div class="detail-grid"><section class="facts" aria-label="Sourced decision facts">{decision_facts(p)}{filter_facts}<div class="fact"><h2>Pricing and availability</h2>{pricing(p)}<p>Current capacity and onboarding dates are not confirmed. Ask the provider directly.</p></div></section><aside class="source-box"><h2>Read the evidence.</h2><p>Claims below are reported by the provider, not independently tested. Source dates show when the pages were reviewed.</p><ul>{sources}</ul><p>{E(p["evidence_access"])}</p><a class="button" href="{E(p["website"])}">Visit {E(p["name"])} ↗</a></aside></div><section class="method" id="about"><h2>Before you request a quote.</h2><div><p>Confirm the exact product-handling requirements, order profile, retailer requirements, facility coverage and minimum charges for your account. Published services do not establish available capacity or a contractual service level.</p><p>No ratings or performance rankings are assigned. <a href="/3pl-companies/">Compare the other researched providers.</a></p></div></section>'''
    return page(p["name"], content, p["description"], path=f'/providers/{p["id"]}/', site_url=site_url, entity=organization(p), parent_category=parent_category)


def home(providers, category="3pl-companies", site_url=None):
    heading = CATEGORIES[category][1]
    description = CATEGORIES[category][2]
    buying_note = '<details style="margin-bottom:30px"><summary style="cursor:pointer">Compare services and integrations in a table</summary>'+comparison(providers)+'</details>'
    category_nav = '<nav class="category-nav" aria-label="Provider categories"><a href="/">All research categories</a><a href="#directory">Browse providers below</a></nav>'
    services = sorted({v for p in providers for v in p["services"]})
    audiences = sorted({v for p in providers for v in p["audience"]})
    def options(values):
        return "".join(f'<option value="{E(v)}">{E(v)}</option>' for v in values)
    cards = []
    for index, p in enumerate(providers, 1):
        flag = ""
        search = " ".join([p["name"], p["description"], *p["services"], *p["audience"], *(p["software"] or [])]).lower()
        cards.append(f'''<article class="provider" data-provider="{E(p["id"])}" data-search="{E(search)}" data-services="{E(json.dumps(p["services"]))}" data-audiences="{E(json.dumps(p["audience"]))}"><div><span class="provider-index">{index:02d} / PROVIDER</span><a class="provider-name" href="/providers/{E(p["id"])}/">{E(p["name"])}</a>{flag}</div><div><p>{E(p["description"])}</p><div class="tags">{"".join(f'<span class="tag">{E(s)}</span>' for s in p["services"][:3])}</div><a class="provider-link" href="/providers/{E(p["id"])}/">View profile &amp; sources →</a></div><div class="meta"><b>Engagement</b><p>{E(p["delivery_model"])}</p><b style="margin-top:12px">Stated audience</b><p>{E(" · ".join(p["audience"][:2]))}</p></div></article>''')
    script = """<script>
const search=document.getElementById('search'),service=document.getElementById('service'),audience=document.getElementById('audience'),rows=[...document.querySelectorAll('.provider')];
function filter(){const words=search.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);let count=0;for(const row of rows){const show=words.every(word=>row.dataset.search.includes(word))&&(!service.value||JSON.parse(row.dataset.services).includes(service.value))&&(!audience.value||JSON.parse(row.dataset.audiences).includes(audience.value));row.hidden=!show;document.querySelector('tr[data-provider="'+row.dataset.provider+'"]').hidden=!show;if(show)count++}document.getElementById('count').textContent=count+' of '+rows.length+' providers';document.getElementById('empty').hidden=count!==0}
search.addEventListener('input',filter);service.addEventListener('change',filter);audience.addEventListener('change',filter);document.getElementById('reset').addEventListener('click',()=>{search.value='';service.value='';audience.value='';filter();search.focus()});
</script>"""
    content = f'''<section class="hero"><div><div class="eyebrow">{E(CATEGORIES[category][0])}</div><h1>{E(heading)}</h1><p class="meta" style="margin-top:18px">Reviewed {E(max(p["read_date"] for p in providers))}</p></div><div><p>{E(description)}</p><div class="hero-note">Research built from official provider pages. Every profile includes its sources.</div></div></section>{category_nav}<section class="method" style="margin-top:30px"><h2>Define the requirement.</h2><div><p>{E(CATEGORIES[category][3])}</p><p>{E(CATEGORIES[category][4])}</p></div></section><section class="catalog" id="directory"><div class="section-head"><h2>The provider index</h2><p>Alphabetical order · No paid rankings</p></div><div class="filters" role="search" aria-label="Filter providers"><div><label for="search">Search by provider, service or software</label><input id="search" type="search" placeholder="Try retail, fulfillment or returns" autocomplete="off"></div><div><label for="service">Service needed</label><select id="service"><option value="">All services</option>{options(services)}</select></div><div><label for="audience">Who they serve</label><select id="audience"><option value="">All audiences</option>{options(audiences)}</select></div><button class="reset" id="reset" type="button">Reset filters</button></div><p class="results" id="count" role="status" aria-live="polite">{len(providers)} of {len(providers)} providers</p>{buying_note}<noscript><p>Search and filters need JavaScript. All providers remain listed below.</p></noscript>{"".join(cards)}<p class="empty" id="empty" hidden>No providers match these filters. Try a broader service or reset the filters.</p></section><section class="method" id="about"><h2>Sources over scores.</h2><div><p>We read providers' own pages and record their services, audiences, delivery models and named software. Missing information stays unknown. Listings are alphabetized, not rated; a listing does not mean we have used or endorsed the provider.</p><p>Named software does not establish support for every version or workflow. Confirm integration details with the provider.</p><p>Records reviewed from {E(min(p["read_date"] for p in providers))} to {E(max(p["read_date"] for p in providers))}. Inclusion follows the service scope stated above and recorded evidence. Coverage is limited to {len(providers)} researched organizations, not the whole market. Provider claims have not been independently tested.</p></div></section>{script}'''
    entity = {"@type":"ItemList", "numberOfItems":len(providers), "itemListElement":[{"@type":"ListItem", "position":i, **({"url":site_url+f'/providers/{p["id"]}/'} if site_url else {}), "item":organization(p)} for i,p in enumerate(providers,1)]}
    return page(CATEGORIES[category][0], content, description, path=f"/{category}/", site_url=site_url, entity=entity, collection=True, parent_category=category)


def validate(providers):
    assert providers and len({p["id"] for p in providers}) == len(providers)
    assert len({p["website"].rstrip("/").lower() for p in providers}) == len(providers), "Duplicate official website requires review"
    for p in providers:
        assert p["id"] and all(c.isalnum() or c == "-" for c in p["id"])
        assert p["description"] and p["name"]
        for url in [p["website"], *p["source_urls"]]:
            parsed = urlparse(url)
            assert parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password and not any(c.isspace() for c in url)
        assert p["services"] and p["audience"] and p["read_date"]
        assert p["categories"] and set(p["categories"]) <= set(CATEGORIES), "Unknown category requires an editorial template"
        assert "3pl-companies" in p["categories"], "Current directory requires core logistics qualification"
        for category in set(p["categories"]) - {"3pl-companies"}:
            support = p.get("category_evidence", {}).get(category)
            assert support and support.get("supporting_fact"), f"Missing category evidence: {p['id']} / {category}"
            assert support["source_url"] in p["source_urls"], "Category source was not reviewed"
            sourced_fact = any(f["value"] == support["supporting_fact"] and f["source_url"] == support["source_url"] for f in p["decision_facts"])
            sourced_service = support["supporting_fact"] in p["services"] and support["source_url"] in p["evidence_by_field"].get("services", [])
            assert sourced_fact or sourced_service, f"Category evidence does not match a sourced visible field: {p['id']}"
            assert E(support["supporting_fact"]) in details(p), "Category qualification must be visible on the profile"
        for field in ["description", "services", "audience", "delivery_model", "categories"] + (["software"] if p["software"] else []):
            assert p["evidence_by_field"].get(field), f"No supporting source for {field}"
            assert all(u in p["source_urls"] for u in p["evidence_by_field"][field])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["read_date"]), "Missing or malformed review date"
        assert date.fromisoformat(p["read_date"]) <= date.today(), "Future review date"
        if p["public_pricing"] is not None:
            assert isinstance(p["public_pricing"], str) and p["public_pricing"].strip(), "Pricing must be a scoped sourced string or null"
            assert p["evidence_by_field"].get("public_pricing"), "Published price needs supporting sources"
            assert all(u in p["source_urls"] for u in p["evidence_by_field"]["public_pricing"])
            priced_facts = [f for f in p["decision_facts"] if any(word in f["label"].lower() for word in ("minimum", "pricing", "price", "charge"))]
            assert priced_facts, "Published price needs a scoped decision fact"
            # ponytail: currency-token parity catches changed amounts; scope still needs editorial review.
            assert set(re.findall(r"\$[\d,.]+", p["public_pricing"])) <= set(re.findall(r"\$[\d,.]+", " ".join(f["value"] for f in priced_facts))), "Price differs from supporting facts"
        assert len(p["decision_facts"]) >= 2
        for f in p["decision_facts"]:
            assert f["label"] and f["value"] and f["evidence_type"]
            assert f["source_url"] in p["source_urls"], "Decision fact source missing from reviewed sources"
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["observed_on"]), "Missing or malformed observation date"
            assert date.fromisoformat(f["observed_on"]) <= date.today(), "Future observation date"
            assert f["observed_on"] <= p["read_date"]
    index = home(providers)
    assert 'content="noindex,nofollow"' in index and 'rel="canonical"' not in index
    assert index.count('<article class="provider"') == len(providers)
    assert "hireopus.com" not in index and "utm_" not in index and "sponsor" not in index.lower()
    for slug, selected in published_categories(providers).items():
        category_page = home(selected, slug)
        assert category_page.count('<article class="provider"') == len(selected)
        assert 'content="noindex,nofollow"' in category_page
    for p in providers:
        profile = details(p)
        assert E(p["name"]) in profile and all(E(u) in profile for u in p["source_urls"])
        assert f'/providers/{p["id"]}/' in index
    for rendered in [index, *(details(p) for p in providers)]:
        for payload in re.findall(r'<script type="application/ld\+json">(.*?)</script>', rendered):
            structured = json.loads(payload)
            assert "AggregateRating" not in payload and "Offer" not in payload
    hostile = dict(providers[0], name='<script>alert("x")</script>')
    hostile_page = details(hostile)
    assert hostile["name"] not in hostile_page
    payload = re.search(r'<script type="application/ld\+json">(.*?)</script>', hostile_page).group(1)
    assert json.loads(payload)["name"] == hostile["name"]
    assert '<script>' not in payload


def render(providers, site_url=None):
    validate(providers)
    categories = published_categories(providers)
    assert "3pl-companies" in categories, "Core category needs at least five supported providers"
    files = {"index.html":landing(providers, site_url), "3pl-evaluation-checklist/index.html":checklist(providers, site_url), "methodology/index.html":methodology(providers, site_url)}
    files.update({f"{slug}/index.html":home(members, slug, site_url) for slug,members in categories.items()})
    files.update({f'providers/{p["id"]}/index.html':details(p, site_url, categories) for p in providers})
    if site_url:
        routes = ["/", "/3pl-evaluation-checklist/", "/methodology/", *(f"/{slug}/" for slug in categories), *(f'/providers/{p["id"]}/' for p in providers)]
        files["sitemap.xml"] = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{E(site_url+route)}</loc></url>' for route in routes)+'</urlset>'
        files["robots.txt"] = f'User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n'
    else:
        files["robots.txt"] = 'User-agent: *\nDisallow: /\n'
    files["404.html"] = page("Page not found", '<section class="detail-hero"><h1>Page not found.</h1><p><a href="/3pl-companies/">Browse the provider comparison.</a></p></section>', "This page does not exist.")
    return files


def build(providers, site_url=None, output=OUT):
    files = render(providers, site_url)
    # ponytail: one build at a time; add a build lock if concurrent deployments become necessary.
    with tempfile.TemporaryDirectory(prefix=".directory-stage-", dir=output.parent) as temporary:
        staged = Path(temporary) / "dist"
        staged.mkdir()
        for filename, content in files.items():
            target = staged / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        previous = Path(temporary) / "previous"
        if output.exists():
            os.replace(output, previous)
        try:
            os.replace(staged, output)
        except BaseException:
            if previous.exists():
                os.replace(previous, output)
            raise


def self_test(providers):
    validate(providers)
    for mutate in [lambda p:p["decision_facts"][0].update(observed_on="2026-99-99"), lambda p:p["decision_facts"][0].update(source_url="https://unsupported.example/"), lambda p:p.update(read_date="9999-01-01"), lambda p:p.update(read_date="")]:
        bad = copy.deepcopy(providers)
        mutate(bad[0])
        try:
            validate(bad)
        except (AssertionError, ValueError):
            pass
        else:
            raise AssertionError("Malformed evidence accepted")
    duplicate = copy.deepcopy(providers)
    duplicate[1]["website"] = duplicate[0]["website"]
    try:
        validate(duplicate)
    except AssertionError:
        pass
    else:
        raise AssertionError("Duplicate official URL accepted")
    for value in ["http://test.example", "https://test.example/path", "https://user@test.example", "https://test.example/?x=1", 'https://test.example/<script>', "https://test.example/#x"]:
        try:
            site_root(value)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid deployment URL accepted")
    test_url = site_root("https://directory.example/")
    preview, production = render(providers), render(providers, test_url)
    assert "sitemap.xml" not in preview and "noindex,nofollow" in preview["index.html"]
    assert 'href="https://directory.example/"' in production["index.html"]
    assert '<loc>https://directory.example/</loc>' in production["sitemap.xml"]
    assert "404" not in production["sitemap.xml"]
    worksheet = production["3pl-evaluation-checklist/index.html"]
    assert 'onclick="window.print()"' in worksheet and '<form' not in worksheet
    assert worksheet.count('type="checkbox"') == 15
    assert '<loc>'+test_url+'/3pl-evaluation-checklist/</loc>' in production["sitemap.xml"]
    assert '<loc>'+test_url+'/methodology/</loc>' in production["sitemap.xml"]
    assert "independently tested" in production["methodology/index.html"]
    for provider_id, label in [("shipbob", "API constraint"), ("fulfillrite", "Minimum charges")]:
        provider = next((p for p in providers if p["id"] == provider_id), None)
        if provider:
            fact = next(f for f in provider["decision_facts"] if f["label"] == label)
            assert E(fact["source_url"]) in worksheet and E(fact["value"]) in worksheet
    assert "correction submission channel" not in production["index.html"]
    for p in providers:
        if p["public_pricing"]:
            assert E(p["public_pricing"]) in production["3pl-companies/index.html"]
            assert E(p["public_pricing"]) in production[f'providers/{p["id"]}/index.html']
            bad = copy.deepcopy(providers)
            next(q for q in bad if q["id"] == p["id"])["public_pricing"] = "$9999999 unsupported minimum"
            try:
                validate(bad)
            except AssertionError:
                pass
            else:
                raise AssertionError("Mismatched price accepted")
    assert "Disallow" not in production["robots.txt"]
    assert production["3pl-companies/index.html"].index('id="search"') < production["3pl-companies/index.html"].index("<table>")
    assert '<table>' not in production["index.html"] and '<table>' in production["3pl-companies/index.html"]
    for filename, body in production.items():
        if filename.endswith(".html") and filename != "404.html":
            assert "noindex" not in body
            schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', body).group(1))
            assert schema["url"].startswith(test_url) and schema["breadcrumb"]["itemListElement"][0]["item"] == test_url+"/"
            if filename.startswith("providers/"):
                provider = next(p for p in providers if filename == f'providers/{p["id"]}/index.html')
                assert schema["mainEntity"] == organization(provider)
                assert E(schema["mainEntity"]["name"]) in body and E(schema["mainEntity"]["description"]) in body
            if filename.split("/")[0] in CATEGORIES:
                members = published_categories(providers)[filename.split("/")[0]]
                assert schema["mainEntity"]["numberOfItems"] == len(members)
                assert [item["item"] for item in schema["mainEntity"]["itemListElement"]] == [organization(p) for p in members]
    category_fixture = copy.deepcopy(providers)
    for i,p in enumerate(category_fixture):
        p["categories"] = ["3pl-companies"] + (["ecommerce-fulfillment"] if i < 5 else []) + (["cold-chain-logistics"] if i < 4 else [])
        p["category_evidence"] = {slug:{"source_url":p["decision_facts"][0]["source_url"], "supporting_fact":p["decision_facts"][0]["value"]} for slug in p["categories"] if slug != "3pl-companies"}
    broken_categories = copy.deepcopy(category_fixture)
    broken_categories[0]["category_evidence"] = {}
    try:
        validate(broken_categories)
    except AssertionError:
        pass
    else:
        raise AssertionError("Unsupported category assignment accepted")
    category_files = render(category_fixture, test_url)
    assert "ecommerce-fulfillment/index.html" in category_files
    assert "cold-chain-logistics/index.html" not in category_files
    ecommerce = category_files["ecommerce-fulfillment/index.html"]
    assert ecommerce.count('<article class="provider"') == 5
    assert CATEGORIES["ecommerce-fulfillment"][1] in ecommerce
    assert '<loc>'+test_url+'/ecommerce-fulfillment/</loc>' in category_files["sitemap.xml"]
    assert '/cold-chain-logistics/' not in category_files["sitemap.xml"]
    assert 'href="/ecommerce-fulfillment/"' in category_files[f'providers/{category_fixture[0]["id"]}/index.html']
    if len(category_fixture) > 5:
        assert f'href="/providers/{category_fixture[5]["id"]}/"' not in ecommerce
        assert 'href="/ecommerce-fulfillment/"' not in category_files[f'providers/{category_fixture[5]["id"]}/index.html']
    for filename, body in category_files.items():
        if filename.endswith('.html'):
            for route in re.findall(r'href="(/[^"#]*)',body):
                if route.endswith('/'):
                    assert route.lstrip('/')+'index.html' in category_files, f"Missing internal route {route}"
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary)/"dist"
        output.mkdir()
        (output/"index.html").write_text("previous good build")
        bad = copy.deepcopy(providers)
        bad[0]["review_note"] = object()
        try:
            build(bad, output=output)
        except (AttributeError, TypeError):
            pass
        else:
            raise AssertionError("Expected rendering failure")
        assert (output/"index.html").read_text() == "previous good build"
    print(f"Passed: {len(providers)} profiles; evidence, dates, escaping, deployment modes, schema and failed-build preservation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--site-url", type=site_root, help="Explicitly generate indexable production output for this HTTPS domain")
    args = parser.parse_args()
    providers = sorted(json.loads((ROOT / "data.json").read_text()), key=lambda p:p["name"].casefold())
    if args.test:
        self_test(providers)
    else:
        build(providers, args.site_url)
        print(f"Built {len(providers)} profiles in {OUT}; mode: {'production' if args.site_url else 'noindex preview'}")


if __name__ == "__main__":
    main()
