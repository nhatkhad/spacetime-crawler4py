import re
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
from collections import Counter


SEEN_FINGERPRINTS = set()
HAMMING_THRESHOLD = 3
UNIQUE_PAGES = set()
SUB_DOMAINS = {}
LONGEST_PAGE_URL = ""
LONGEST_PAGE_WORDS = 0
WORD_FREQ = Counter()

def load_stop_words():
    with open("stopwords.txt", "r") as f:
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
    links = []

    if resp.status != 200:
        return links
    currentUrl = urldefrag(resp.url)[0]
    UNIQUE_PAGES.add(currentUrl)

    parseHTML = BeautifulSoup(resp.raw_response.content, "lxml")
    #finger printing and check
    text = parseHTML.get_text(separator= ' ')
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())
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
    
    
    fingerprint = compute_simhash(tokens)
    tokens = three_gram(text)
    
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
