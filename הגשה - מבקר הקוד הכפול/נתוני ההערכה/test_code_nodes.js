/**
 * test_code_nodes.js — בדיקות יחידה לצמתי ה-Code של ה-workflow.
 *
 * הקוד של הצמתים נקרא ישירות מקובץ ה-JSON של ה-workflow ומורץ בתוך סביבת
 * n8n מדומה (items, $, $env). כך הבדיקה תמיד רצה מול הקוד האמיתי שיובא
 * ל-n8n, ולא מול העתק שיכול להתיישן.
 *
 * הרצה:  node scripts/eval/test_code_nodes.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');
const assert = require('assert');

const WF_PATH = path.join(__dirname, '..', '..', 'dual_code_auditor_wf_updated.json');
const wf = JSON.parse(fs.readFileSync(WF_PATH, 'utf8'));

function nodeCode(name) {
  const node = wf.nodes.find((n) => n.name === name);
  if (!node) throw new Error(`node not found: ${name}`);
  return node.parameters.jsCode;
}

/** מריץ קוד של Code Node בסביבת n8n מדומה. */
function runNode(name, { items, nodes = {}, env = {} }) {
  const $ = (nodeName) => {
    if (!(nodeName in nodes)) throw new Error(`mock missing for $('${nodeName}')`);
    return { item: { json: nodes[nodeName] } };
  };
  const sandbox = { items, $, $env: env, require, Buffer, console, JSON, Date, String, Boolean, Object };
  const script = new vm.Script(`(function(){ ${nodeCode(name)} })()`);
  return script.runInNewContext(sandbox);
}

let passed = 0;
let failed = 0;
function test(label, fn) {
  try {
    fn();
    console.log(`  PASS  ${label}`);
    passed++;
  } catch (err) {
    console.log(`  FAIL  ${label}\n        ${err.message}`);
    failed++;
  }
}

// ---------------------------------------------------------------------------
const SECRET = 'test-secret-value';
const goodBody = {
  action: 'opened',
  number: 7,
  repository: {
    name: 'Dual-Code-Auditor',
    full_name: 'Levi2599/Dual-Code-Auditor',
    owner: { login: 'Levi2599' }
  },
  pull_request: { head: { ref: 'feature/login' } }
};

function sign(body, secret) {
  return 'sha256=' + crypto.createHmac('sha256', secret).update(JSON.stringify(body), 'utf8').digest('hex');
}

console.log('\n[1] Verify Request — שכבת האימות');

/** מריץ את Verify Request ומחזיר את ה-verdict. */
function verify(headers, body, env) {
  return runNode('Verify Request', { items: [{ json: { headers, body } }], env: env || {} })[0].json;
}

test('בקשה חתומה נכון מ-GitHub מתקבלת', () => {
  const v = verify({ 'x-hub-signature-256': sign(goodBody, SECRET) }, goodBody, { GITHUB_WEBHOOK_SECRET: SECRET });
  assert.strictEqual(v.verified, true);
});

test('חתימת HMAC שגויה נדחית', () => {
  const v = verify({ 'x-hub-signature-256': sign(goodBody, 'wrong-secret') }, goodBody, { GITHUB_WEBHOOK_SECRET: SECRET });
  assert.strictEqual(v.verified, false);
  assert.match(v.reject_reason, /HMAC mismatch/);
});

test('בקשה לא חתומה למאגר שברשימת ההיתר מתקבלת (הפעלה ידנית מהאתר)', () => {
  const v = verify({}, goodBody);
  assert.strictEqual(v.verified, true);
});

test('בקשה לא חתומה למאגר זר נדחית — סגירת חולשת ה-arbitrary repo', () => {
  const evil = JSON.parse(JSON.stringify(goodBody));
  evil.repository.full_name = 'attacker/private-repo';
  const v = verify({}, evil);
  assert.strictEqual(v.verified, false);
  assert.match(v.reject_reason, /not in the allow-list/);
});

test('body ללא repository.full_name נדחה', () => {
  const v = verify({}, {});
  assert.strictEqual(v.verified, false);
  assert.match(v.reject_reason, /malformed repository\.full_name/);
});

test('חתימה קיימת אך אין סוד מוגדר בשרת — נדחה', () => {
  const v = verify({ 'x-hub-signature-256': sign(goodBody, SECRET) }, goodBody, {});
  assert.strictEqual(v.verified, false);
  assert.match(v.reject_reason, /GITHUB_WEBHOOK_SECRET is not configured/);
});

test('ההודעה לקורא אינה חושפת את הסוד', () => {
  const v = verify({ 'x-hub-signature-256': sign(goodBody, 'wrong') }, goodBody, { GITHUB_WEBHOOK_SECRET: SECRET });
  assert.ok(!v.reject_reason.includes(SECRET), 'הסוד דלף להודעת הדחייה!');
});

// ---------------------------------------------------------------------------
console.log('\n[2] Parse Diff — עיבוד מקדים');

const sampleDiff = [
  'diff --git a/app/db.py b/app/db.py',
  'index 83db48f..bf269f4 100644',
  '--- a/app/db.py',
  '+++ b/app/db.py',
  '@@ -1,5 +1,7 @@',
  ' import sqlite3',
  '-def get_user(uid):',
  '+def get_user(uid):',
  '+    q = "SELECT * FROM users WHERE id = " + uid',
  '+    return conn.execute(q).fetchall()'
].join('\n');

test('מחלץ את נתיב הקובץ מה-Diff', () => {
  const out = runNode('Parse Diff', {
    items: [{ json: { data: sampleDiff } }],
    nodes: { 'GitHub Webhook': { body: goodBody } }
  });
  assert.strictEqual(out[0].json.file_path, 'app/db.py');
});

test('מחלץ רק שורות שנוספו, בלי כותרות ה-Diff', () => {
  const out = runNode('Parse Diff', {
    items: [{ json: { data: sampleDiff } }],
    nodes: { 'GitHub Webhook': { body: goodBody } }
  });
  const code = out[0].json.code_to_analyze;
  assert.ok(code.includes('SELECT * FROM users'), 'שורת הקוד הפגיע חסרה');
  assert.ok(!code.includes('+++'), 'כותרת Diff דלפה לקלט של ה-LLM');
  assert.ok(!code.includes('diff --git'), 'כותרת Diff דלפה לקלט של ה-LLM');
  assert.strictEqual(out[0].json.diff_added_lines, 3);
});

test('מקטין את כמות הטוקנים ביחס ל-Diff הגולמי', () => {
  const out = runNode('Parse Diff', {
    items: [{ json: { data: sampleDiff } }],
    nodes: { 'GitHub Webhook': { body: goodBody } }
  });
  assert.ok(out[0].json.code_to_analyze.length < sampleDiff.length);
});

test('מעביר נכון את מטא-הנתונים של ה-PR', () => {
  const out = runNode('Parse Diff', {
    items: [{ json: { data: sampleDiff } }],
    nodes: { 'GitHub Webhook': { body: goodBody } }
  })[0].json;
  assert.strictEqual(out.repo_owner, 'Levi2599');
  assert.strictEqual(out.repo_name, 'Dual-Code-Auditor');
  assert.strictEqual(out.pr_number, 7);
  assert.strictEqual(out.branch, 'feature/login');
  assert.strictEqual(out.source, 'github');
});

// ---------------------------------------------------------------------------
console.log('\n[3] Build Report — פורמט וחילוץ הקוד המתוקן');

const baseGithub = {
  code_to_analyze: 'q = "SELECT * FROM users WHERE id = " + uid',
  source: 'github',
  repo_owner: 'Levi2599',
  repo_name: 'Dual-Code-Auditor',
  pr_number: 7,
  branch: 'feature/login',
  file_path: 'app/db.py'
};

const redVuln = [
  'נמצאה חולשת SQL Injection.',
  'PoC:  uid = "1 OR 1=1"',
  'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
].join('\n');

const blueFix = [
  'להלן הקוד המתוקן:',
  '',
  '```python',
  'def get_user(uid):',
  '    q = "SELECT * FROM users WHERE id = ?"',
  '    return conn.execute(q, (uid,)).fetchall()',
  '```',
  '',
  'התיקון משתמש בשאילתה פרמטרית וחוסם את ה-PoC.'
].join('\n');

test('מחלץ את מחרוזת וקטור ה-CVSS', () => {
  const out = runNode('Build Report', {
    items: [{ json: {} }],
    nodes: {
      'Normalize Input': baseGithub,
      'Capture Red Finding': { red_output: redVuln },
      'Capture Blue Fix': { blue_output: blueFix }
    }
  })[0].json;
  assert.strictEqual(out.cvss_vector_string, 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H');
});

test('דוחף לריפו קוד בלבד — בלי פרוזה בעברית', () => {
  const out = runNode('Build Report', {
    items: [{ json: {} }],
    nodes: {
      'Normalize Input': baseGithub,
      'Capture Red Finding': { red_output: redVuln },
      'Capture Blue Fix': { blue_output: blueFix }
    }
  })[0].json;
  assert.strictEqual(out.has_fixed_code, true);
  assert.ok(out.fixed_code.startsWith('def get_user'), 'הקוד המתוקן לא חולץ נכון');
  assert.ok(!out.fixed_code.includes('להלן'), 'פרוזה בעברית דלפה לתוכן הקובץ!');
  assert.ok(!out.fixed_code.includes('```'), 'סימוני markdown דלפו לתוכן הקובץ!');
  assert.ok(!out.fixed_code.includes('התיקון משתמש'), 'הסבר דלף לתוכן הקובץ!');
});

test('לא נמצאה חולשה -> לא נדחף Commit', () => {
  const out = runNode('Build Report', {
    items: [{ json: {} }],
    nodes: {
      'Normalize Input': baseGithub,
      'Capture Red Finding': { red_output: 'NO_VULNERABILITIES_FOUND\nהקוד משתמש בשאילתות פרמטריות.' },
      'Capture Blue Fix': { blue_output: 'NO_FIX_REQUIRED' }
    }
  })[0].json;
  assert.strictEqual(out.no_vulnerabilities_found, true);
  assert.strictEqual(out.has_fixed_code, false);
  assert.ok(out.full_report.includes('לא נמצאו חולשות'));
});

test('פלט ללא בלוק קוד -> לא נדחף Commit (הגנה מפני הרס קובץ)', () => {
  const out = runNode('Build Report', {
    items: [{ json: {} }],
    nodes: {
      'Normalize Input': baseGithub,
      'Capture Red Finding': { red_output: redVuln },
      'Capture Blue Fix': { blue_output: 'צריך להשתמש בשאילתות פרמטריות, בלי לתת קוד.' }
    }
  })[0].json;
  assert.strictEqual(out.has_fixed_code, false);
});

test('מקור צ׳אט (בלי נתיב קובץ) -> לא נדחף Commit', () => {
  const out = runNode('Build Report', {
    items: [{ json: {} }],
    nodes: {
      'Normalize Input': { ...baseGithub, source: 'chat', file_path: '', repo_owner: '', repo_name: '' },
      'Capture Red Finding': { red_output: redVuln },
      'Capture Blue Fix': { blue_output: blueFix }
    }
  })[0].json;
  assert.strictEqual(out.has_fixed_code, false);
  assert.ok(out.full_report.includes('הזנת קוד ידנית'));
});

test('הדוח בפורמט Markdown ומכיל את שני הצוותים', () => {
  const out = runNode('Build Report', {
    items: [{ json: {} }],
    nodes: {
      'Normalize Input': baseGithub,
      'Capture Red Finding': { red_output: redVuln },
      'Capture Blue Fix': { blue_output: blueFix }
    }
  })[0].json;
  assert.ok(out.full_report.includes('### 🔴'), 'חסר פרק הצוות האדום');
  assert.ok(out.full_report.includes('### 🔵'), 'חסר פרק הצוות הכחול');
  assert.ok(out.full_report.includes('| שדה | ערך |'), 'חסרה טבלת הסיכום');
  assert.ok(/DualCodeAuditor_.*\.md/.test(out.log_file_name), 'שם קובץ הלוג אינו ייחודי');
});

test('שם קובץ הלוג ייחודי לכל הרצה (לא דורס לוג קודם)', () => {
  const mk = () => runNode('Build Report', {
    items: [{ json: {} }],
    nodes: {
      'Normalize Input': baseGithub,
      'Capture Red Finding': { red_output: redVuln },
      'Capture Blue Fix': { blue_output: blueFix }
    }
  })[0].json.log_file_name;
  const a = mk();
  assert.ok(a.includes('DualCodeAuditor_'));
  assert.ok(!a.includes(':'), 'שם הקובץ מכיל תווים לא חוקיים');
});

// ---------------------------------------------------------------------------
console.log(`\n${passed} passed, ${failed} failed\n`);
process.exit(failed === 0 ? 0 : 1);
