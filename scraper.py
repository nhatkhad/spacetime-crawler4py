import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
from results import record_page_stats

def scraper(url, resp):
    # Record statistics for a successfully fetched, in-scope page.
    if resp.status == 200 and resp.raw_response is not None:
        page_url = resp.url or url

        if is_valid(page_url):
            record_page_stats(
                page_url,
                resp.raw_response.content
            )

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
    e_links = []

    if resp.status != 200:
        return e_links

    raw_res = resp.raw_response
    base_url = resp.url if resp.url else url

    for link in BeautifulSoup(raw_res.content, "html.parser").find_all('a', href=True):
        hre = link['href']

        if isinstance(hre, str) and hre.strip():
            full_url = urljoin(base_url, hre.strip())
            full_url, _ = urldefrag(full_url)
            e_links.append(full_url)

    return e_links

def is_valid(url):
    try:
        # Only accept non-empty string URLs.
        if not isinstance(url, str) or not url:
            return False

        parsed = urlparse(url)

        # Only allow HTTP and HTTPS URLs.
        if parsed.scheme.lower() not in ("http", "https"):
            return False

        # Get the hostname.
        host = parsed.hostname

        if not host:
            return False

        host = host.lower().rstrip(".")

        # Only allow the four specified UCI domain families.
        allowed_domains = (
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        )

        if not any(
            host == domain or host.endswith("." + domain)
            for domain in allowed_domains
        ):
            return False

        # Avoid the known ICS calendar crawler trap.
        if (host == "calendar.ics.uci.edu"
                and parsed.path.lower() == "/calendar.php"):
            return False

        # Reject malformed port numbers.
        _ = parsed.port

        # Ignore non-HTML resources such as images, documents, and media.
        if re.search(
            r"\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$",
            parsed.path.lower()
        ):
            return False

        return True

    except (TypeError, ValueError):
        return False