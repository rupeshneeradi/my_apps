import os
import json
from datetime import datetime
import database as db

REPORTS_BASE = os.path.join(os.path.dirname(__file__), 'monthly_reports')
MONTH_NAMES = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def _report_folder(year: int, month: int) -> str:
    folder = os.path.join(REPORTS_BASE, str(year), f"{int(month):02d}_{MONTH_NAMES[int(month)]}")
    os.makedirs(folder, exist_ok=True)
    return folder


def generate_monthly_report(year: int, month: int) -> dict:
    """Generate and save a monthly report. Returns summary dict."""
    month = int(month)
    year = int(year)
    month_name = MONTH_NAMES[month]

    transactions = db.get_transactions(month=month, year=year)
    account_breakdown = db.get_account_breakdown(month, year)
    category_breakdown = db.get_category_breakdown(month, year)
    grand_total = sum(a['total'] for a in account_breakdown)
    wasted_total = db.get_wasted_total(month, year)

    summary = {
        'year': year,
        'month': month,
        'month_name': month_name,
        'generated_at': datetime.now().isoformat(),
        'grand_total': grand_total,
        'wasted_total': wasted_total,
        'transaction_count': len(transactions),
        'account_breakdown': account_breakdown,
        'category_breakdown': category_breakdown,
    }

    folder = _report_folder(year, month)

    # Save JSON summary
    json_path = os.path.join(folder, f'summary_{year}_{month:02d}.json')
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    # Save CSV of all transactions
    csv_path = os.path.join(folder, f'transactions_{year}_{month:02d}.csv')
    _save_csv(transactions, csv_path)

    # Save HTML report
    html_path = os.path.join(folder, f'report_{year}_{month:02d}.html')
    _save_html(summary, transactions, html_path)

    summary['folder'] = folder
    summary['html_path'] = html_path
    summary['csv_path'] = csv_path
    return summary


def _save_csv(transactions: list, path: str):
    import csv
    if not transactions:
        return
    fields = ['date', 'account_name', 'description', 'amount', 'category', 'is_wasted']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for t in transactions:
            writer.writerow({k: t.get(k, '') for k in fields})


def _save_html(summary: dict, transactions: list, path: str):
    month_name = summary['month_name']
    year = summary['year']
    grand_total = summary['grand_total']
    wasted_total = summary['wasted_total']
    accounts = summary['account_breakdown']
    categories = summary['category_breakdown']

    # Build account rows
    account_rows = ''
    for a in accounts:
        if a['total'] > 0:
            account_rows += f"""
            <tr>
                <td>{a['name']}</td>
                <td class="badge-type">{a['type'].title()}</td>
                <td class="amount">${a['total']:,.2f}</td>
                <td>{a['count']}</td>
                <td class="wasted">${a['wasted']:,.2f}</td>
            </tr>"""

    # Build category rows
    cat_rows = ''
    for c in categories:
        wasted_class = ' class="wasted-row"' if c['category'] == 'Wasted' else ''
        cat_rows += f"""
            <tr{wasted_class}>
                <td>{c['category']}</td>
                <td class="amount">${c['total']:,.2f}</td>
                <td>{c['count']}</td>
            </tr>"""

    # Build transaction rows
    txn_rows = ''
    for t in transactions:
        wasted_class = ' class="wasted-row"' if t['is_wasted'] else ''
        txn_rows += f"""
            <tr{wasted_class}>
                <td>{t['date']}</td>
                <td>{t['account_name']}</td>
                <td>{t['description']}</td>
                <td class="amount">${t['amount']:,.2f}</td>
                <td>{t['category']}</td>
            </tr>"""

    wasted_pct = (wasted_total / grand_total * 100) if grand_total > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Expense Report — {month_name} {year}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         max-width: 1100px; margin: 0 auto; padding: 2rem; color: #1a1a2e; }}
  h1 {{ color: #16213e; border-bottom: 3px solid #e94560; padding-bottom: .5rem; }}
  h2 {{ color: #16213e; margin-top: 2rem; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; margin: 1.5rem 0; }}
  .card {{ background: #f8f9fa; border-radius: 12px; padding: 1.5rem; text-align: center; border: 1px solid #e0e0e0; }}
  .card .value {{ font-size: 2rem; font-weight: 700; color: #16213e; }}
  .card.wasted .value {{ color: #e94560; }}
  .card .label {{ font-size: .85rem; color: #666; margin-top: .3rem; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: .9rem; }}
  th {{ background: #16213e; color: #fff; padding: .75rem 1rem; text-align: left; }}
  td {{ padding: .65rem 1rem; border-bottom: 1px solid #eee; }}
  tr:hover td {{ background: #f0f4ff; }}
  .amount {{ text-align: right; font-weight: 600; }}
  .wasted {{ color: #e94560; font-weight: 600; }}
  .wasted-row td {{ background: #fff5f5; color: #c0392b; }}
  .badge-type {{ font-size: .75rem; background: #e8f4fd; color: #2980b9; padding: .2rem .5rem; border-radius: 20px; }}
  .footer {{ margin-top: 3rem; font-size: .8rem; color: #999; text-align: center; border-top: 1px solid #eee; padding-top: 1rem; }}
</style>
</head>
<body>
<h1>Expense Report — {month_name} {year}</h1>
<p>Generated: {summary['generated_at'][:19].replace('T', ' ')}</p>

<div class="summary-grid">
  <div class="card">
    <div class="value">${grand_total:,.2f}</div>
    <div class="label">Total Spent</div>
  </div>
  <div class="card wasted">
    <div class="value">${wasted_total:,.2f}</div>
    <div class="label">Wasted ({wasted_pct:.1f}%)</div>
  </div>
  <div class="card">
    <div class="value">{summary['transaction_count']}</div>
    <div class="label">Transactions</div>
  </div>
</div>

<h2>By Account</h2>
<table>
  <thead><tr><th>Account</th><th>Type</th><th>Total Spent</th><th>Transactions</th><th>Wasted</th></tr></thead>
  <tbody>{account_rows}</tbody>
</table>

<h2>By Category</h2>
<table>
  <thead><tr><th>Category</th><th>Total</th><th>Transactions</th></tr></thead>
  <tbody>{cat_rows}</tbody>
</table>

<h2>All Transactions</h2>
<table>
  <thead><tr><th>Date</th><th>Account</th><th>Description</th><th>Amount</th><th>Category</th></tr></thead>
  <tbody>{txn_rows}</tbody>
</table>

<div class="footer">Expenses Tracker — {month_name} {year} Report</div>
</body>
</html>"""

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)


def list_saved_reports() -> list:
    """Return list of all saved reports sorted newest first."""
    reports = []
    if not os.path.exists(REPORTS_BASE):
        return reports
    for year_dir in sorted(os.listdir(REPORTS_BASE), reverse=True):
        year_path = os.path.join(REPORTS_BASE, year_dir)
        if not os.path.isdir(year_path):
            continue
        for month_dir in sorted(os.listdir(year_path), reverse=True):
            month_path = os.path.join(year_path, month_dir)
            if not os.path.isdir(month_path):
                continue
            json_files = [f for f in os.listdir(month_path) if f.endswith('.json')]
            html_files = [f for f in os.listdir(month_path) if f.endswith('.html')]
            if json_files:
                try:
                    with open(os.path.join(month_path, json_files[0])) as f:
                        data = json.load(f)
                    data['html_file'] = html_files[0] if html_files else None
                    data['folder'] = month_path
                    reports.append(data)
                except Exception:
                    pass
    return reports
