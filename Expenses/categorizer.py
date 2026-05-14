import database as db


# Known categories importable from web (standard personal finance categories)
WEB_CATEGORIES = {
    "Food & Dining": [
        "restaurant", "cafe", "coffee", "pizza", "sushi", "burger", "sandwich",
        "bakery", "deli", "food court", "fast food", "doordash", "uber eats",
        "grubhub", "postmates", "instacart", "seamless", "menufy",
        "starbucks", "mcdonald", "subway", "chipotle", "chick-fil-a",
        "taco bell", "wendy", "panera", "dunkin",
    ],
    "Groceries": [
        "grocery", "supermarket", "walmart", "costco", "target", "kroger",
        "safeway", "whole foods", "trader joe", "aldi", "publix", "heb",
        "food lion", "sprouts", "wegmans", "fresh market", "h-e-b",
    ],
    "Shopping": [
        "amazon", "ebay", "etsy", "best buy", "apple store", "ikea",
        "home depot", "lowe", "tj maxx", "marshalls", "ross", "macy",
        "nordstrom", "gap", "old navy", "h&m", "zara", "nike", "adidas",
        "sephora", "ulta", "bath & body", "victoria secret",
    ],
    "Transportation": [
        "uber", "lyft", "taxi", "parking", "toll", "metro", "transit",
        "bus", "train", "zipcar", "enterprise rent", "hertz", "avis",
    ],
    "Travel": [
        "airline", "hotel", "airbnb", "hilton", "marriott", "hyatt",
        "delta", "united", "american airlines", "southwest", "spirit",
        "expedia", "booking.com", "vrbo", "priceline", "kayak",
    ],
    "Gas & Auto": [
        "auto repair", "jiffy lube", "oil change", "autozone", "o reilly",
        "napa auto", "pep boys", "car wash", "dmv", "costco gas",
        "tesla", "ev charging", "electrify america", "chargepoint",
        "safelite", "firestone", "midas", "mavis", "discount tire",
    ],
    "Utilities": [
        "electric", "gas bill", "water bill", "internet", "at&t", "verizon",
        "t-mobile", "sprint", "comcast", "xfinity", "spectrum", "utility",
        "pg&e", "con ed", "duke energy", "dominion energy",
    ],
    "Entertainment": [
        "netflix", "spotify", "hulu", "disney+", "hbo", "amazon prime",
        "youtube premium", "cinema", "theater", "amc ", "regal", "movie",
        "ticketmaster", "stubhub", "eventbrite", "twitch",
    ],
    "Healthcare": [
        "pharmacy", "cvs", "walgreens", "rite aid", "doctor", "hospital",
        "dental", "vision", "optometrist", "urgent care", "medical",
        "clinic", "lab corp", "quest diagnostics",
    ],
    "Fitness": [
        "gym", "planet fitness", "24 hour fitness", "la fitness",
        "peloton", "yoga", "crossfit", "anytime fitness",
    ],
    "Finance & Banking": [
        "payment", "bank fee", "interest charge", "annual fee", "late fee",
        "zelle", "venmo", "paypal", "cash app", "wire transfer",
    ],
    "Insurance": [
        "insurance", "geico", "state farm", "allstate", "progressive",
        "farmers", "liberty mutual", "nationwide",
    ],
    "Education": [
        "tuition", "udemy", "coursera", "skillshare", "linkedin learning",
        "school", "college", "university", "bookstore",
    ],
    "Home & Garden": [
        "rent", "mortgage", "hoa", "pest control", "lawn", "cleaning",
        "furniture", "appliance", "plumber", "electrician",
    ],
    "Personal Care": [
        "salon", "barber", "haircut", "spa", "nail salon", "massage",
    ],
    "Subscriptions": [
        "subscription", "membership", "annual fee", "monthly fee",
    ],
    "Gifts & Donations": [
        "donation", "charity", "gofundme", "gift",
    ],
    "Kids & Family": [
        "daycare", "school supply", "toy", "baby", "children",
    ],
    "Pets": [
        "petco", "petsmart", "vet", "veterinary", "pet food", "pet store",
    ],
    "Taxes": [
        "irs", "tax payment", "state tax", "tax prep", "turbotax", "h&r block",
    ],
}


def categorize(description: str) -> tuple[str, bool]:
    """Return (category, is_wasted) for a transaction description."""
    desc_lower = description.lower()

    # Check wasted keywords first
    wasted_kws = db.get_wasted_keywords()
    for wkw in wasted_kws:
        kw = wkw['keyword'].lower()
        if kw in desc_lower:
            exclude = wkw.get('exclude_if_contains') or ''
            if exclude and exclude.lower() in desc_lower:
                continue  # Exception (e.g. Costco Gas is NOT wasted)
            return ('Wasted', True)

    # Check category rules from DB
    rules = db.get_category_rules()
    for rule in rules:
        kw = rule['keyword'].lower()
        if kw in desc_lower:
            return (rule['category'], False)

    return ('Uncategorized', False)


def extract_merchant_keyword(description: str) -> str:
    """
    Derive the shortest reliable keyword from a transaction description that
    uniquely identifies the merchant across all its transactions.

    e.g.  "STARBUCKS #12345 SEATTLE WA"  →  "starbucks"
          "STARBUCKS DRIVE THRU"          →  "starbucks"
          "AMAZON.COM*AB12CD3EF"          →  "amazon.com"
          "SHELL OIL 04529 Q35"           →  "shell"
          "IN-N-OUT BURGER #42"           →  "in-n-out"
    """
    import re
    s = description.strip()

    # Strip Amazon-style reference codes (AMAZON.COM*XYZABC → AMAZON.COM)
    s = re.sub(r'\*[\w\d]+', '', s)
    # Strip inline reference numbers (#1234, 04529)
    s = re.sub(r'\s+#?\d[\d\-]*', '', s)
    # Strip trailing US state abbreviations (two capital letters at end)
    s = re.sub(r'\s+[A-Z]{2}\s*$', '', s.strip())
    s = re.sub(r'\s{2,}', ' ', s).strip()

    # Split into tokens; drop pure-number/punctuation tokens
    words = [w for w in s.split() if re.search(r'[A-Za-z]', w)]

    if not words:
        return description[:20].lower().strip()

    first = words[0].lower()

    # If the first word is substantial (≥5 chars) it IS the brand — use it alone.
    # Short first words (e.g. "IN", "THE") get a second word appended.
    if len(first) >= 5:
        return first
    elif len(words) >= 2:
        return (first + ' ' + words[1].lower()).strip()
    return first


def recategorize_all():
    """Re-run categorization on all transactions that are Uncategorized."""
    txns = db.get_transactions()
    for txn in txns:
        if txn['category'] in ('Uncategorized', None):
            cat, is_wasted = categorize(txn['description'])
            db.update_transaction_category(txn['id'], cat, is_wasted)


# ── Public dispatcher ─────────────────────────────────────────────────────────

def parse_statement(filepath: str, account_id: int, statement_file: str,
                    currency: str = 'USD') -> tuple[list, int, int]:
    """Route to the right parser based on file extension."""
    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        return parse_pdf(filepath, account_id, statement_file, currency=currency)
    if ext in ('xlsx', 'xls'):
        return parse_excel(filepath, account_id, statement_file, currency=currency)
    return parse_csv(filepath, account_id, statement_file, currency=currency)


# ── CSV ───────────────────────────────────────────────────────────────────────

def parse_csv(filepath: str, account_id: int, statement_file: str,
              currency: str = 'USD') -> tuple[list, int, int]:
    df = _load_csv(filepath)
    if df is None or df.empty:
        return [], 0, 0
    return _df_to_transactions(df, account_id, statement_file, source='CSV', currency=currency)


def _load_csv(filepath: str):
    """
    Smart CSV loader that handles:
    - Files with metadata header rows (ICICI, HDFC, Axis, SBI, etc.)
    - Files with a MESSAGE/NOTES section at the bottom
    - Standard bank CSVs with no preamble
    """
    import pandas as pd
    import io

    # Column names that indicate a real transaction header row
    HEADER_SIGNALS = {'date', 'transaction', 'amount', 'description',
                      'debit', 'credit', 'memo', 'narration', 'particulars',
                      'withdrawal', 'deposit', 'details', 'dr', 'cr'}
    # Section-end markers (stop reading after these)
    CUTOFF_SIGNALS = ('message details', 'srno,last_upd', 'safe banking',
                      'note:', 'disclaimer', '---', 'end of statement')

    for encoding in ('utf-8', 'latin-1', 'cp1252'):
        try:
            with open(filepath, encoding=encoding, errors='replace') as f:
                raw = f.readlines()

            # Walk through the file looking for a header row that actually
            # produces ≥ 2 parseable CSV columns.
            # ICICI files have a "Transaction Details:" label line (1 field only)
            # BEFORE the real header — we must skip past it.
            search_start = 0
            found_df = None
            while search_start < len(raw):
                header_idx = None
                for i in range(search_start, len(raw)):
                    lower = raw[i].lower()
                    hits = sum(1 for s in HEADER_SIGNALS if s in lower)
                    if hits >= 2:
                        header_idx = i
                        break

                if header_idx is None:
                    break  # no more candidates

                # Find cutoff row (bank "message" section, disclaimers, etc.)
                cutoff_idx = len(raw)
                for i in range(header_idx + 1, len(raw)):
                    ll = raw[i].lower().strip().strip('"')
                    if any(s in ll for s in CUTOFF_SIGNALS):
                        cutoff_idx = i
                        break

                snippet = ''.join(raw[header_idx:cutoff_idx])
                try:
                    df = pd.read_csv(io.StringIO(snippet), dtype=str)
                    # Strip surrounding quotes from column names (ICICI wraps them)
                    df.columns = df.columns.str.strip().str.strip('"').str.strip()
                    if len(df.columns) >= 2 and len(df) > 0:
                        found_df = df
                        break
                except Exception:
                    pass

                # This candidate didn't work — try the next row
                search_start = header_idx + 1

            if found_df is not None:
                return found_df

            # Fallback: try first few rows as-is
            for skip in (0, 1, 2, 3):
                try:
                    df = pd.read_csv(filepath, encoding=encoding,
                                     skiprows=skip, dtype=str)
                    df.columns = df.columns.str.strip()
                    if len(df.columns) >= 2 and len(df) > 0:
                        return df
                except Exception:
                    continue

        except Exception:
            continue
    return None


# ── Excel ─────────────────────────────────────────────────────────────────────

def parse_excel(filepath: str, account_id: int, statement_file: str,
                currency: str = 'USD') -> tuple[list, int, int]:
    import pandas as pd
    df = None
    for skip in (0, 1, 2, 3):
        try:
            df = pd.read_excel(filepath, skiprows=skip, dtype=str)
            df.columns = df.columns.str.strip()
            if len(df.columns) >= 2 and len(df) > 0:
                break
        except Exception:
            continue
    if df is None or df.empty:
        return [], 0, 0
    return _df_to_transactions(df, account_id, statement_file, source='Excel', currency=currency)


# ── PDF ───────────────────────────────────────────────────────────────────────

def parse_pdf(filepath: str, account_id: int, statement_file: str,
              currency: str = 'USD') -> tuple[list, int, int]:
    """
    Extract transactions from a bank statement PDF.
    Strategy 1 – table extraction via pdfplumber (structured statements).
    Strategy 2 – regex line scan of raw text (fallback for all other layouts).
    """
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("pdfplumber is not installed. Run: pip3 install pdfplumber")

    # Strategy 1: table extraction
    rows = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                if not table:
                    continue
                for row in table:
                    if row:
                        rows.append([str(c).strip() if c else '' for c in row])

    if rows:
        try:
            result = _pdf_rows_to_transactions(rows, account_id, statement_file, currency)
            if result[1] > 0 or result[2] > 0:
                return result
        except Exception:
            pass  # table had no usable columns — fall through

    # Strategy 2: text scan
    return _pdf_text_to_transactions(filepath, account_id, statement_file, currency)


def _pdf_rows_to_transactions(rows: list, account_id: int, statement_file: str, currency: str = 'USD'):
    """Convert pdfplumber table rows → DataFrame → transactions."""
    import pandas as pd

    if not rows:
        return [], 0, 0

    # Find the header row (must contain at least one recognisable column word)
    HEADER_WORDS = {'date', 'description', 'amount', 'debit', 'credit', 'memo',
                    'payee', 'transaction', 'withdrawal', 'deposit', 'charges'}
    header_idx = None
    for i, row in enumerate(rows):
        if any(w in ' '.join(row).lower() for w in HEADER_WORDS):
            header_idx = i
            break

    if header_idx is None:
        return [], 0, 0  # no recognisable header — let text fallback handle it

    headers   = rows[header_idx]
    data_rows = rows[header_idx + 1:]

    # Reject tables where all headers are blank
    non_blank = [h for h in headers if h.strip()]
    if len(non_blank) < 2:
        return [], 0, 0

    # Pad/trim rows to header width
    n = len(headers)
    cleaned = [((r + [''] * n)[:n]) for r in data_rows if any(c.strip() for c in r)]
    if not cleaned:
        return [], 0, 0

    df = pd.DataFrame(cleaned, columns=headers)
    df.columns = df.columns.str.strip()
    return _df_to_transactions(df, account_id, statement_file, source='PDF-table', currency=currency)


def _pdf_text_to_transactions(filepath: str, account_id: int, statement_file: str, currency: str = 'USD'):
    """
    Regex line-scan fallback for non-tabular PDFs.
    Handles two line formats:
      A) BofA / 2-date style:  MM/DD  MM/DD  DESCRIPTION  [REF4]  [ACCT4]  AMOUNT
      B) Generic dated lines:  DATE  DESCRIPTION  AMOUNT
    Year is inferred from the statement period header when no year is present.
    Negative amounts are treated as credits (payments/refunds).
    """
    import re
    import pdfplumber
    from datetime import datetime as _dt

    # ── Extract all text ────────────────────────────────────────────────────────
    text_lines = []
    header_text = ''
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            t = page.extract_text()
            if t:
                text_lines.extend(t.splitlines())
                if i < 4:
                    header_text += t + '\n'

    # ── Infer statement year + month→year mapping ───────────────────────────────
    MNAME = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
             'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12,
             'january':1,'february':2,'march':3,'april':4,'june':6,
             'july':7,'august':8,'september':9,'october':10,'november':11,'december':12}

    stmt_year    = _dt.now().year
    start_month  = None
    end_month    = None

    # Pattern: "December 27 - January 26, 2026" or "01/27/2026 - 02/26/2026"
    period_m = re.search(
        r'([A-Za-z]{3,9})\s+\d{1,2}\s*[-–]\s*([A-Za-z]{3,9})\s+\d{1,2},?\s*(20\d{2})',
        header_text, re.IGNORECASE
    )
    if period_m:
        start_month = MNAME.get(period_m.group(1).lower()[:3])
        end_month   = MNAME.get(period_m.group(2).lower()[:3])
        stmt_year   = int(period_m.group(3))
    else:
        # Fallback: grab the highest 4-digit year in the header
        years = re.findall(r'\b(20\d{2})\b', header_text[:2000])
        if years:
            stmt_year = max(int(y) for y in years)

    def _year_for_month(m_int):
        """Return correct year for a given month number, handling year-boundary statements."""
        if start_month and end_month and start_month > end_month:
            # Statement crosses a year boundary (e.g. Dec 2025 → Jan 2026)
            if m_int >= start_month:          # Dec → previous year
                return stmt_year - 1
        return stmt_year

    # ── Line patterns ───────────────────────────────────────────────────────────
    # BofA pattern: MM/DD  MM/DD  ...description...  AMOUNT  (amount at end, possibly negative)
    bofa_re = re.compile(
        r'^(\d{1,2}/\d{1,2})\s+(\d{1,2}/\d{1,2})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*$'
    )
    # ICICI PDF pattern: DD/MM/YYYY  REFNO  DESCRIPTION  REWARD_PTS  AMOUNT  [CR]
    # e.g. "04/04/2026 13174870804 RS BROTHERS RETAIL INDI MEDAK IN 27 2,717.00"
    # e.g. "24/04/2026 13293792033 BBPS Payment received 0 649.00 CR"
    icici_pdf_re = re.compile(
        r'^(\d{2}/\d{2}/\d{4})\s+\d+\s+(.+?)\s+(-?\d+)\s+([\d,]+\.\d{2})\s*(CR)?\s*$',
        re.IGNORECASE
    )
    # Generic date at start of line
    generic_date_re = re.compile(
        r'^(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}'
        r'|[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4}'
        r'|[A-Za-z]{3,9}\.?\s+\d{1,2}(?!\s*\d)'
        r'|\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4})'
    )
    any_amount_re = re.compile(r'-?\$?([\d,]+\.\d{2})')

    # Lines to skip for GENERIC (non-BofA) format only
    SKIP_GENERIC = (
        'total ', 'subtotal', 'balance', 'account number', 'credit limit',
        'minimum payment', 'opening balance', 'closing balance',
        'new balance', 'previous balance', 'finance charge', 'date description',
        'transaction date', 'posting date', 'page ', 'continued',
        'purchases and adjustments', 'payments and other',
        'total payments', 'total purchases', 'total interest', 'year-to-date',
        'annual percentage', 'apr type', 'balance transfers', 'cash advances',
        'totals year', 'interest charge calculation', 'daily periodic', 'promotional',
    )
    # Lines to skip even inside BofA transactions (zero-value system entries)
    SKIP_BOFA_DESC = ('interest charged on', 'interest charged on purchases',
                      'interest charged on balance', 'interest charged on dir',
                      'interest charged on bank')

    transactions = []
    inserted = skipped = 0

    for line in text_lines:
        line = line.strip()
        if not line or len(line) < 8:
            continue

        txn_type    = 'debit'
        date        = None
        description = None
        amount      = None

        # ── Try ICICI PDF format: DD/MM/YYYY REFNO DESC REWARD AMOUNT [CR] ──────
        im = icici_pdf_re.match(line)
        if im:
            # Always DD/MM/YYYY — parse directly to avoid MM/DD/YYYY misread
            try:
                date = _dt.strptime(im.group(1), '%d/%m/%Y').strftime('%Y-%m-%d')
            except ValueError:
                continue
            if not date:
                continue
            description = re.sub(r'\s{2,}', ' ', im.group(2)).strip()
            raw = _parse_amount(im.group(4))
            if raw is None or raw == 0:
                continue
            is_cr = bool(im.group(5))                # "CR" present → credit
            txn_type = 'credit' if is_cr else 'debit'
            amount   = abs(raw)

            txn_month = int(date[5:7])
            txn_year  = int(date[:4])
            if currency == 'INR':
                inr_rate    = db.get_inr_rate_for_month(txn_year, txn_month)
                usd_amount  = round(amount * inr_rate, 4)
                orig_amount = amount
                orig_curr   = 'INR'
            else:
                usd_amount  = amount
                orig_amount = None
                orig_curr   = None

            if db.get_duplicate_check(account_id, date, description, usd_amount):
                skipped += 1
                continue

            if txn_type == 'credit':
                category  = _classify_credit(description)
                is_wasted = False
            else:
                category, is_wasted = categorize(description)

            transactions.append({
                'account_id':    account_id,
                'date':          date,
                'description':   description,
                'amount':        usd_amount,
                'category':      category,
                'is_wasted':     int(is_wasted),
                'statement_file': statement_file,
                'currency':      'USD',
                'txn_type':      txn_type,
                'orig_amount':   orig_amount,
                'orig_currency': orig_curr,
            })
            inserted += 1
            continue

        # ── Try BofA 2-date format FIRST (before SKIP filtering) ─────────────
        # BofA lines always: MM/DD MM/DD DESCRIPTION AMOUNT
        # We must not SKIP them based on description content (e.g. "late fee for payment due")
        bm = bofa_re.match(line)
        if bm:
            txn_date_str  = bm.group(1)   # MM/DD  (transaction date)
            # bm.group(2) is posting date — ignored
            middle        = bm.group(3)
            amount_str    = bm.group(4)

            # Parse transaction date (MM/DD) — add inferred year
            parts = txn_date_str.split('/')
            m_int, d_int = int(parts[0]), int(parts[1])
            year = _year_for_month(m_int)
            date = _parse_date(f"{m_int:02d}/{d_int:02d}/{year}")

            # Amount
            raw = _parse_amount(amount_str)
            if raw is None or raw == 0:
                continue
            if raw < 0:
                txn_type = 'credit'
                amount   = abs(raw)
            else:
                amount = raw

            # Clean description — strip trailing reference/account 4-digit groups
            # e.g. "AMAZON MARK* 2O4J03X63 AMAZON.COM/MAWA 9049 7729"
            #   → "AMAZON MARK* 2O4J03X63 AMAZON.COM/MAWA"
            desc_raw = re.sub(r'(\s+\d{4}){1,2}\s*$', '', middle).strip()
            description = re.sub(r'\s{2,}', ' ', desc_raw).strip()

        else:
            # ── Generic date-led line — apply SKIP filter here ────────────────
            ll = line.lower()
            if any(s in ll for s in SKIP_GENERIC):
                continue
            gm = generic_date_re.match(line)
            if not gm:
                continue

            date_str = gm.group(0)
            date     = _parse_date(date_str)
            if not date:
                continue

            rest = line[len(date_str):]
            # Amount = last decimal number on line (handles "... balance charge")
            am = re.search(r'(-?\$?[\d,]+\.\d{2})\s*$', rest)
            if not am:
                continue
            raw = _parse_amount(am.group(1))
            if raw is None or raw == 0:
                continue
            if raw < 0:
                txn_type = 'credit'
                amount   = abs(raw)
            else:
                amount = raw

            desc_raw    = rest[:am.start()].strip(' \t|,')
            description = re.sub(r'\s{2,}', ' ', desc_raw).strip()

        if not date or not description or len(description) < 2:
            continue

        # Skip zero-amount system entries (interest at 0.00, etc.)
        if amount == 0:
            continue
        dl = description.lower()
        if any(x in dl for x in SKIP_BOFA_DESC):
            continue

        # ── INR → USD conversion using rate for that month ───────────────────
        txn_month = int(date[5:7])
        txn_year  = int(date[:4])
        if currency == 'INR':
            inr_rate    = db.get_inr_rate_for_month(txn_year, txn_month)
            usd_amount  = round(amount * inr_rate, 4)
            orig_amount = amount
            orig_curr   = 'INR'
        else:
            usd_amount  = amount
            orig_amount = None
            orig_curr   = None

        if db.get_duplicate_check(account_id, date, description, usd_amount):
            skipped += 1
            continue

        if txn_type == 'credit':
            category  = _classify_credit(description)
            is_wasted = False
        else:
            category, is_wasted = categorize(description)

        transactions.append({
            'account_id':    account_id,
            'date':          date,
            'description':   description,
            'amount':        usd_amount,
            'category':      category,
            'is_wasted':     int(is_wasted),
            'statement_file': statement_file,
            'currency':      'USD',
            'txn_type':      txn_type,
            'orig_amount':   orig_amount,
            'orig_currency': orig_curr,
        })
        inserted += 1

    if transactions:
        db.add_transactions_bulk(transactions)

    return transactions, inserted, skipped


# ── Shared DataFrame processor ────────────────────────────────────────────────

def _classify_credit(description: str) -> str:
    """Return 'Payments' for card payments, 'Refunds' for merchant reversals."""
    dl = description.lower()
    PAYMENT_SIGNALS = ('payment', 'paid', 'remittance', 'neft', 'imps', 'rtgs',
                       'bbps', 'autopay', 'auto pay', 'thank you', 'pymt')
    return 'Payments' if any(s in dl for s in PAYMENT_SIGNALS) else 'Refunds'


def _df_to_transactions(df, account_id: int, statement_file: str,
                        source: str = '', currency: str = 'USD') -> tuple[list, int, int]:
    date_col, desc_col, amount_col, sign_col = _detect_columns(df)
    if not date_col or not desc_col or not amount_col:
        raise ValueError(
            f"Could not detect date/description/amount columns in {source}. "
            f"Columns found: {list(df.columns)}"
        )

    transactions = []
    skipped = inserted = 0

    # Detect if date column uses DD/MM/YYYY (ICICI new format) vs MM/DD/YYYY.
    # If any day > 12 appears in first position, it's unambiguously DD/MM/YYYY.
    import re as _re
    _dd_mm_yyyy = False
    for _sv in df[date_col].dropna().head(30):
        _m = _re.match(r'^(\d{1,2})/(\d{1,2})/\d{4}$', str(_sv).strip())
        if _m and int(_m.group(1)) > 12:
            _dd_mm_yyyy = True
            break

    for _, row in df.iterrows():
        try:
            raw_date = str(row[date_col]).strip()
            if _dd_mm_yyyy:
                try:
                    from datetime import datetime as _dtc
                    date = _dtc.strptime(raw_date, '%d/%m/%Y').strftime('%Y-%m-%d')
                except ValueError:
                    date = _parse_date(raw_date)
            else:
                date = _parse_date(raw_date)
            if not date:
                continue

            description = str(row[desc_col]).strip()
            if not description or description.lower() in ('nan', 'description', ''):
                continue

            txn_type = 'debit'
            amount = None

            if isinstance(amount_col, tuple):
                # Split debit / credit columns
                debit_col, credit_col = amount_col
                debit  = _parse_amount(row.get(debit_col,  ''))
                credit = _parse_amount(row.get(credit_col, ''))
                if debit and debit > 0:
                    amount, txn_type = debit, 'debit'
                elif credit and credit > 0:
                    amount, txn_type = credit, 'credit'
                else:
                    continue
            else:
                raw = _parse_amount(row[amount_col])
                if raw is None:
                    continue
                raw = abs(raw) if raw else 0
                if raw == 0:
                    continue

                # ICICI new format: BillingAmountSign has "CR" for credits, "" for debits
                if sign_col:
                    sign_val = str(row.get(sign_col, '')).strip().upper()
                    if sign_val == 'CR':
                        txn_type = 'credit'
                    elif sign_val == 'DR':
                        txn_type = 'debit'
                    else:
                        # Old ICICI / other formats: check original sign from raw value
                        orig_raw = _parse_amount(row[amount_col])
                        txn_type = 'credit' if (orig_raw is not None and orig_raw < 0) else 'debit'
                else:
                    orig_raw = _parse_amount(row[amount_col])
                    if orig_raw is not None and orig_raw < 0:
                        txn_type = 'credit'
                amount = raw

            if amount == 0:
                continue

            # Convert to USD using the monthly rate for that transaction's month
            if currency == 'INR':
                txn_m = int(date[5:7])
                txn_y = int(date[:4])
                inr_rate     = db.get_inr_rate_for_month(txn_y, txn_m)
                usd_amount   = round(amount * inr_rate, 4)
                orig_amount  = amount
                orig_currency = 'INR'
            else:
                usd_amount   = amount
                orig_amount  = None
                orig_currency = None

            if db.get_duplicate_check(account_id, date, description, usd_amount):
                skipped += 1
                continue

            if txn_type == 'credit':
                category  = _classify_credit(description)
                is_wasted = False
            else:
                category, is_wasted = categorize(description)

            transactions.append({
                'account_id':   account_id,
                'date':         date,
                'description':  description,
                'amount':       usd_amount,
                'category':     category,
                'is_wasted':    int(is_wasted),
                'statement_file': statement_file,
                'currency':     'USD',
                'txn_type':     txn_type,
                'orig_amount':  orig_amount,
                'orig_currency': orig_currency,
            })
            inserted += 1
        except Exception:
            continue

    if transactions:
        db.add_transactions_bulk(transactions)

    return transactions, inserted, skipped


# ── Column detection ──────────────────────────────────────────────────────────

def _detect_columns(df):
    cols_lower = {c.lower().strip(): c for c in df.columns}

    # ── Date column ─────────────────────────────────────────────────────────────
    date_col = None
    for c in ('transaction date', 'trans date', 'trans. date', 'value date',
              'txn date', 'tran date', 'date', 'posted date', 'post date', 'posting date'):
        if c in cols_lower:
            date_col = cols_lower[c]
            break

    # ── Description column ───────────────────────────────────────────────────────
    desc_col = None
    for c in ('description', 'transaction description', 'transaction details',
              'transaction narration', 'narration', 'particulars', 'particular',
              'memo', 'payee', 'merchant', 'name', 'details', 'narrative',
              'remarks', 'chq/ref no.description', 'chq / ref no. description',
              'remarks / description'):
        if c in cols_lower:
            desc_col = cols_lower[c]
            break

    # ── Amount column ────────────────────────────────────────────────────────────
    DEBIT_NAMES  = ('debit', 'debit amount', 'withdrawal', 'withdrawals',
                    'withdrawal amt.', 'withdrawal amt', 'dr', 'dr amount')
    CREDIT_NAMES = ('credit', 'credit amount', 'deposit', 'deposits',
                    'deposit amt.', 'deposit amt', 'cr', 'cr amount')

    has_debit  = any(c in cols_lower for c in DEBIT_NAMES)
    has_credit = any(c in cols_lower for c in CREDIT_NAMES)

    amount_col = None
    # sign_col: a separate column that holds 'CR'/'DR'/''/sign indicators
    sign_col   = None

    if has_debit:
        debit_col  = next(cols_lower[c] for c in DEBIT_NAMES  if c in cols_lower)
        credit_col = next((cols_lower[c] for c in CREDIT_NAMES if c in cols_lower), None)
        amount_col = (debit_col, credit_col) if credit_col else debit_col
    else:
        # Exact matches — NOTE: 'billingamountsign' intentionally excluded;
        # we use Amount(in Rs) as the amount and BillingAmountSign as the sign indicator
        for c in ('amount', 'transaction amount', 'charges', 'charge amount',
                  'total', 'net amount', 'billing amount sign',
                  'inr amount', 'rs amount'):
            if c in cols_lower:
                amount_col = cols_lower[c]
                break

        # Fuzzy: first column whose name contains 'amount' but not 'intl'/'reward'/'billing'/'point'
        if not amount_col:
            for col_lower, col_orig in cols_lower.items():
                if ('amount' in col_lower and
                        not any(x in col_lower for x in ('intl', 'reward', 'point', 'billing'))):
                    amount_col = col_orig
                    break

        # ICICI BillingAmountSign — use as sign indicator if present
        if 'billingamountsign' in cols_lower:
            sign_col = cols_lower['billingamountsign']
        elif 'cr/dr' in cols_lower:
            sign_col = cols_lower['cr/dr']
        elif 'dr/cr' in cols_lower:
            sign_col = cols_lower['dr/cr']

        # Last resort amount
        if not amount_col:
            for col_lower, col_orig in cols_lower.items():
                if 'amount' in col_lower:
                    amount_col = col_orig
                    break

    return date_col, desc_col, amount_col, sign_col


# ── Date / amount parsers ─────────────────────────────────────────────────────

def _parse_date(raw: str) -> str | None:
    from datetime import datetime
    raw = raw.strip().replace('"', '').replace('*', '').strip()
    for fmt in ('%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%d-%m-%Y',
                '%b %d, %Y', '%B %d, %Y', '%m-%d-%Y', '%d/%m/%Y',
                '%Y/%m/%d', '%d %b %Y', '%d %B %Y', '%b %d %Y',
                '%d/%m/%y', '%d-%b-%Y', '%d-%b-%y'):
        try:
            return datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def _parse_amount(raw) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(',', '').replace('$', '').replace('"', '').strip()
    if not s or s.lower() in ('nan', '', '-', 'n/a', 'none'):
        return None
    # Handle parentheses as negative: (49.99) → -49.99
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def import_web_categories():
    """Bulk-import the WEB_CATEGORIES keyword rules into the DB."""
    for category, keywords in WEB_CATEGORIES.items():
        for kw in keywords:
            db.add_category_rule(kw.lower(), category)
    return sum(len(v) for v in WEB_CATEGORIES.values())
