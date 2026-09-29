#!/usr/bin/env python3
"""Audit a deployed directory's crawl and answer-retrieval foundations."""
import argparse
import concurrent.futures
import json
import re
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse


class Page(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.headings, self.canonicals, self.descriptions = [], [], []
        self.links, self.schemas, self.directives = [], [], []
        self.titles, self.schema_errors, self.visible = [], [], []
        self.title, self.hidden = None, 0
        self.heading, self.schema = None, None
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'): self.hidden += 1
        if tag == 'title': self.title = ''
        if tag == 'h1': self.heading = ''
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split(): self.canonicals.append(a.get('href'))
        if tag == 'meta' and a.get('name', '').lower() == 'description': self.descriptions.append(a.get('content', ''))
        if tag == 'meta' and a.get('name', '').lower() in ('robots', 'googlebot', 'bingbot', 'oai-searchbot', 'perplexitybot'): self.directives.append(a.get('content', ''))
        if tag == 'a' and a.get('href'): self.links.append(a['href'])
        if tag == 'script' and a.get('type') == 'application/ld+json': self.schema = ''

    def handle_data(self, value):
        if self.title is not None: self.title += value
        if not self.hidden: self.visible.append(value)
        if self.heading is not None: self.heading += value
        if self.schema is not None: self.schema += value

    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
        if tag == 'title' and self.title is not None:
            self.titles.append(self.title.strip()); self.title = None
        if tag == 'h1' and self.heading is not None:
            self.headings.append(self.heading.strip()); self.heading = None
        if tag == 'script' and self.schema is not None:
            try:
                self.schemas.append(json.loads(self.schema))
            except (ValueError, TypeError) as error:
                self.schema_errors.append(str(error))
            self.schema = None


def schema_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from schema_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from schema_objects(child)


def page_issues(page, url, headers):
    issues = []
    if page.canonicals != [url]: issues.append('Missing or conflicting self-canonical')
    if len(page.titles) != 1 or not page.titles[0]: issues.append('Expected one nonempty title')
    if len(page.headings) != 1 or not page.headings[0]: issues.append('Expected one nonempty H1')
    if len(page.descriptions) != 1 or not page.descriptions[0]: issues.append('Missing or duplicate description')
    directives = ','.join(page.directives) + ',' + next((v for k,v in headers.items() if k.lower() == 'x-robots-tag'), '')
    if re.search(r'\b(noindex|none)\b', directives.lower()): issues.append('Unexpected noindex')
    if page.schema_errors: issues.append('Malformed JSON-LD')
    if not page.schemas: issues.append('Missing structured data')
    objects = list(schema_objects(page.schemas))
    pages = [obj for obj in objects if obj.get('@type') in ('WebPage', 'CollectionPage')]
    if len(pages) != 1 or pages[0].get('url') != url: issues.append('Page schema URL disagrees with canonical')
    visible = ' '.join(' '.join(page.visible).split())
    for obj in objects:
        if obj.get('@type') == 'Organization':
            for field in ('name', 'description'):
                if obj.get(field) and ' '.join(obj[field].split()) not in visible:
                    issues.append('Organization '+field+' is not in visible HTML')
        if obj.get('@type') == 'ItemList' and obj.get('numberOfItems') != len(obj.get('itemListElement', [])):
            issues.append('ItemList count disagrees with entries')
    for observed in re.findall(r'(?:Observed|Reviewed|reviewed through)\s+(\d{4}-\d{2}-\d{2})', visible):
        try:
            if date.fromisoformat(observed) > date.today(): issues.append('Future visible evidence date')
        except ValueError:
            issues.append('Malformed visible evidence date')
    return list(dict.fromkeys(issues))

def fetch(url, agent='3PLFieldGuideQualityAudit/1.0'):
    request = urllib.request.Request(url, headers={'User-Agent': agent})
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, dict(response.headers), response.read().decode('utf-8'), response.url


def audit(base):
    base = base.rstrip('/')
    origin = urlparse(base)
    assert origin.scheme == 'https' and origin.hostname and not origin.username and not origin.password and not origin.query and not origin.fragment and not origin.path, 'Audit the public HTTPS origin without a path or credentials'
    status, _, robots, _ = fetch(base + '/robots.txt')
    assert status == 200, 'robots.txt unavailable'
    rules = urllib.robotparser.RobotFileParser(); rules.parse(robots.splitlines())
    status, _, sitemap, _ = fetch(base + '/sitemap.xml')
    assert status == 200, 'sitemap.xml unavailable'
    sitemap_root = ET.fromstring(sitemap)
    assert sitemap_root.tag == '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset', 'Expected one URL sitemap, not a sitemap index'
    urls = [e.text for e in sitemap_root.findall('{*}url/{*}loc')]
    assert urls and len(urls) == len(set(urls)), 'Empty or duplicate sitemap'
    assert all(u.startswith(base + '/') for u in urls), 'Sitemap contains another origin'
    bots = ['Googlebot', 'bingbot', 'OAI-SearchBot', 'PerplexityBot']

    def inspect(url):
        try:
            status, headers, body, final = fetch(url)
        except (OSError, ValueError) as error:
            return {'url':url, 'status':None, 'h1':[], 'title':[], 'bytes':0, 'issues':['Fetch failed: '+str(error)], 'internal_links':[], 'external_https_links':0}
        page = Page(body)
        issues = []
        if status != 200: issues.append('HTTP status is not 200')
        if final != url: issues.append('Canonical sitemap URL redirects')
        issues.extend(page_issues(page, url, headers))
        blocked = [bot for bot in bots if not rules.can_fetch(bot, url)]
        if blocked: issues.append('Robots blocks ' + ', '.join(blocked))
        links = sorted(set(urljoin(url, link).split('#')[0].split('?')[0] for link in page.links))
        internal = [link for link in links if link.startswith(base + '/')]
        broken = [link for link in internal if link not in urls]
        if broken: issues.append('Internal links outside sitemap: ' + ', '.join(broken))
        if '/providers/' in url and ('Source</a>' not in body or 'Observed ' not in body):
            issues.append('Profile lacks visible claim sources or observation dates')
        if re.search(r'"(?:aggregateRating|reviewRating)"', body): issues.append('Review schema requires an evidence audit')
        return {'url':url, 'status':status, 'h1':page.headings, 'title':page.titles, 'bytes':len(body.encode()), 'issues':issues,
                'internal_links':internal, 'external_https_links':len([u for u in links if u.startswith('https://') and not u.startswith(base + '/')])}

    # ponytail: one sitemap and at most 5000 pages; recurse sitemap indexes if inventory grows beyond this deployment.
    assert len(urls) <= 5000
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pages = list(pool.map(inspect, urls))
    reached = {base + '/'}
    for _ in range(3):
        reached |= {link for page in pages if page['url'] in reached for link in page['internal_links']}
    issues = []
    for field in ('title', 'h1'):
        seen = {}
        for entry in pages:
            for value in entry[field]:
                seen.setdefault(value, []).append(entry['url'])
        duplicates = {value:routes for value,routes in seen.items() if len(routes) > 1}
        if duplicates: issues.append({'duplicate_'+field:duplicates})
    orphaned = sorted(set(urls) - reached)
    if orphaned: issues.append({'unreachable_within_three_clicks':orphaned})
    missing_status, _, _, _ = fetch(base + '/__directory-quality-missing-page__')
    if missing_status != 404: issues.append({'missing_page_status':missing_status})
    http_status, _, _, http_final = fetch(base.replace('https://', 'http://', 1) + '/')
    if http_status != 200 or not http_final.startswith(base + '/'):
        issues.append({'http_redirect_target':http_final})
    probes = {}
    sample = next((u for u in urls if '/providers/' in u), base + '/')
    for bot in bots:
        code, _, body, _ = fetch(sample, bot)
        probes[bot] = {'status':code, 'html_h1_present':bool(Page(body).headings)}
        if code != 200 or not Page(body).headings: issues.append({'crawler_probe_failed':bot})
    return {'audited_at':datetime.now(timezone.utc).isoformat(), 'origin':base, 'pages':pages,
            'page_count':len(pages), 'crawler_http_probes':probes, 'site_issues':issues,
            'passed':not issues and not any(p['issues'] for p in pages),
            'limits':'Crawler probes test HTTP responses with named user agents, not verified crawler visits. Passing checks does not establish indexing, rankings, citations, performance or audience quality.'}


def self_test():
    import build
    providers = sorted(json.loads((Path(__file__).parent/'data.json').read_text()), key=lambda p:p['name'].casefold())
    origin = 'https://directory.example'
    files = build.render(providers, origin)
    titles = []
    for filename, body in files.items():
        if not filename.endswith('.html') or filename == '404.html': continue
        route = '/' if filename == 'index.html' else '/'+filename.removesuffix('index.html')
        parsed = Page(body)
        assert not page_issues(parsed, origin+route, {}), (filename, page_issues(parsed, origin+route, {}))
        titles += parsed.titles
    assert len(titles) == len(set(titles)), 'Duplicate production titles'
    sample = files['3pl-companies/index.html']
    assert 'Malformed JSON-LD' in page_issues(Page(sample.replace('"@context"', 'BROKEN', 1)), origin+'/3pl-companies/', {})
    assert 'Unexpected noindex' in page_issues(Page(sample), origin+'/3pl-companies/', {'X-Robots-Tag':'none'})
    assert 'Page schema URL disagrees with canonical' in page_issues(Page(sample), origin+'/wrong/', {})
    assert Page('<title>Example &amp; more</title><h1 class="x">A <span>nested</span> heading</h1>').headings == ['A nested heading']
    print(f'Passed parser and rendered-production checks for {len(titles)} pages; no network requests.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?'); parser.add_argument('--output', default='live-audit.json'); parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    if args.test:
        self_test()
    else:
        if not args.url: parser.error('Provide an HTTPS origin or --test')
        result = audit(args.url)
        Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k:v for k,v in result.items() if k != 'pages'}, indent=2))
        raise SystemExit(0 if result['passed'] else 1)
