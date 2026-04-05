import azure.functions as func
import psycopg2
import os
import logging
import json
from datetime import datetime

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── DB helper ────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME,
        user=DB_USER, password=DB_PASS, sslmode="require"
    )

def table_exists(table_name: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = %s
        );
    """, (table_name,))
    exists = cur.fetchone()[0]
    cur.close()
    conn.close()
    return exists

# ── Home UI ──────────────────────────────────────────────────
@app.route(route="")
def index(req: func.HttpRequest) -> func.HttpResponse:
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Azure Functions DB Manager</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #13131a;
    --border: #1e1e2e;
    --accent: #5c6fff;
    --accent2: #ff6b6b;
    --accent3: #43e97b;
    --text: #e8e8f0;
    --muted: #6b6b80;
    --card: #16161f;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
    padding: 40px 20px;
  }
  .grid-bg {
    position: fixed; inset: 0; z-index: 0;
    background-image:
      linear-gradient(var(--border) 1px, transparent 1px),
      linear-gradient(90deg, var(--border) 1px, transparent 1px);
    background-size: 40px 40px;
    opacity: 0.4;
  }
  .container { max-width: 860px; margin: 0 auto; position: relative; z-index: 1; }
  header { margin-bottom: 48px; }
  .badge {
    display: inline-block;
    background: var(--accent);
    color: #fff;
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 4px 10px;
    border-radius: 2px;
    margin-bottom: 16px;
  }
  h1 {
    font-family: 'Syne', sans-serif;
    font-size: clamp(28px, 5vw, 48px);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -1px;
  }
  h1 span { color: var(--accent); }
  .subtitle { color: var(--muted); margin-top: 10px; font-size: 13px; }
  .status-bar {
    display: flex; gap: 20px; margin: 24px 0 40px;
    padding: 14px 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 12px;
  }
  .status-item { display: flex; align-items: center; gap: 6px; }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent3); }
  .dot.warn { background: #f59e0b; }
  .section-label {
    font-size: 10px; letter-spacing: 3px; text-transform: uppercase;
    color: var(--muted); margin-bottom: 16px;
  }
  .tables-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 48px; }
  .table-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    display: block;
    position: relative;
    overflow: hidden;
  }
  .table-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, var(--accent) 0%, transparent 60%);
    opacity: 0;
    transition: opacity 0.2s;
  }
  .table-card:hover { border-color: var(--accent); transform: translateY(-2px); }
  .table-card:hover::before { opacity: 0.06; }
  .table-card.orders::before { background: linear-gradient(135deg, #5c6fff 0%, transparent 60%); }
  .table-card.customers::before { background: linear-gradient(135deg, #ff6b6b 0%, transparent 60%); }
  .table-card.products::before { background: linear-gradient(135deg, #43e97b 0%, transparent 60%); }
  .card-icon { font-size: 28px; margin-bottom: 14px; }
  .card-title {
    font-family: 'Syne', sans-serif;
    font-size: 18px; font-weight: 700;
    margin-bottom: 6px;
  }
  .card-desc { color: var(--muted); font-size: 11px; line-height: 1.6; }
  .card-tag {
    position: absolute; top: 16px; right: 16px;
    font-size: 9px; letter-spacing: 1px; text-transform: uppercase;
    padding: 3px 8px; border-radius: 2px;
  }
  .tag-new { background: rgba(92,111,255,0.15); color: var(--accent); }
  .tag-exists { background: rgba(67,233,123,0.15); color: var(--accent3); }
  .logs-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
  }
  .log-line { font-size: 12px; color: var(--muted); padding: 4px 0; border-bottom: 1px solid var(--border); }
  .log-line:last-child { border-bottom: none; }
  .log-line .ts { color: var(--accent); margin-right: 10px; }
  .log-line .ok { color: var(--accent3); }
  .log-line .err { color: var(--accent2); }
</style>
</head>
<body>
<div class="grid-bg"></div>
<div class="container">
  <header>
    <div class="badge">Azure Functions + PostgreSQL</div>
    <h1>DB <span>Manager</span></h1>
    <p class="subtitle">Manage your database tables and records via Azure Functions</p>
  </header>

  <div class="status-bar" id="statusBar">
    <div class="status-item"><div class="dot"></div> Function: Online</div>
    <div class="status-item"><div class="dot" id="dbDot"></div> <span id="dbStatus">Checking DB...</span></div>
    <div class="status-item"><div class="dot warn"></div> <span id="tableCount">Loading tables...</span></div>
  </div>

  <div class="section-label">Available tables</div>
  <div class="tables-grid" id="tablesGrid">
    <a href="/api/table/orders" class="table-card orders">
      <div class="card-tag" id="tag-orders">checking...</div>
      <div class="card-icon">📦</div>
      <div class="card-title">Orders</div>
      <div class="card-desc">Manage customer orders. Create, view, and insert order records.</div>
    </a>
    <a href="/api/table/customers" class="table-card customers">
      <div class="card-tag" id="tag-customers">checking...</div>
      <div class="card-icon">👤</div>
      <div class="card-title">Customers</div>
      <div class="card-desc">Store customer profiles, names and contact information.</div>
    </a>
    <a href="/api/table/products" class="table-card products">
      <div class="card-tag" id="tag-products">checking...</div>
      <div class="card-icon">🛍️</div>
      <div class="card-title">Products</div>
      <div class="card-desc">Product catalog with pricing and inventory tracking.</div>
    </a>
  </div>

  <div class="logs-section">
    <div class="section-label">Recent activity</div>
    <div id="logLines"><div class="log-line"><span class="ts">--:--:--</span> Loading activity...</div></div>
  </div>
</div>

<script>
async function checkStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    document.getElementById('dbStatus').textContent = 'DB: Connected';
    document.getElementById('dbDot').style.background = '#43e97b';
    document.getElementById('tableCount').textContent = `${d.existing_tables.length} tables active`;

    ['orders','customers','products'].forEach(t => {
      const tag = document.getElementById('tag-' + t);
      if (d.existing_tables.includes(t)) {
        tag.textContent = 'EXISTS';
        tag.className = 'card-tag tag-exists';
      } else {
        tag.textContent = 'NEW';
        tag.className = 'card-tag tag-new';
      }
    });

    const logs = document.getElementById('logLines');
    logs.innerHTML = d.recent_logs.map(l =>
      `<div class="log-line"><span class="ts">${l.time}</span><span class="${l.ok ? 'ok' : 'err'}">${l.ok ? '✓' : '✗'}</span> ${l.msg}</div>`
    ).join('') || '<div class="log-line"><span class="ts">--</span> No recent activity</div>';
  } catch(e) {
    document.getElementById('dbStatus').textContent = 'DB: Error';
    document.getElementById('dbDot').style.background = '#ff6b6b';
  }
}
checkStatus();
</script>
</body>
</html>"""
    return func.HttpResponse(html, mimetype="text/html", status_code=200)


# ── Status API ───────────────────────────────────────────────
@app.route(route="status")
def status(req: func.HttpRequest) -> func.HttpResponse:
    try:
        tables = ["orders", "customers", "products"]
        existing = [t for t in tables if table_exists(t)]
        return func.HttpResponse(json.dumps({
            "status": "ok",
            "existing_tables": existing,
            "recent_logs": [
                {"time": datetime.now().strftime("%H:%M:%S"), "msg": "Status check OK", "ok": True}
            ]
        }), mimetype="application/json", status_code=200)
    except Exception as e:
        return func.HttpResponse(json.dumps({"status": "error", "error": str(e), "existing_tables": [], "recent_logs": []}),
                                  mimetype="application/json", status_code=500)


# ── Table UI — smart: create if not exists, show actions if exists ──
@app.route(route="table/{table_name}")
def table_ui(req: func.HttpRequest) -> func.HttpResponse:
    table_name = req.route_params.get("table_name")
    exists = table_exists(table_name)

    icons = {"orders": "📦", "customers": "👤", "products": "🛍️"}
    icon = icons.get(table_name, "🗄️")

    if table_name == "orders":
        fields_html = """
        <div class="field-group">
          <label>Customer Name</label>
          <input type="text" id="f_customer_name" placeholder="e.g. Chirag Jaria"/>
        </div>
        <div class="field-group">
          <label>Product</label>
          <input type="text" id="f_product" placeholder="e.g. Laptop"/>
        </div>
        <div class="field-group">
          <label>Amount (₹)</label>
          <input type="number" id="f_amount" placeholder="e.g. 75000"/>
        </div>
        <div class="field-group">
          <label>Status</label>
          <select id="f_status">
            <option>pending</option>
            <option>confirmed</option>
            <option>shipped</option>
            <option>delivered</option>
          </select>
        </div>"""
        insert_js = """
        const data = {
          customer_name: document.getElementById('f_customer_name').value,
          product: document.getElementById('f_product').value,
          amount: document.getElementById('f_amount').value,
          status: document.getElementById('f_status').value
        };"""
    elif table_name == "customers":
        fields_html = """
        <div class="field-group">
          <label>Full Name</label>
          <input type="text" id="f_name" placeholder="e.g. Chirag Jaria"/>
        </div>
        <div class="field-group">
          <label>Email</label>
          <input type="email" id="f_email" placeholder="e.g. chirag@example.com"/>
        </div>
        <div class="field-group">
          <label>Phone</label>
          <input type="text" id="f_phone" placeholder="e.g. +91 98765 43210"/>
        </div>
        <div class="field-group">
          <label>City</label>
          <input type="text" id="f_city" placeholder="e.g. Mumbai"/>
        </div>"""
        insert_js = """
        const data = {
          name: document.getElementById('f_name').value,
          email: document.getElementById('f_email').value,
          phone: document.getElementById('f_phone').value,
          city: document.getElementById('f_city').value
        };"""
    else:  # products
        fields_html = """
        <div class="field-group">
          <label>Product Name</label>
          <input type="text" id="f_name" placeholder="e.g. MacBook Pro"/>
        </div>
        <div class="field-group">
          <label>Price (₹)</label>
          <input type="number" id="f_price" placeholder="e.g. 150000"/>
        </div>
        <div class="field-group">
          <label>Stock</label>
          <input type="number" id="f_stock" placeholder="e.g. 50"/>
        </div>
        <div class="field-group">
          <label>Category</label>
          <input type="text" id="f_category" placeholder="e.g. Electronics"/>
        </div>"""
        insert_js = """
        const data = {
          name: document.getElementById('f_name').value,
          price: document.getElementById('f_price').value,
          stock: document.getElementById('f_stock').value,
          category: document.getElementById('f_category').value
        };"""

    create_section = "" if exists else f"""
    <div class="alert">
      <span>⚠</span>
      Table <strong>{table_name}</strong> does not exist yet.
      <button class="btn btn-create" onclick="createTable()">Create Table</button>
    </div>"""

    actions_section = "" if not exists else f"""
    <div class="actions-bar">
      <button class="btn btn-primary" onclick="showPanel('insert')">+ Insert Record</button>
      <button class="btn btn-secondary" onclick="showPanel('view')">View Records</button>
      <button class="btn btn-danger" onclick="showPanel('delete')">Drop Table</button>
    </div>

    <div id="panel-insert" class="panel">
      <div class="panel-title">Insert record into {table_name}</div>
      {fields_html}
      <button class="btn btn-primary" onclick="insertRecord()">Save Record</button>
    </div>

    <div id="panel-view" class="panel">
      <div class="panel-title">Records in {table_name}</div>
      <div id="recordsTable">Click "View Records" to load data</div>
      <button class="btn btn-secondary" onclick="loadRecords()">Refresh</button>
    </div>

    <div id="panel-delete" class="panel">
      <div class="panel-title" style="color:#ff6b6b">⚠ Drop table {table_name}</div>
      <p style="color:#6b6b80;font-size:13px;margin-bottom:20px">This will permanently delete the table and all its data.</p>
      <button class="btn btn-danger" onclick="dropTable()">Confirm Drop Table</button>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>{table_name.capitalize()} — DB Manager</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
<style>
  :root {{
    --bg:#0a0a0f; --surface:#13131a; --border:#1e1e2e;
    --accent:#5c6fff; --accent2:#ff6b6b; --accent3:#43e97b;
    --text:#e8e8f0; --muted:#6b6b80; --card:#16161f;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--text); font-family:'DM Mono',monospace; min-height:100vh; padding:40px 20px; }}
  .grid-bg {{ position:fixed; inset:0; z-index:0;
    background-image: linear-gradient(var(--border) 1px,transparent 1px), linear-gradient(90deg,var(--border) 1px,transparent 1px);
    background-size:40px 40px; opacity:0.4; }}
  .container {{ max-width:760px; margin:0 auto; position:relative; z-index:1; }}
  .back {{ color:var(--muted); text-decoration:none; font-size:12px; display:inline-flex; align-items:center; gap:6px; margin-bottom:32px; }}
  .back:hover {{ color:var(--text); }}
  .page-icon {{ font-size:40px; margin-bottom:12px; }}
  h1 {{ font-family:'Syne',sans-serif; font-size:36px; font-weight:800; margin-bottom:6px; }}
  h1 span {{ color:var(--accent); }}
  .subtitle {{ color:var(--muted); font-size:12px; margin-bottom:32px; }}
  .alert {{
    display:flex; align-items:center; gap:12px; flex-wrap:wrap;
    background:rgba(255,107,107,0.08); border:1px solid rgba(255,107,107,0.3);
    border-radius:8px; padding:16px 20px; margin-bottom:24px; font-size:13px;
  }}
  .alert strong {{ color:var(--accent2); }}
  .actions-bar {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px; }}
  .btn {{
    padding:10px 20px; border:none; border-radius:6px; cursor:pointer;
    font-family:'DM Mono',monospace; font-size:13px; font-weight:500;
    transition:all 0.15s; letter-spacing:0.5px;
  }}
  .btn-primary {{ background:var(--accent); color:#fff; }}
  .btn-primary:hover {{ background:#4a5aff; }}
  .btn-secondary {{ background:var(--surface); color:var(--text); border:1px solid var(--border); }}
  .btn-secondary:hover {{ border-color:var(--accent); color:var(--accent); }}
  .btn-create {{ background:var(--accent2); color:#fff; margin-left:auto; }}
  .btn-create:hover {{ background:#ff5252; }}
  .btn-danger {{ background:rgba(255,107,107,0.1); color:var(--accent2); border:1px solid rgba(255,107,107,0.3); }}
  .btn-danger:hover {{ background:rgba(255,107,107,0.2); }}
  .panel {{
    display:none; background:var(--card); border:1px solid var(--border);
    border-radius:12px; padding:28px; margin-bottom:20px;
  }}
  .panel.active {{ display:block; animation:fadeIn 0.2s ease; }}
  @keyframes fadeIn {{ from{{opacity:0;transform:translateY(4px)}} to{{opacity:1;transform:none}} }}
  .panel-title {{ font-family:'Syne',sans-serif; font-size:18px; font-weight:700; margin-bottom:20px; }}
  .field-group {{ margin-bottom:16px; }}
  .field-group label {{ display:block; font-size:11px; letter-spacing:1px; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }}
  .field-group input, .field-group select {{
    width:100%; background:var(--surface); border:1px solid var(--border);
    border-radius:6px; padding:10px 14px; color:var(--text);
    font-family:'DM Mono',monospace; font-size:13px;
  }}
  .field-group input:focus, .field-group select:focus {{ outline:none; border-color:var(--accent); }}
  .field-group select option {{ background:var(--surface); }}
  .toast {{
    position:fixed; bottom:24px; right:24px; z-index:100;
    background:var(--surface); border:1px solid var(--border);
    border-radius:8px; padding:14px 20px; font-size:13px;
    transform:translateY(100px); opacity:0; transition:all 0.3s;
  }}
  .toast.show {{ transform:none; opacity:1; }}
  .toast.success {{ border-color:var(--accent3); color:var(--accent3); }}
  .toast.error {{ border-color:var(--accent2); color:var(--accent2); }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; margin-top:16px; }}
  th {{ text-align:left; padding:10px; border-bottom:1px solid var(--border); color:var(--muted); font-size:10px; letter-spacing:1px; text-transform:uppercase; }}
  td {{ padding:10px; border-bottom:1px solid var(--border); }}
  tr:last-child td {{ border-bottom:none; }}
  .empty {{ color:var(--muted); font-size:12px; padding:20px 0; }}
</style>
</head>
<body>
<div class="grid-bg"></div>
<div class="container">
  <a href="/api/" class="back">← Back to home</a>
  <div class="page-icon">{icon}</div>
  <h1><span>{table_name.capitalize()}</span></h1>
  <p class="subtitle">Table manager — PostgreSQL via Azure Functions</p>

  {create_section}
  {actions_section}
</div>

<div class="toast" id="toast"></div>

<script>
function showToast(msg, type='success') {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  setTimeout(() => t.className = 'toast', 3000);
}}

function showPanel(name) {{
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  const p = document.getElementById('panel-' + name);
  if (p) {{ p.classList.add('active'); if(name==='view') loadRecords(); }}
}}

async function createTable() {{
  try {{
    const r = await fetch('/api/create-table/{table_name}');
    const d = await r.json();
    if (d.error) {{ showToast('Error: ' + d.error, 'error'); return; }}
    showToast('Table created! Reloading...', 'success');
    setTimeout(() => location.reload(), 1500);
  }} catch(e) {{ showToast('Failed: ' + e, 'error'); }}
}}

async function insertRecord() {{
  {insert_js}
  try {{
    const r = await fetch('/api/insert/{table_name}', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(data)
    }});
    const d = await r.json();
    if (d.error) {{ showToast('Error: ' + d.error, 'error'); return; }}
    showToast('Record saved!', 'success');
  }} catch(e) {{ showToast('Failed: ' + e, 'error'); }}
}}

async function loadRecords() {{
  const div = document.getElementById('recordsTable');
  div.innerHTML = 'Loading...';
  try {{
    const r = await fetch('/api/records/{table_name}');
    const d = await r.json();
    if (!d.records || d.records.length === 0) {{
      div.innerHTML = '<div class="empty">No records yet. Insert one above.</div>';
      return;
    }}
    const cols = Object.keys(d.records[0]);
    div.innerHTML = '<table><thead><tr>' + cols.map(c => `<th>${{c}}</th>`).join('') + '</tr></thead><tbody>' +
      d.records.map(row => '<tr>' + cols.map(c => `<td>${{row[c] ?? ''}}</td>`).join('') + '</tr>').join('') +
      '</tbody></table>';
  }} catch(e) {{ div.innerHTML = '<div class="empty">Failed to load: ' + e + '</div>'; }}
}}

async function dropTable() {{
  if (!confirm('Are you sure? This cannot be undone.')) return;
  try {{
    const r = await fetch('/api/drop/{table_name}', {{method:'DELETE'}});
    const d = await r.json();
    showToast('Table dropped. Redirecting...', 'success');
    setTimeout(() => window.location.href='/api/', 1500);
  }} catch(e) {{ showToast('Failed: ' + e, 'error'); }}
}}
</script>
</body>
</html>"""
    return func.HttpResponse(html, mimetype="text/html", status_code=200)


# ── Create table API ─────────────────────────────────────────
@app.route(route="create-table/{table_name}")
def create_table(req: func.HttpRequest) -> func.HttpResponse:
    table_name = req.route_params.get("table_name")
    logger.info(f"Creating table: {table_name}")
    try:
        conn = get_conn()
        cur = conn.cursor()
        if table_name == "orders":
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    customer_name VARCHAR(100),
                    product VARCHAR(100),
                    amount NUMERIC(10,2),
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW()
                );""")
        elif table_name == "customers":
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    email VARCHAR(100),
                    phone VARCHAR(20),
                    city VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                );""")
        elif table_name == "products":
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    price NUMERIC(10,2),
                    stock INTEGER DEFAULT 0,
                    category VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                );""")
        else:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                );""")
        conn.commit()
        cur.close()
        conn.close()
        return func.HttpResponse(json.dumps({
            "message": f"Table '{table_name}' created successfully",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), mimetype="application/json", status_code=200)
    except Exception as e:
        logger.error(f"Failed: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), mimetype="application/json", status_code=500)


# ── Insert record API ────────────────────────────────────────
@app.route(route="insert/{table_name}", methods=["POST"])
def insert_record(req: func.HttpRequest) -> func.HttpResponse:
    table_name = req.route_params.get("table_name")
    try:
        data = req.get_json()
        conn = get_conn()
        cur = conn.cursor()
        if table_name == "orders":
            cur.execute(
                "INSERT INTO orders (customer_name, product, amount, status) VALUES (%s,%s,%s,%s)",
                (data.get("customer_name"), data.get("product"), data.get("amount"), data.get("status"))
            )
        elif table_name == "customers":
            cur.execute(
                "INSERT INTO customers (name, email, phone, city) VALUES (%s,%s,%s,%s)",
                (data.get("name"), data.get("email"), data.get("phone"), data.get("city"))
            )
        elif table_name == "products":
            cur.execute(
                "INSERT INTO products (name, price, stock, category) VALUES (%s,%s,%s,%s)",
                (data.get("name"), data.get("price"), data.get("stock"), data.get("category"))
            )
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Record inserted into {table_name}")
        return func.HttpResponse(json.dumps({"message": "Record inserted"}), mimetype="application/json", status_code=200)
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), mimetype="application/json", status_code=500)


# ── View records API ─────────────────────────────────────────
@app.route(route="records/{table_name}")
def get_records(req: func.HttpRequest) -> func.HttpResponse:
    table_name = req.route_params.get("table_name")
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 50;")
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, [str(v) if v is not None else None for v in row])) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return func.HttpResponse(json.dumps({"records": rows, "count": len(rows)}), mimetype="application/json", status_code=200)
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e), "records": []}), mimetype="application/json", status_code=500)


# ── Drop table API ───────────────────────────────────────────
@app.route(route="drop/{table_name}", methods=["DELETE"])
def drop_table(req: func.HttpRequest) -> func.HttpResponse:
    table_name = req.route_params.get("table_name")
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Table {table_name} dropped")
        return func.HttpResponse(json.dumps({"message": f"Table {table_name} dropped"}), mimetype="application/json", status_code=200)
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), mimetype="application/json", status_code=500)


# ── Health check ─────────────────────────────────────────────
@app.route(route="health")
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "ok", "version": "v2", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}),
        mimetype="application/json", status_code=200
    )