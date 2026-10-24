import re
import hashlib
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
from collections import Counter
import atexit

SEEN_FINGERPRINTS = set()
HAMMING_THRESHOLD = 3
UNIQUE_PAGES = set()
SUB_DOMAINS = {}
LONGEST_PAGE_URL = ""
LONGEST_PAGE_WORDS = 0
WORD_FREQ = Counter()

def load_stop_words():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stopword_path = os.path.join(base_dir, "stopword.txt")

    with open(stopword_path, "r") as f:
        return {
            line.strip().lower()
            for line in f
            if line.strip()
        }
STOP_WORDS = load_stop_words()

def three_gram(text):
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())

    if len(words) < 3:
        return words

    return [
        " ".join(words[i:i+3])
        for i in range(len(words) - 2)
    ]

def compute_simhash(tokens):
    """Computes a 64-bit SimHash integer from a list of token strings."""
    if not tokens:
        return 0
    
    v = [0] * 64
    for token in tokens:
        # Generate 64-bit MD5 hash slice
        token_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest()[:16], 16)
        for i in range(64):
            bit = (token_hash >> i) & 1
            v[i] += 1 if bit else -1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint

def hamming_distance(hash1, hash2):
    """Calculates the number of differing bits between two 64-bit integers."""
    x = (hash1 ^ hash2) & 0xFFFFFFFFFFFFFFFF
    return bin(x).count('1')


def is_near_duplicate(fingerprint):
    """Checks if a fingerprint is within the threshold of any previously seen page."""
    for seen_fp in SEEN_FINGERPRINTS:
        if hamming_distance(fingerprint, seen_fp) <= HAMMING_THRESHOLD:
            return True
    return False

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    global LONGEST_PAGE_WORDS
    global LONGEST_PAGE_URL
    links = []

    if resp.status != 200:
        return links

    parseHTML = BeautifulSoup(resp.raw_response.content, "lxml")
    text = parseHTML.get_text(separator= ' ')
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())
    
    currentUrl = urldefrag(resp.url)[0]
    UNIQUE_PAGES.add(currentUrl)

    # STAT: SUBdomain
    hostname = urlparse(currentUrl).hostname
    if hostname and hostname.endswith(".ics.uci.edu"):
        if hostname not in SUB_DOMAINS:
            SUB_DOMAINS[hostname] = set()
        SUB_DOMAINS[hostname].add(currentUrl)

    
    
    # STAT: LONGEST PAGE 
    if len(words) > LONGEST_PAGE_WORDS:
        LONGEST_PAGE_WORDS= len(words)
        LONGEST_PAGE_URL = resp.url

    # STAT: Most Common Words
    filteredWords = []
    for word in words:
        if word not in STOP_WORDS:
            filteredWords.append(word)

    WORD_FREQ.update(filteredWords)
    #finger printing and check
    
    tokens = three_gram(text)
    fingerprint = compute_simhash(tokens)
    
    
    if is_near_duplicate(fingerprint):
        print("Duplicate page skipped:", resp.url)
        return links
    SEEN_FINGERPRINTS.add(fingerprint)

    seen_links = set()
    for tag in parseHTML.find_all("a", href = True):
        href = tag["href"]

        absoluteUrl = urljoin(resp.url, href)

        absoluteUrl = urldefrag(absoluteUrl)[0]
        if absoluteUrl and absoluteUrl not in seen_links:
            seen_links.add(absoluteUrl)
            links.append(absoluteUrl)
            
    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:

        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        allowed_domains = (
            ".ics.uci.edu",
            ".cs.uci.edu",
            ".informatics.uci.edu",
            ".stat.uci.edu"
        )
        if not parsed.netloc.endswith(allowed_domains):
            return False
        return not re.match(
        r".*\.(css|js|bmp|gif|jpe?g|ico"
        + r"|png|tiff?|mid|mp2|mp3|mp4"
        + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
        + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
        + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
        + r"|epub|dll|cnf|tgz|sha1"
        + r"|thmx|mso|arff|rtf|jar|csv"
        + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def print_stats():
    #Prints and writes final assignment report to crawler_report.txt
    report_lines = []
    
    report_lines.append("=" * 60)
    report_lines.append("           CS 121 / INFX 141 CRAWLER REPORT")
    report_lines.append("=" * 60 + "\n")

    # STAT1: Unique Pages
    report_lines.append(f"1. Unique Pages Found: {len(UNIQUE_PAGES)}\n")

    # STAT2: Longest Page
    report_lines.append("2. Longest Page:")
    report_lines.append(f"   URL: {LONGEST_PAGE_URL}")
    report_lines.append(f"   Word Count: {LONGEST_PAGE_WORDS}\n")

    # STAT3: 50 Most Common Words
    report_lines.append("3. 50 Most Common Words:")
    for rank, (word, count) in enumerate(WORD_FREQ.most_common(50), 1):
        report_lines.append(f"   {rank}. {word}: {count}")
    report_lines.append("")

    # STAT4: Subdomains in ics.uci.edu
    report_lines.append(f"4. Subdomains in ics.uci.edu ({len(SUB_DOMAINS)} total):")
    for hostname in sorted(SUB_DOMAINS.keys()):
        count = len(SUB_DOMAINS[hostname])
        report_lines.append(f"   http://{hostname}, {count}")

    report_lines.append("\n" + "=" * 60)

    report_text = "\n".join(report_lines)
    print(report_text)

    # Save output automatically to report text file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(base_dir, "crawler_report.txt")
    with open("crawler_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
    print("\n[SUCCESS] Final statistics written to 'crawler_report.txt'.")

atexit.register(print_stats)