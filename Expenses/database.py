import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'expenses.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT 'credit',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'Uncategorized',
            is_wasted INTEGER DEFAULT 0,
            statement_file TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS category_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            category TEXT NOT NULL,
            is_case_sensitive INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wasted_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            reason TEXT,
            exclude_if_contains TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)

    # Migrate existing transactions table — add new columns if not present
    existing = {row[1] for row in c.execute("PRAGMA table_info(transactions)")}
    if 'currency' not in existing:
        c.execute("ALTER TABLE transactions ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD'")
    if 'txn_type' not in existing:
        c.execute("ALTER TABLE transactions ADD COLUMN txn_type TEXT NOT NULL DEFAULT 'debit'")
    if 'orig_amount' not in existing:
        c.execute("ALTER TABLE transactions ADD COLUMN orig_amount REAL")
    if 'orig_currency' not in existing:
        c.execute("ALTER TABLE transactions ADD COLUMN orig_currency TEXT")

    # Performance indexes
    for _sql in [
        "CREATE INDEX IF NOT EXISTS idx_txn_date     ON transactions(date)",
        "CREATE INDEX IF NOT EXISTS idx_txn_account  ON transactions(account_id)",
        "CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category)",
        "CREATE INDEX IF NOT EXISTS idx_txn_type     ON transactions(txn_type)",
        "CREATE INDEX IF NOT EXISTS idx_txn_wasted   ON transactions(is_wasted)",
        "CREATE INDEX IF NOT EXISTS idx_txn_orig_cur ON transactions(orig_currency)",
    ]:
        c.execute(_sql)

    # Deduplicate category_rules (keep highest id per keyword), then enforce uniqueness
    c.execute("DELETE FROM category_rules WHERE id NOT IN "
              "(SELECT MAX(id) FROM category_rules GROUP BY keyword)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cat_rules_keyword ON category_rules(keyword)")

    # Seed default INR rate if missing
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('inr_usd_rate', '0.012')")

    # Seed default wasted keywords (tobacco + gas stations except Costco)
    tobacco_keywords = [
        ('tobacco', 'Tobacco products', None),
        ('smoke shop', 'Tobacco/smoking', None),
        ('cigarette', 'Tobacco products', None),
        ('cigar', 'Tobacco products', None),
        ('vape', 'Vaping products', None),
        ('nicotine', 'Nicotine products', None),
        ('smokeless', 'Tobacco products', None),
        ('chewing tobacco', 'Tobacco products', None),
    ]
    gas_keywords = [
        ('shell', 'Gas station', 'costco'),
        ('chevron', 'Gas station', 'costco'),
        ('bp ', 'Gas station', 'costco'),
        ('exxon', 'Gas station', 'costco'),
        ('mobil', 'Gas station', 'costco'),
        ('arco', 'Gas station', 'costco'),
        ('circle k', 'Gas station', 'costco'),
        ('speedway', 'Gas station', 'costco'),
        ('marathon', 'Gas station', 'costco'),
        ('sunoco', 'Gas station', 'costco'),
        ('valero', 'Gas station', 'costco'),
        ('citgo', 'Gas station', 'costco'),
        ('wawa', 'Gas station', 'costco'),
        ('kwik trip', 'Gas station', 'costco'),
        ('pilot fuel', 'Gas station', 'costco'),
        ('love\'s travel', 'Gas station', 'costco'),
        ('76 gas', 'Gas station', 'costco'),
        ('quiktrip', 'Gas station', 'costco'),
        ('casey\'s', 'Gas station', 'costco'),
        ('murphy gas', 'Gas station', 'costco'),
        ('murphy usa', 'Gas station', 'costco'),
        ('racetrac', 'Gas station', 'costco'),
        ('sheetz', 'Gas station', 'costco'),
        ('fuel station', 'Gas station', 'costco'),
        ('gas station', 'Gas station', 'costco'),
    ]
    for kw, reason, exclude in tobacco_keywords + gas_keywords:
        try:
            c.execute(
                "INSERT OR IGNORE INTO wasted_keywords (keyword, reason, exclude_if_contains) VALUES (?, ?, ?)",
                (kw, reason, exclude)
            )
        except Exception:
            pass

    # Seed default category rules
    default_rules = [
        # Food & Dining
        ('mcdonald', 'Food & Dining'), ('starbucks', 'Food & Dining'),
        ('subway', 'Food & Dining'), ('chipotle', 'Food & Dining'),
        ('doordash', 'Food & Dining'), ('uber eats', 'Food & Dining'),
        ('grubhub', 'Food & Dining'), ('postmates', 'Food & Dining'),
        ('pizza', 'Food & Dining'), ('restaurant', 'Food & Dining'),
        ('cafe', 'Food & Dining'), ('diner', 'Food & Dining'),
        ('taco bell', 'Food & Dining'), ('burger king', 'Food & Dining'),
        ('wendy\'s', 'Food & Dining'), ('chick-fil-a', 'Food & Dining'),
        ('panera', 'Food & Dining'), ('domino', 'Food & Dining'),
        ('dunkin', 'Food & Dining'), ('in-n-out', 'Food & Dining'),
        # Groceries
        ('walmart', 'Groceries'), ('costco', 'Groceries'),
        ('target', 'Groceries'), ('kroger', 'Groceries'),
        ('safeway', 'Groceries'), ('whole foods', 'Groceries'),
        ('trader joe', 'Groceries'), ('aldi', 'Groceries'),
        ('publix', 'Groceries'), ('heb', 'Groceries'),
        ('grocery', 'Groceries'), ('supermarket', 'Groceries'),
        ('food lion', 'Groceries'), ('sprouts', 'Groceries'),
        # Shopping
        ('amazon', 'Shopping'), ('ebay', 'Shopping'),
        ('best buy', 'Shopping'), ('ikea', 'Shopping'),
        ('tj maxx', 'Shopping'), ('marshalls', 'Shopping'),
        ('ross', 'Shopping'), ('macy\'s', 'Shopping'),
        ('nordstrom', 'Shopping'), ('gap', 'Shopping'),
        ('old navy', 'Shopping'), ('h&m', 'Shopping'),
        ('zara', 'Shopping'), ('nike', 'Shopping'),
        ('apple store', 'Shopping'),
        # Transportation
        ('uber', 'Transportation'), ('lyft', 'Transportation'),
        ('parking', 'Transportation'), ('toll', 'Transportation'),
        ('metro', 'Transportation'), ('transit', 'Transportation'),
        ('amtrak', 'Transportation'), ('greyhound', 'Transportation'),
        ('taxi', 'Transportation'), ('zipcar', 'Transportation'),
        # Travel
        ('airline', 'Travel'), ('hotel', 'Travel'),
        ('airbnb', 'Travel'), ('hilton', 'Travel'),
        ('marriott', 'Travel'), ('delta', 'Travel'),
        ('united airlines', 'Travel'), ('american airlines', 'Travel'),
        ('southwest', 'Travel'), ('expedia', 'Travel'),
        ('booking.com', 'Travel'), ('vrbo', 'Travel'),
        # Utilities
        ('electric', 'Utilities'), ('gas bill', 'Utilities'),
        ('water bill', 'Utilities'), ('internet', 'Utilities'),
        ('at&t', 'Utilities'), ('verizon', 'Utilities'),
        ('t-mobile', 'Utilities'), ('sprint', 'Utilities'),
        ('comcast', 'Utilities'), ('xfinity', 'Utilities'),
        ('spectrum', 'Utilities'), ('utility', 'Utilities'),
        ('pg&e', 'Utilities'), ('con ed', 'Utilities'),
        # Entertainment
        ('netflix', 'Entertainment'), ('spotify', 'Entertainment'),
        ('hulu', 'Entertainment'), ('disney+', 'Entertainment'),
        ('apple tv', 'Entertainment'), ('hbo', 'Entertainment'),
        ('amazon prime video', 'Entertainment'), ('youtube', 'Entertainment'),
        ('cinema', 'Entertainment'), ('theater', 'Entertainment'),
        ('amc ', 'Entertainment'), ('regal', 'Entertainment'),
        ('ticketmaster', 'Entertainment'), ('stub hub', 'Entertainment'),
        # Healthcare
        ('pharmacy', 'Healthcare'), ('cvs', 'Healthcare'),
        ('walgreens', 'Healthcare'), ('rite aid', 'Healthcare'),
        ('doctor', 'Healthcare'), ('hospital', 'Healthcare'),
        ('dental', 'Healthcare'), ('vision', 'Healthcare'),
        ('optometrist', 'Healthcare'), ('urgent care', 'Healthcare'),
        ('medical', 'Healthcare'), ('health', 'Healthcare'),
        # Fitness
        ('gym', 'Fitness'), ('planet fitness', 'Fitness'),
        ('24 hour fitness', 'Fitness'), ('la fitness', 'Fitness'),
        ('peloton', 'Fitness'), ('yoga', 'Fitness'),
        # Finance & Banking
        ('payment', 'Finance'), ('transfer', 'Finance'),
        ('bank fee', 'Finance'), ('interest charge', 'Finance'),
        ('annual fee', 'Finance'), ('late fee', 'Finance'),
        ('zelle', 'Finance'), ('venmo', 'Finance'),
        ('paypal', 'Finance'), ('cash app', 'Finance'),
        # Insurance
        ('insurance', 'Insurance'), ('geico', 'Insurance'),
        ('state farm', 'Insurance'), ('allstate', 'Insurance'),
        ('progressive', 'Insurance'), ('aaa', 'Insurance'),
        # Education
        ('tuition', 'Education'), ('udemy', 'Education'),
        ('coursera', 'Education'), ('skillshare', 'Education'),
        ('school', 'Education'), ('college', 'Education'),
        # Home
        ('rent', 'Home'), ('mortgage', 'Home'),
        ('home depot', 'Home'), ('lowe\'s', 'Home'),
        ('pest control', 'Home'), ('lawn', 'Home'),
        ('cleaning', 'Home'),
        # Personal Care
        ('salon', 'Personal Care'), ('barber', 'Personal Care'),
        ('haircut', 'Personal Care'), ('spa', 'Personal Care'),
        ('nail', 'Personal Care'),
        # Gas & Auto
        ('costco gas', 'Gas & Auto'), ('costco whse', 'Groceries'),
        ('costco fuel', 'Gas & Auto'), ('tesla', 'Gas & Auto'),
        ('chargepoint', 'Gas & Auto'), ('electrify', 'Gas & Auto'),
        ('safelite', 'Gas & Auto'), ('firestone', 'Gas & Auto'),
        ('autozone', 'Gas & Auto'), ('jiffy lube', 'Gas & Auto'),
        ('car wash', 'Gas & Auto'), ('oil change', 'Gas & Auto'),
        # Travel / Insurance (unique entries only — geico/state farm/allstate etc. already above)
        ('travelers', 'Insurance'), ('travelers per ins', 'Insurance'),
        ('travelers ins', 'Insurance'),
        # Finance / Banking (unique entries only — late fee/wire transfer already above)
        ('cash rewards', 'Finance'), ('statement credit', 'Finance'),
        ('payment from chk', 'Finance'), ('ach payment', 'Finance'),
        # Amazon
        ('amazon mark', 'Shopping'), ('amazon mktpl', 'Shopping'),
        ('amzn.com', 'Shopping'), ('amazon.com', 'Shopping'),
        ('amazon prime', 'Subscriptions'), ('amazon music', 'Entertainment'),
        # Misc well-known merchants
        ('vinhistory', 'Auto Services'), ('vin history', 'Auto Services'),
        ('carfax', 'Auto Services'), ('autocheck', 'Auto Services'),
    ]
    for kw, cat in default_rules:
        try:
            c.execute(
                "INSERT OR IGNORE INTO category_rules (keyword, category) VALUES (?, ?)",
                (kw, cat)
            )
        except Exception:
            pass

    conn.commit()
    conn.close()


# ── Accounts ──────────────────────────────────────────────────────────────────

def get_accounts():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_account(account_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_account(name, acct_type='credit'):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO accounts (name, type) VALUES (?, ?)", (name, acct_type))
        conn.commit()
        account_id = conn.execute("SELECT id FROM accounts WHERE name=?", (name,)).fetchone()['id']
    finally:
        conn.close()
    return account_id


def get_or_create_account(name, acct_type='credit'):
    conn = get_conn()
    row = conn.execute("SELECT id FROM accounts WHERE name=?", (name,)).fetchone()
    if row:
        conn.close()
        return row['id']
    conn.execute("INSERT INTO accounts (name, type) VALUES (?, ?)", (name, acct_type))
    conn.commit()
    row = conn.execute("SELECT id FROM accounts WHERE name=?", (name,)).fetchone()
    account_id = row['id']
    conn.close()
    return account_id


def delete_account(account_id):
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE account_id=?", (account_id,))
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()
    conn.close()


# ── Transactions ──────────────────────────────────────────────────────────────

def add_transaction(account_id, date, description, amount, category, is_wasted, statement_file=None):
    conn = get_conn()
    conn.execute(
        """INSERT INTO transactions (account_id, date, description, amount, category, is_wasted, statement_file)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (account_id, date, description, amount, category, int(is_wasted), statement_file)
    )
    conn.commit()
    conn.close()


def add_transactions_bulk(rows):
    conn = get_conn()
    conn.executemany(
        """INSERT INTO transactions
             (account_id, date, description, amount, category, is_wasted,
              statement_file, currency, txn_type, orig_amount, orig_currency)
           VALUES
             (:account_id, :date, :description, :amount, :category, :is_wasted,
              :statement_file,
              COALESCE(:currency, 'USD'),
              COALESCE(:txn_type, 'debit'),
              :orig_amount,
              :orig_currency)""",
        [{**r,
          'currency':      r.get('currency', 'USD'),
          'txn_type':      r.get('txn_type', 'debit'),
          'orig_amount':   r.get('orig_amount'),
          'orig_currency': r.get('orig_currency'),
         } for r in rows]
    )
    conn.commit()
    conn.close()


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key: str, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key,value,updated_at) VALUES (?,?,datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value)
    )
    conn.commit()
    conn.close()


def get_inr_rate() -> float:
    return float(get_setting('inr_usd_rate', '0.012'))


def get_inr_rate_for_month(year: int, month: int) -> float:
    """Return the INR→USD rate for a specific month/year.
    Falls back to the global rate if no monthly override exists."""
    key = f'inr_usd_rate_{year}_{month:02d}'
    val = get_setting(key)
    if val:
        return float(val)
    return get_inr_rate()


def set_monthly_inr_rate(year: int, month: int, rate: float):
    set_setting(f'inr_usd_rate_{year}_{month:02d}', str(rate))


def delete_monthly_inr_rate(year: int, month: int):
    conn = get_conn()
    conn.execute("DELETE FROM settings WHERE key=?", (f'inr_usd_rate_{year}_{month:02d}',))
    conn.commit()
    conn.close()


def get_all_monthly_inr_rates() -> list:
    """Return all stored monthly overrides sorted by date."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE 'inr_usd_rate_____' OR key LIKE 'inr_usd_rate_______' ORDER BY key"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        # key format: inr_usd_rate_YYYY_MM
        parts = r['key'].replace('inr_usd_rate_', '').split('_')
        if len(parts) == 2:
            result.append({'key': r['key'], 'year': parts[0], 'month': parts[1], 'rate': r['value']})
    return result


def _apply_period(sql, params, month, year):
    """Append date filter clauses. month=0 or None means whole year."""
    if month and int(month) != 0 and year:
        sql += " AND strftime('%m', t.date) = ? AND strftime('%Y', t.date) = ?"
        params += [f"{int(month):02d}", str(year)]
    elif year:
        sql += " AND strftime('%Y', t.date) = ?"
        params.append(str(year))
    return sql, params


def get_transactions(month=None, year=None, account_id=None, category=None,
                     txn_type=None, is_wasted=None, search=None, limit=None, offset=0):
    conn = get_conn()
    sql = """
        SELECT t.*, a.name as account_name, a.type as account_type
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        WHERE 1=1
    """
    params = []
    sql, params = _apply_period(sql, params, month, year)
    if account_id:
        sql += " AND t.account_id = ?"
        params.append(account_id)
    if category:
        sql += " AND t.category = ?"
        params.append(category)
    if txn_type:
        sql += " AND t.txn_type = ?"
        params.append(txn_type)
    if is_wasted is not None:
        sql += " AND t.is_wasted = ?"
        params.append(int(is_wasted))
    if search:
        sql += " AND t.description LIKE ?"
        params.append(f'%{search}%')
    sql += " ORDER BY t.date DESC"
    if limit:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_transactions(month=None, year=None, account_id=None, category=None,
                       txn_type=None, is_wasted=None, search=None):
    conn = get_conn()
    sql = "SELECT COUNT(*) FROM transactions t WHERE 1=1"
    params = []
    sql, params = _apply_period(sql, params, month, year)
    if account_id:
        sql += " AND t.account_id = ?"
        params.append(account_id)
    if category:
        sql += " AND t.category = ?"
        params.append(category)
    if txn_type:
        sql += " AND t.txn_type = ?"
        params.append(txn_type)
    if is_wasted is not None:
        sql += " AND t.is_wasted = ?"
        params.append(int(is_wasted))
    if search:
        sql += " AND t.description LIKE ?"
        params.append(f'%{search}%')
    count = conn.execute(sql, params).fetchone()[0]
    conn.close()
    return count


def get_transaction(txn_id):
    conn = get_conn()
    row = conn.execute(
        """SELECT t.*, a.name as account_name FROM transactions t
           JOIN accounts a ON a.id = t.account_id WHERE t.id=?""",
        (txn_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_transaction_category(txn_id, category, is_wasted):
    conn = get_conn()
    conn.execute(
        "UPDATE transactions SET category=?, is_wasted=? WHERE id=?",
        (category, int(is_wasted), txn_id)
    )
    conn.commit()
    conn.close()


def count_merchant_matches(keyword: str, exclude_id: int) -> int:
    """Count transactions whose description contains keyword (case-insensitive), excluding one row."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE lower(description) LIKE ? AND id != ?",
        (f'%{keyword.lower()}%', exclude_id)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def bulk_update_category_by_keyword(keyword: str, category: str, is_wasted: int, exclude_id: int) -> int:
    """Update category on all transactions whose description contains keyword. Returns rows changed."""
    conn = get_conn()
    cur = conn.execute(
        "UPDATE transactions SET category=?, is_wasted=? WHERE lower(description) LIKE ? AND id != ?",
        (category, int(is_wasted), f'%{keyword.lower()}%', exclude_id)
    )
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed


def delete_transaction(txn_id):
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
    conn.commit()
    conn.close()


def get_duplicate_check(account_id, date, description, amount):
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM transactions WHERE account_id=? AND date=? AND description=? AND amount=?",
        (account_id, date, description, amount)
    ).fetchone()
    conn.close()
    return row is not None


# ── Stats / Reports ───────────────────────────────────────────────────────────

# SQL expression to convert any transaction amount to USD
_USD = ("(amount * CASE WHEN currency='INR' THEN "
        "(SELECT CAST(value AS REAL) FROM settings WHERE key='inr_usd_rate') "
        "ELSE 1.0 END)")


def get_account_total(account_id, month, year):
    conn = get_conn()
    row = conn.execute(
        f"""SELECT COALESCE(SUM({_USD}), 0) as total FROM transactions
           WHERE account_id=? AND txn_type='debit'
           AND strftime('%m', date)=?
           AND strftime('%Y', date)=?""",
        (account_id, f"{int(month):02d}", str(year))
    ).fetchone()
    conn.close()
    return row['total'] if row else 0.0


def get_period_totals(month, year):
    """Returns debits, payments, refunds, wasted, loans for the period (all in USD)."""
    conn = get_conn()
    clause = ""
    params = []
    if month and int(month) != 0:
        clause = "AND strftime('%m', date)=? AND strftime('%Y', date)=?"
        params = [f"{int(month):02d}", str(year)]
    else:
        clause = "AND strftime('%Y', date)=?"
        params = [str(year)]
    row = conn.execute(
        f"""SELECT
            COALESCE(SUM(CASE WHEN txn_type='debit'  THEN {_USD} ELSE 0 END), 0) as debits,
            COALESCE(SUM(CASE WHEN txn_type='credit' THEN {_USD} ELSE 0 END), 0) as credits,
            COALESCE(SUM(CASE WHEN txn_type='credit' AND category='Payments' THEN {_USD} ELSE 0 END), 0) as payments,
            COALESCE(SUM(CASE WHEN txn_type='credit' AND category!='Payments' THEN {_USD} ELSE 0 END), 0) as refunds,
            COALESCE(SUM(CASE WHEN txn_type='loan'   THEN {_USD} ELSE 0 END), 0) as loans,
            COALESCE(SUM(CASE WHEN is_wasted=1 AND txn_type='debit' THEN {_USD} ELSE 0 END), 0) as wasted
           FROM transactions WHERE 1=1 {clause}""",
        params
    ).fetchone()
    conn.close()
    return dict(row) if row else {'debits': 0, 'credits': 0, 'payments': 0, 'refunds': 0, 'loans': 0, 'wasted': 0}


def get_category_breakdown(month, year):
    """Return DEBIT spending by category — one row per category, sorted by total."""
    conn = get_conn()
    clause, params = '', []
    if month and int(month) != 0:
        clause = "AND strftime('%m', date)=? AND strftime('%Y', date)=?"
        params = [f"{int(month):02d}", str(year)]
    else:
        clause = "AND strftime('%Y', date)=?"
        params = [str(year)]
    rows = conn.execute(
        f"""SELECT category,
                   SUM({_USD}) as total,
                   COUNT(*) as count
           FROM transactions
           WHERE txn_type='debit' {clause}
           GROUP BY category ORDER BY total DESC""",
        params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_wasted_total(month, year):
    conn = get_conn()
    if month and int(month) != 0:
        row = conn.execute(
            f"""SELECT COALESCE(SUM({_USD}), 0) as total FROM transactions
               WHERE is_wasted=1 AND txn_type='debit'
               AND strftime('%m', date)=? AND strftime('%Y', date)=?""",
            (f"{int(month):02d}", str(year))
        ).fetchone()
    else:
        row = conn.execute(
            f"""SELECT COALESCE(SUM({_USD}), 0) as total FROM transactions
               WHERE is_wasted=1 AND txn_type='debit'
               AND strftime('%Y', date)=?""",
            (str(year),)
        ).fetchone()
    conn.close()
    return row['total'] if row else 0.0


def get_monthly_summary(year):
    conn = get_conn()
    rows = conn.execute(
        f"""SELECT strftime('%m', date) as month,
                  SUM(CASE WHEN txn_type='debit'  THEN {_USD} ELSE 0 END) as total,
                  SUM(CASE WHEN txn_type='credit' THEN {_USD} ELSE 0 END) as credits,
                  SUM(CASE WHEN txn_type='loan'   THEN {_USD} ELSE 0 END) as loans,
                  SUM(CASE WHEN is_wasted=1 AND txn_type='debit' THEN {_USD} ELSE 0 END) as wasted
           FROM transactions WHERE strftime('%Y', date)=?
           GROUP BY month ORDER BY month""",
        (str(year),)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_available_months():
    conn = get_conn()
    rows = conn.execute(
        """SELECT DISTINCT strftime('%Y', date) as year, strftime('%m', date) as month
           FROM transactions ORDER BY year DESC, month DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_available_years():
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT strftime('%Y', date) as year FROM transactions ORDER BY year DESC"
    ).fetchall()
    conn.close()
    return [r['year'] for r in rows]


def get_account_breakdown(month, year):
    conn = get_conn()
    usd = _USD.replace('amount', 't.amount').replace('currency', 't.currency')
    period_clause = ("AND strftime('%m', t.date)=? AND strftime('%Y', t.date)=?"
                     if month and int(month) != 0 else "AND strftime('%Y', t.date)=?")
    period_params = ([f"{int(month):02d}", str(year)] if month and int(month) != 0
                     else [str(year)])
    rows = conn.execute(
        f"""SELECT a.id, a.name, a.type,
                  COALESCE(SUM(CASE WHEN t.txn_type='debit'  THEN {usd} ELSE 0 END),0) as total,
                  COALESCE(SUM(CASE WHEN t.txn_type='credit' THEN {usd} ELSE 0 END),0) as credits,
                  COALESCE(SUM(CASE WHEN t.txn_type='loan'   THEN {usd} ELSE 0 END),0) as loans,
                  COUNT(t.id) as count,
                  COALESCE(SUM(CASE WHEN t.is_wasted=1 AND t.txn_type='debit' THEN {usd} ELSE 0 END),0) as wasted,
                  COALESCE(SUM(CASE WHEN t.txn_type='debit'  AND t.orig_currency='INR' THEN t.orig_amount ELSE 0 END),0) as inr_charges,
                  COALESCE(SUM(CASE WHEN t.txn_type='credit' AND t.orig_currency='INR' THEN t.orig_amount ELSE 0 END),0) as inr_credits,
                  MAX(CASE WHEN t.orig_currency='INR' THEN 1 ELSE 0 END) as has_inr
           FROM accounts a
           LEFT JOIN transactions t ON t.account_id = a.id {period_clause}
           GROUP BY a.id ORDER BY total DESC""",
        period_params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_transaction_type(txn_id, txn_type):
    conn = get_conn()
    conn.execute("UPDATE transactions SET txn_type=? WHERE id=?", (txn_type, txn_id))
    conn.commit()
    conn.close()


# ── Category Rules ────────────────────────────────────────────────────────────

def get_category_rules():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM category_rules ORDER BY category, keyword").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category_rule(keyword, category):
    """Insert or update a category rule. Always wins — even if keyword already exists."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO category_rules (keyword, category) VALUES (?, ?) "
        "ON CONFLICT(keyword) DO UPDATE SET category=excluded.category",
        (keyword.lower(), category)
    )
    conn.commit()
    conn.close()


def delete_category_rule(rule_id):
    conn = get_conn()
    conn.execute("DELETE FROM category_rules WHERE id=?", (rule_id,))
    conn.commit()
    conn.close()


def get_distinct_categories():
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT category FROM category_rules UNION SELECT DISTINCT category FROM transactions ORDER BY category"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


# ── Wasted Keywords ───────────────────────────────────────────────────────────

def get_wasted_keywords():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM wasted_keywords ORDER BY reason, keyword").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_wasted_keyword(keyword, reason='', exclude_if_contains=''):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO wasted_keywords (keyword, reason, exclude_if_contains) VALUES (?, ?, ?)",
        (keyword.lower(), reason, exclude_if_contains.lower() if exclude_if_contains else None)
    )
    conn.commit()
    conn.close()


def delete_wasted_keyword(kw_id):
    conn = get_conn()
    conn.execute("DELETE FROM wasted_keywords WHERE id=?", (kw_id,))
    conn.commit()
    conn.close()


# ── INR rate helpers ──────────────────────────────────────────────────────────

def reapply_inr_rates_for_month(year: int, month: int) -> int:
    """Re-convert all INR transactions in a month using the stored monthly rate."""
    rate = get_inr_rate_for_month(year, month)
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, orig_amount FROM transactions
           WHERE orig_currency='INR'
           AND strftime('%Y', date)=? AND strftime('%m', date)=?""",
        (str(year), f"{month:02d}")
    ).fetchall()
    for row in rows:
        new_usd = round(row['orig_amount'] * rate, 4)
        conn.execute("UPDATE transactions SET amount=? WHERE id=?", (new_usd, row['id']))
    conn.commit()
    conn.close()
    return len(rows)


def reapply_all_inr_rates() -> int:
    """Re-convert every INR transaction using the correct monthly rate."""
    conn = get_conn()
    months = conn.execute(
        """SELECT DISTINCT strftime('%Y', date) as y, strftime('%m', date) as m
           FROM transactions WHERE orig_currency='INR'"""
    ).fetchall()
    conn.close()
    total = 0
    for row in months:
        total += reapply_inr_rates_for_month(int(row['y']), int(row['m']))
    return total


def get_inr_prompt_month():
    """Return (year, month, label) if we should prompt for last month's INR rate, else None.
    Fires once per calendar month on first dashboard load."""
    from datetime import datetime
    now = datetime.now()
    current_ym = f"{now.year}-{now.month:02d}"
    if get_setting('inr_rate_last_prompted', '') == current_ym:
        return None
    prev_year  = now.year  if now.month > 1 else now.year - 1
    prev_month = now.month - 1 if now.month > 1 else 12
    conn = get_conn()
    count = conn.execute(
        """SELECT COUNT(*) FROM transactions WHERE orig_currency='INR'
           AND strftime('%Y', date)=? AND strftime('%m', date)=?""",
        (str(prev_year), f"{prev_month:02d}")
    ).fetchone()[0]
    conn.close()
    if count == 0:
        return None
    MNAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return (prev_year, prev_month, f"{MNAMES[prev_month]} {prev_year}",
            round(get_inr_rate_for_month(prev_year, prev_month), 6))


def dismiss_inr_prompt():
    """Mark current month's prompt as shown (suppresses until next month)."""
    from datetime import datetime
    now = datetime.now()
    set_setting('inr_rate_last_prompted', f"{now.year}-{now.month:02d}")
