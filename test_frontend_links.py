"""
Frontend Link Validation Tests

Verifies that generated HTML files have correct relative paths for:
  - CSS and JS asset references
  - Inter-page navigation links (nav header, CTAs, anchor tags)
  - Home links from within the /pages/ subdirectory

Rules enforced:
  index.html  → other pages: href="pages/pagename.html"
  pages/*.html → other pages: href="pagename.html"  (no pages/ prefix)
  pages/*.html → home:        href="../index.html"
  pages/*.html → CSS:         href="../styles.css"
  pages/*.html → shared JS:   src="../api.js" / src="../nav.js"
  NEVER: absolute paths starting with /
"""

import re
import sys
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def find_hrefs(html: str) -> list[str]:
    """Return all href values from anchor and link tags."""
    return re.findall(r'href=["\']([^"\'#][^"\']*)["\']', html)


def find_srcs(html: str) -> list[str]:
    """Return all src values from script tags."""
    return re.findall(r'src=["\']([^"\'#][^"\']*)["\']', html)


def check_no_absolute_paths(paths: list[str], file_label: str) -> list[str]:
    """Fail if any path starts with / (absolute)."""
    errors = []
    for p in paths:
        if p.startswith('/'):
            errors.append(f"{file_label}: absolute path found: '{p}' — use relative paths only")
    return errors


def check_pages_subdir_links(hrefs: list[str], file_label: str) -> list[str]:
    """
    In a pages/*.html file, links to other pages must NOT include 'pages/' prefix.
    They should be bare filenames like 'catalog.html', not 'pages/catalog.html'.
    """
    errors = []
    for h in hrefs:
        if h.startswith('pages/') and h.endswith('.html'):
            errors.append(
                f"{file_label}: link uses 'pages/' prefix '{h}' — "
                "from inside /pages/ use bare filename e.g. 'catalog.html'"
            )
    return errors


def check_index_links_have_pages_prefix(hrefs: list[str], known_pages: set[str], file_label: str) -> list[str]:
    """
    From index.html, links to known sub-pages must use 'pages/pagename.html'.
    A bare 'pagename.html' (without pages/) is wrong from the root.
    """
    errors = []
    for h in hrefs:
        if h.endswith('.html') and not h.startswith('pages/') and h != 'index.html':
            basename = Path(h).name
            if basename in known_pages:
                errors.append(
                    f"{file_label}: link to '{h}' is missing 'pages/' prefix — "
                    "from index.html use 'pages/pagename.html'"
                )
    return errors


def check_asset_paths(srcs: list[str], hrefs: list[str], file_label: str, in_pages_dir: bool) -> list[str]:
    """
    CSS/JS assets must use the correct relative path for the file's location.

    File layout:
      frontend/
        index.html       → js/api.js   js/nav.js   styles.css
        js/api.js
        js/nav.js
        styles.css
        pages/
          *.html         → ../js/api.js   ../js/nav.js   ../styles.css
    """
    errors = []

    # Expected paths differ by location
    if in_pages_dir:
        expected_api  = '../js/api.js'
        expected_nav  = '../js/nav.js'
        expected_css  = '../styles.css'
    else:
        expected_api  = 'js/api.js'
        expected_nav  = 'js/nav.js'
        expected_css  = 'styles.css'

    for src in srcs:
        if src.startswith('http'):
            continue
        basename = Path(src).name
        if basename == 'api.js' and src != expected_api:
            errors.append(f"{file_label}: JS asset '{src}' should be '{expected_api}'")
        if basename == 'nav.js' and src != expected_nav:
            errors.append(f"{file_label}: JS asset '{src}' should be '{expected_nav}'")

    for href in hrefs:
        if href.startswith('http'):
            continue
        basename = Path(href).name
        if basename == 'styles.css' and href != expected_css:
            errors.append(f"{file_label}: CSS asset '{href}' should be '{expected_css}'")

    return errors


# ── core validator ────────────────────────────────────────────────────────────

def validate_product_frontend(frontend_dir: Path) -> list[str]:
    """
    Validate all HTML files in a product's frontend directory.
    Returns a list of error strings (empty = all good).
    """
    errors: list[str] = []
    frontend_dir = Path(frontend_dir)

    if not frontend_dir.exists():
        return [f"Frontend directory does not exist: {frontend_dir}"]

    pages_dir = frontend_dir / 'pages'
    known_pages: set[str] = set()
    if pages_dir.exists():
        known_pages = {p.name for p in pages_dir.glob('*.html')}

    # ── validate index.html ────────────────────────────────────────────────
    index_html = frontend_dir / 'index.html'
    if index_html.exists():
        content = index_html.read_text()
        hrefs = find_hrefs(content)
        srcs = find_srcs(content)
        label = 'index.html'

        errors += check_no_absolute_paths(hrefs + srcs, label)
        errors += check_index_links_have_pages_prefix(hrefs, known_pages, label)
        errors += check_asset_paths(srcs, hrefs, label, in_pages_dir=False)

    # ── validate pages/*.html ──────────────────────────────────────────────
    if pages_dir.exists():
        for page_file in pages_dir.glob('*.html'):
            content = page_file.read_text()
            hrefs = find_hrefs(content)
            srcs = find_srcs(content)
            label = f'pages/{page_file.name}'

            errors += check_no_absolute_paths(hrefs + srcs, label)
            errors += check_pages_subdir_links(hrefs, label)
            errors += check_asset_paths(srcs, hrefs, label, in_pages_dir=True)

            # Home link must be ../index.html, not index.html or /index.html
            for h in hrefs:
                if h == 'index.html':
                    errors.append(
                        f"{label}: home link 'index.html' should be '../index.html' from inside /pages/"
                    )

    return errors


# ── test runner ───────────────────────────────────────────────────────────────

class FrontendLinkTests:
    """Tests for frontend link and path correctness."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def _assert(self, condition: bool, msg: str):
        if condition:
            print(f"  ✓ {msg}")
            self.passed += 1
        else:
            print(f"  ✗ {msg}")
            self.failed += 1

    def test_resolvepath_logic(self):
        """Unit-test the path resolution rules without needing a browser."""
        print("\n[Unit] resolvePath logic")

        def resolve(path: str, in_pages: bool) -> str:
            if in_pages and path.startswith('pages/'):
                return path[len('pages/'):]
            return path

        self._assert(resolve('pages/catalog.html', True) == 'catalog.html',
                     "pages/catalog.html → catalog.html when in /pages/")
        self._assert(resolve('pages/catalog.html', False) == 'pages/catalog.html',
                     "pages/catalog.html unchanged when at root")
        self._assert(resolve('catalog.html', True) == 'catalog.html',
                     "bare catalog.html unchanged when in /pages/")
        self._assert(resolve('login.html', True) == 'login.html',
                     "login.html (no prefix) unchanged in /pages/")

    def test_no_absolute_paths(self):
        """Absolute paths starting with / must be caught."""
        print("\n[Unit] Absolute path detection")
        errors = check_no_absolute_paths(['/styles.css', '/pages/login.html', 'ok.html'], 'test.html')
        self._assert(len(errors) == 2, "Detects 2 absolute paths")
        errors = check_no_absolute_paths(['../styles.css', 'login.html'], 'test.html')
        self._assert(len(errors) == 0, "No false positives on relative paths")

    def test_pages_subdir_link_check(self):
        """From /pages/, links with pages/ prefix must be caught."""
        print("\n[Unit] pages/ prefix detection inside /pages/")
        errors = check_pages_subdir_links(['pages/catalog.html', 'catalog.html', '../index.html'], 'pages/x.html')
        self._assert(len(errors) == 1, "Catches only the pages/ prefixed link")
        self._assert('pages/catalog.html' in errors[0], "Error mentions the offending path")

    def test_index_missing_pages_prefix(self):
        """From index.html, bare page references must be caught."""
        print("\n[Unit] Missing pages/ prefix in index.html")
        known = {'catalog.html', 'login.html'}
        errors = check_index_links_have_pages_prefix(
            ['catalog.html', 'pages/login.html', 'index.html'], known, 'index.html'
        )
        self._assert(len(errors) == 1, "Catches bare 'catalog.html' missing pages/ prefix")
        errors = check_index_links_have_pages_prefix(
            ['pages/catalog.html', 'pages/login.html'], known, 'index.html'
        )
        self._assert(len(errors) == 0, "No errors when pages/ prefix present")

    def test_asset_paths(self):
        """CSS and JS assets must use correct prefix for their location."""
        print("\n[Unit] Asset path validation")

        # From pages/ — must use ../js/ subdirectory prefix
        errors = check_asset_paths(['/api.js', '../js/nav.js'], ['../styles.css'], 'pages/x.html', True)
        self._assert(any('/api.js' in e for e in errors), "Catches /api.js (absolute) in pages/")
        self._assert(not any('../js/nav.js' in e for e in errors), "../js/nav.js is correct in pages/")

        # From root — must use js/ subdirectory prefix
        errors = check_asset_paths(['../api.js'], ['styles.css'], 'index.html', False)
        self._assert(any('../api.js' in e for e in errors), "Catches ../api.js (wrong prefix) in index.html")

        errors = check_asset_paths(['js/api.js', 'js/nav.js'], ['styles.css'], 'index.html', False)
        self._assert(len(errors) == 0, "js/api.js, js/nav.js, styles.css are correct in index.html")

    def test_existing_products(self):
        """Validate all existing generated products in products/ directory."""
        print("\n[Integration] Existing generated products")
        products_dir = Path(__file__).parent / 'products'
        if not products_dir.exists():
            print("  (no products/ directory found, skipping)")
            return

        any_tested = False
        for product_dir in sorted(products_dir.iterdir()):
            frontend_dir = product_dir / 'frontend'
            if not frontend_dir.exists():
                continue
            pages = list((frontend_dir / 'pages').glob('*.html')) if (frontend_dir / 'pages').exists() else []
            if not pages:
                continue  # skip fallback-only products

            any_tested = True
            errors = validate_product_frontend(frontend_dir)
            if errors:
                for e in errors:
                    print(f"  ✗ {product_dir.name}: {e}")
                self.failed += len(errors)
            else:
                print(f"  ✓ {product_dir.name}: all links valid")
                self.passed += 1

        if not any_tested:
            print("  (no products with pages found)")

    def run(self):
        print("=" * 60)
        print("FRONTEND LINK VALIDATION TESTS")
        print("=" * 60)
        self.test_resolvepath_logic()
        self.test_no_absolute_paths()
        self.test_pages_subdir_link_check()
        self.test_index_missing_pages_prefix()
        self.test_asset_paths()
        self.test_existing_products()
        print(f"\n{'=' * 60}")
        print(f"Results: {self.passed} passed, {self.failed} failed")
        if self.failed:
            print("SOME TESTS FAILED")
            return False
        print("ALL TESTS PASSED")
        return True


if __name__ == '__main__':
    ok = FrontendLinkTests().run()
    sys.exit(0 if ok else 1)
