import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, urldefrag

from bs4 import BeautifulSoup


STATS_FILE = Path("page_stats.jsonl")
REPORT_FILE = Path("report.txt")

# Common English stop words to exclude from the 50 most frequent words.
STOP_WORDS = set("""
a about above after again against all am an and any are aren't as at
be because been before being below between both but by can can't
cannot could couldn't did didn't do does doesn't doing don't down
during each few for from further had hadn't has hasn't have haven't
having he he'd he'll he's her here here's hers herself him himself
his how how's i i'd i'll i'm i've if in into is isn't it it's its
itself just let's me more most must my myself no nor not of off on
once only or other our ours ourselves out over own same she she'd
she'll she's should shouldn't so some such than that that's the
their theirs them themselves then there there's these they they'd
they'll they're they've this those through to too under until up
very was wasn't we we'd we'll we're we've were weren't what what's
when when's where where's which while who who's whom why why's with
won't would wouldn't you you'd you'll you're you've your yours
yourself yourselves
""".split())

WORD_PATTERN = re.compile(r"[a-z]+(?:'[a-z]+)?")


def normalize_url(url):
    # Ignore fragments, and normalize the scheme and hostname.
    url, _ = urldefrag(url)
    parsed = urlparse(url)

    return parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment=""
    ).geturl()


def record_page_stats(url, html_content):
    # Extract visible text instead of counting HTML markup.
    soup = BeautifulSoup(html_content, "html.parser")

    # Exclude code and content that generally isn't visible page text.
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True).lower()
    words = WORD_PATTERN.findall(text)

    # Count every word for the longest-page calculation.
    word_count = len(words)

    # Exclude common English stop words from word-frequency statistics.
    frequencies = Counter(
        word for word in words if word not in STOP_WORDS
    )

    record = {
        "url": normalize_url(url),
        "word_count": word_count,
        "word_frequencies": dict(frequencies)
    }

    # Append each visited page. Duplicate URLs are deduplicated later.
    with STATS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def generate_report():
    # Keep one record per URL, even if a page was logged multiple times.
    pages = {}

    if not STATS_FILE.exists():
        raise FileNotFoundError(
            "No page statistics found. Run the crawler first."
        )

    with STATS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)
            pages[normalize_url(record["url"])] = record

    if not pages:
        raise ValueError("No pages were recorded.")

    all_word_frequencies = Counter()
    subdomain_counts = Counter()

    for url, record in pages.items():
        all_word_frequencies.update(record["word_frequencies"])

        host = urlparse(url).hostname

        # Count unique pages hosted under ics.uci.edu, by hostname.
        if host and (
            host == "ics.uci.edu"
            or host.endswith(".ics.uci.edu")
        ):
            subdomain_counts[host.lower()] += 1

    # Find the page with the greatest word count.
    longest_url, longest_page = max(
        pages.items(),
        key=lambda item: item[1]["word_count"]
    )

    lines = [
        f"Unique pages: {len(pages)}",
        "",
        "Longest page:",
        f"URL: {longest_url}",
        f"Word count: {longest_page['word_count']}",
        "",
        "Top 50 words (excluding stop words):"
    ]

    for word, count in all_word_frequencies.most_common(50):
        lines.append(f"{word}, {count}")

    lines.extend([
        "",
        "ICS subdomains (alphabetical):"
    ])

    for host, count in sorted(subdomain_counts.items()):
        lines.append(f"http://{host}, {count}")

    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nReport saved to {REPORT_FILE}")