import os
import json
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, send_file)
from werkzeug.utils import secure_filename

import database as db
import categorizer
import reports as rpt

app = Flask(__name__)
app.secret_key = 'expenses-tracker-2024-secret'

# ── Template helpers ──────────────────────────────────────────────────────────
from urllib.parse import quote_plus
@app.template_filter('urlquote')
def urlquote_filter(s):
    return quote_plus(str(s))
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

ALLOWED_EXTENSIONS = {'csv', 'pdf', 'xlsx', 'xls'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_db()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def current_month_year():
    now = datetime.now()
    # Default: month=0 = full year view (This Year is the landing page)
    month = request.args.get('month', 0, type=int)
    year  = request.args.get('year',  now.year, type=int)
    return month, year


def period_label(month, year):
    """Human-readable label for the current period."""
    if month == 0:
        return f"Full Year {year}"
    return f"{rpt.MONTH_NAMES[month]} {year}"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    month, year = current_month_year()
    now = datetime.now()
    accounts        = db.get_accounts()
    account_breakdown  = db.get_account_breakdown(month, year)
    category_breakdown = db.get_category_breakdown(month, year)
    recent_txns     = db.get_transactions(month=month, year=year, limit=8)
    available_months   = db.get_available_months()
    available_years    = db.get_available_years()
    monthly_summary    = db.get_monthly_summary(year)
    period_totals      = db.get_period_totals(month, year)
    inr_prompt         = db.get_inr_prompt_month()   # (year, month, label, cur_rate) or None

    # Previous period for MoM delta
    if month and month != 0:
        prev_month = month - 1 if month > 1 else 12
        prev_year  = year if month > 1 else year - 1
    else:
        prev_month = 0
        prev_year  = year - 1
    prev_totals = db.get_period_totals(prev_month, prev_year)

    return render_template('dashboard.html',
        account_breakdown=account_breakdown,
        period_totals=period_totals,
        prev_totals=prev_totals,
        category_breakdown=category_breakdown,
        recent_txns=recent_txns,
        available_months=available_months,
        available_years=available_years,
        monthly_summary=monthly_summary,
        month=month, year=year,
        month_name=rpt.MONTH_NAMES[month] if month else '',
        period_label=period_label(month, year),
        current_month=now.month,
        current_year=now.year,
        accounts=accounts,
        inr_prompt=inr_prompt,
    )


# ── Upload ────────────────────────────────────────────────────────────────────

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    accounts = db.get_accounts()
    if request.method == 'POST':
        account_id = request.form.get('account_id')
        new_account = request.form.get('new_account', '').strip()
        acct_type = request.form.get('account_type', 'credit')
        currency = request.form.get('currency', 'USD').strip().upper()
        if currency not in ('USD', 'INR'):
            currency = 'USD'

        if new_account:
            account_id = db.get_or_create_account(new_account, acct_type)
        elif account_id:
            account_id = int(account_id)
        else:
            flash('Please select or create an account.', 'danger')
            return redirect(url_for('upload'))

        files = request.files.getlist('statements')
        if not files or all(f.filename == '' for f in files):
            flash('No files selected.', 'danger')
            return redirect(url_for('upload'))

        total_inserted = 0
        total_skipped = 0
        errors = []

        for f in files:
            if not f or f.filename == '':
                continue
            if not allowed_file(f.filename):
                errors.append(f"{f.filename}: Unsupported format. Use CSV, PDF, XLSX, or XLS.")
                continue
            filename = secure_filename(f.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(save_path)
            try:
                _, inserted, skipped = categorizer.parse_statement(save_path, account_id, filename, currency=currency)
                total_inserted += inserted
                total_skipped += skipped
            except ValueError as e:
                errors.append(f"{filename}: {e}")
            except Exception as e:
                errors.append(f"{filename}: Unexpected error — {e}")

        if errors:
            for err in errors:
                flash(err, 'danger')
        if total_inserted > 0:
            msg = f'Imported {total_inserted} new transaction(s).'
            if total_skipped:
                msg += (f' {total_skipped} duplicate(s) skipped — a transaction is a duplicate when'
                        f' the same account, date, description, and amount already exists in the database.'
                        f' This is normal when statement periods overlap.')
            flash(msg, 'success')
        elif not errors:
            flash('No new transactions found — all entries already exist in the database'
                  ' (same account + date + description + amount). Upload a different statement period.', 'warning')

        return redirect(url_for('transactions'))

    return render_template('upload.html', accounts=accounts)


# ── Transactions ──────────────────────────────────────────────────────────────

@app.route('/transactions')
def transactions():
    month, year = current_month_year()
    account_id = request.args.get('account_id', type=int)
    category   = request.args.get('category', '')
    txn_type   = request.args.get('txn_type', '')   # 'debit' | 'credit' | ''
    is_wasted  = request.args.get('is_wasted', None)
    search     = request.args.get('q', '').strip()
    page       = request.args.get('page', 1, type=int)
    per_page   = 50

    if is_wasted == '1':
        is_wasted = 1
    elif is_wasted == '0':
        is_wasted = 0
    else:
        is_wasted = None

    txns = db.get_transactions(
        month=month, year=year,
        account_id=account_id,
        category=category or None,
        txn_type=txn_type or None,
        is_wasted=is_wasted,
        search=search or None,
        limit=per_page, offset=(page - 1) * per_page
    )
    total_count = db.count_transactions(
        month=month, year=year,
        account_id=account_id,
        category=category or None,
        txn_type=txn_type or None,
        is_wasted=is_wasted,
        search=search or None,
    )
    accounts = db.get_accounts()
    categories = db.get_distinct_categories()
    available_months = db.get_available_months()
    available_years  = db.get_available_years()
    total_pages = (total_count + per_page - 1) // per_page

    return render_template('transactions.html',
        txns=txns, accounts=accounts, categories=categories,
        available_months=available_months,
        available_years=available_years,
        month=month, year=year,
        month_name=rpt.MONTH_NAMES[month] if month else '',
        period_label=period_label(month, year),
        selected_account=account_id, selected_category=category,
        selected_txn_type=txn_type,
        selected_wasted=is_wasted,
        search=search,
        page=page, total_pages=total_pages, total_count=total_count,
    )


@app.route('/transactions/<int:txn_id>/update', methods=['POST'])
def update_transaction(txn_id):
    category = request.form.get('category', 'Uncategorized')
    is_wasted = 1 if request.form.get('is_wasted') == '1' else 0
    db.update_transaction_category(txn_id, category, is_wasted)

    # Work out how many other transactions share the same merchant
    txn = db.get_transaction(txn_id)
    keyword = categorizer.extract_merchant_keyword(txn['description']) if txn else ''
    match_count = db.count_merchant_matches(keyword, exclude_id=txn_id) if keyword else 0

    return jsonify({
        'ok': True,
        'category': category,
        'is_wasted': is_wasted,
        'keyword': keyword,
        'match_count': match_count,
        'description': txn['description'] if txn else '',
    })


@app.route('/transactions/apply-rule', methods=['POST'])
def apply_rule():
    keyword   = request.form.get('keyword', '').strip()
    category  = request.form.get('category', 'Uncategorized')
    is_wasted = 1 if request.form.get('is_wasted') == '1' else 0
    exclude_id = request.form.get('exclude_id', 0, type=int)

    if not keyword:
        return jsonify({'ok': False, 'error': 'No keyword provided'})

    changed = db.bulk_update_category_by_keyword(keyword, category, is_wasted, exclude_id)
    db.add_category_rule(keyword, category)

    return jsonify({'ok': True, 'changed': changed, 'keyword': keyword, 'category': category})


@app.route('/transactions/<int:txn_id>/delete', methods=['POST'])
def delete_transaction(txn_id):
    db.delete_transaction(txn_id)
    flash('Transaction deleted.', 'info')
    return redirect(request.referrer or url_for('transactions'))


@app.route('/transactions/recategorize', methods=['POST'])
def recategorize_all():
    categorizer.recategorize_all()
    flash('All uncategorized transactions have been re-processed.', 'success')
    return redirect(url_for('transactions'))


# ── Categories ────────────────────────────────────────────────────────────────

@app.route('/categories')
def categories():
    rules = db.get_category_rules()
    wasted_kws = db.get_wasted_keywords()
    return render_template('categories.html', rules=rules, wasted_kws=wasted_kws)


@app.route('/categories/add', methods=['POST'])
def add_category_rule():
    keyword = request.form.get('keyword', '').strip().lower()
    category = request.form.get('category', '').strip()
    if keyword and category:
        db.add_category_rule(keyword, category)
        flash(f'Rule saved: "{keyword}" → {category} (existing rule updated if keyword already existed)', 'success')
    else:
        flash('Keyword and category are required.', 'danger')
    return redirect(url_for('categories'))


@app.route('/categories/<int:rule_id>/delete', methods=['POST'])
def delete_category_rule(rule_id):
    db.delete_category_rule(rule_id)
    flash('Rule deleted.', 'info')
    return redirect(url_for('categories'))


@app.route('/categories/import-web', methods=['POST'])
def import_web_categories():
    count = categorizer.import_web_categories()
    flash(f'Imported {count} keyword rules from the built-in web categories list.', 'success')
    return redirect(url_for('categories'))


# ── Wasted Keywords ───────────────────────────────────────────────────────────

@app.route('/wasted/add', methods=['POST'])
def add_wasted_keyword():
    keyword = request.form.get('keyword', '').strip().lower()
    reason = request.form.get('reason', '').strip()
    exclude = request.form.get('exclude_if_contains', '').strip().lower()
    if keyword:
        db.add_wasted_keyword(keyword, reason, exclude)
        flash(f'Added "{keyword}" to wasted list.', 'success')
    else:
        flash('Keyword is required.', 'danger')
    return redirect(url_for('categories'))


@app.route('/wasted/<int:kw_id>/delete', methods=['POST'])
def delete_wasted_keyword(kw_id):
    db.delete_wasted_keyword(kw_id)
    flash('Wasted keyword removed.', 'info')
    return redirect(url_for('categories'))


# ── Accounts ──────────────────────────────────────────────────────────────────

@app.route('/accounts/add', methods=['POST'])
def add_account():
    name = request.form.get('name', '').strip()
    acct_type = request.form.get('type', 'credit')
    if name:
        db.get_or_create_account(name, acct_type)
        flash(f'Account "{name}" added.', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
def delete_account(account_id):
    db.delete_account(account_id)
    flash('Account and all its transactions deleted.', 'warning')
    return redirect(url_for('dashboard'))


# ── Reports ───────────────────────────────────────────────────────────────────

@app.route('/reports')
def reports():
    saved = rpt.list_saved_reports()
    available_months = db.get_available_months()
    return render_template('reports.html', saved=saved, available_months=available_months,
                           month_names=rpt.MONTH_NAMES)


@app.route('/reports/generate', methods=['POST'])
def generate_report():
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    if not month or not year:
        flash('Month and year are required.', 'danger')
        return redirect(url_for('reports'))
    try:
        summary = rpt.generate_monthly_report(year, month)
        flash(
            f'Report saved for {summary["month_name"]} {year} — '
            f'${summary["grand_total"]:,.2f} total, '
            f'${summary["wasted_total"]:,.2f} wasted.',
            'success'
        )
    except Exception as e:
        flash(f'Error generating report: {e}', 'danger')
    return redirect(url_for('reports'))


@app.route('/reports/view/<int:year>/<int:month>')
def view_report(year, month):
    folder = rpt._report_folder(year, month)
    html_files = [f for f in os.listdir(folder) if f.endswith('.html')]
    if not html_files:
        flash('Report not found. Generate it first.', 'warning')
        return redirect(url_for('reports'))
    return send_file(os.path.join(folder, html_files[0]))


@app.route('/reports/download/<int:year>/<int:month>/<filetype>')
def download_report(year, month, filetype):
    folder = rpt._report_folder(year, month)
    ext = 'csv' if filetype == 'csv' else 'html'
    files = [f for f in os.listdir(folder) if f.endswith(f'.{ext}')]
    if not files:
        flash('File not found.', 'warning')
        return redirect(url_for('reports'))
    return send_file(os.path.join(folder, files[0]), as_attachment=True)


# ── Settings ──────────────────────────────────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        action = request.form.get('action', 'global')
        if action == 'global':
            rate = request.form.get('inr_usd_rate', '').strip()
            try:
                rate_f = float(rate)
                if rate_f <= 0: raise ValueError
                db.set_setting('inr_usd_rate', str(rate_f))
                flash(f'Global INR → USD rate updated to {rate_f:.6f}', 'success')
            except (ValueError, TypeError):
                flash('Invalid rate. Enter a positive decimal like 0.01185', 'danger')
        elif action == 'monthly':
            year  = request.form.get('m_year', type=int)
            month = request.form.get('m_month', type=int)
            rate  = request.form.get('m_rate', '').strip()
            try:
                rate_f = float(rate)
                if rate_f <= 0 or not year or not month: raise ValueError
                db.set_monthly_inr_rate(year, month, rate_f)
                flash(f'Monthly rate set: {year}/{month:02d} = {rate_f:.6f}', 'success')
            except (ValueError, TypeError):
                flash('Invalid monthly rate entry.', 'danger')
        elif action == 'delete_monthly':
            key = request.form.get('key', '')
            parts = key.replace('inr_usd_rate_', '').split('_')
            if len(parts) == 2:
                try:
                    db.delete_monthly_inr_rate(int(parts[0]), int(parts[1]))
                    flash('Monthly rate deleted.', 'info')
                except (ValueError, IndexError):
                    flash('Invalid rate key.', 'danger')
        return redirect(url_for('settings'))

    monthly_rates = db.get_all_monthly_inr_rates()
    return render_template('settings.html',
                           inr_rate=db.get_inr_rate(),
                           monthly_rates=monthly_rates)


# ── INR Rate Prompt ───────────────────────────────────────────────────────────

@app.route('/settings/inr-rate-confirm', methods=['POST'])
def inr_rate_confirm():
    """Save the confirmed INR rate for a past month and re-convert transactions."""
    year  = request.form.get('year',  type=int)
    month = request.form.get('month', type=int)
    rate  = request.form.get('rate',  '').strip()
    action = request.form.get('action', 'save')  # 'save' or 'dismiss'

    db.dismiss_inr_prompt()   # always suppress prompt for this calendar month

    if action == 'save' and year and month and rate:
        try:
            rate_f = float(rate)
            if rate_f <= 0:
                raise ValueError
            db.set_monthly_inr_rate(year, month, rate_f)
            changed = db.reapply_inr_rates_for_month(year, month)
            flash(f'INR rate for {rpt.MONTH_NAMES[month]} {year} set to {rate_f:.6f} '
                  f'— {changed} transactions re-converted.', 'success')
        except (ValueError, TypeError):
            flash('Invalid rate entered.', 'danger')

    return redirect(url_for('dashboard'))


# ── Refetch historical INR rates ──────────────────────────────────────────────

@app.route('/settings/refetch-inr-rates', methods=['POST'])
def refetch_inr_rates():
    """Re-fetch the actual historical INR→USD rate for every INR transaction date
    and re-convert amounts. Uses frankfurter.app (free, no API key)."""
    try:
        changed = db.reapply_all_inr_rates()
        flash(f'Historical rates applied — {changed} INR transaction(s) re-converted '
              f'using the actual exchange rate for each date.', 'success')
    except Exception as e:
        flash(f'Rate fetch failed: {e}', 'danger')
    return redirect(url_for('settings'))


# ── API (JSON) ────────────────────────────────────────────────────────────────

@app.route('/api/categories')
def api_categories():
    return jsonify(db.get_distinct_categories())


@app.route('/api/monthly-chart/<int:year>')
def api_monthly_chart(year):
    data = db.get_monthly_summary(year)
    return jsonify(data)


if __name__ == '__main__':
    debug = os.environ.get('EXPENSES_DEBUG', '1') == '1'
    app.run(host='0.0.0.0', port=5050, debug=debug, use_reloader=debug)
