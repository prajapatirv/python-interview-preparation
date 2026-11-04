"""Builds the single-file Interview Answer Map page from the bank files and the hub README.

Writes out/interview-answer-map.html, plus out/unread.txt and out/unread.json: the plan questions
whose answers nobody has read yet. See README.md in this folder.
"""
import html
import pathlib
import re
import sys

here = pathlib.Path(__file__).resolve().parent
root = here.parents[2]
sys.path.insert(0, str(root / 'interview-coach'))
from markdown_it import MarkdownIt
from app.services.bank import parse_questions
from app.services.library import Library
from app.services import tracks
import json

md = MarkdownIt('commonmark', {'html': False}).enable('table')
base = root / 'java/java-interview-prep/interview-scenarios'
hub = (root / 'java/java-interview-prep/reported-interviews/README.md').read_text(encoding='utf-8').replace('\r\n', '\n')
examples = root / 'java/java-interview-prep/examples/21_coding_interview'

GROUPS = [
    ('95', 'Streams: coding', 'Java'), ('96', 'Streams: concepts', 'Java'), ('97', 'Senior core Java', 'Java'),
    ('98', 'Spring backend', 'Spring'), ('99', 'API design', 'Spring'), ('88', 'Databases', 'Data'),
    ('89', 'Production and Kafka', 'Production'), ('33', 'AWS basics', 'Cloud'),
    ('69', 'GenAI fundamentals', 'GenAI'), ('67', 'RAG and vector databases', 'GenAI'),
    ('66', 'Spring AI', 'GenAI'), ('68', 'Agents and MCP', 'GenAI'),
]
NEW = {g[0] for g in GROUPS}
SHORT = {g[0]: g[1] for g in GROUPS}
OLD_LABEL = {'02': 'Kafka consumers', '05': 'Third-party APIs', '07': 'CPU and memory', '08': 'Measurement tools', '20': 'Java core',
             '21': 'Spring Boot', '22': 'Kafka', '24': 'Microservices', '30': 'Architecture', '61': 'Spring Boot round', '62': 'Kafka round',
             '70': 'Core Java', '71': 'Spring Boot', '72': 'Spring MVC', '73': 'Cloud microservices', '74': 'Event-driven', '77': 'RAG design',
             '78': 'MCP server', '83': 'Core Java', '85': 'Spring Boot', '86': 'System design', '87': 'Java 17', '90': 'System design',
             '91': 'Auto-configuration', '93': 'Java 8', '94': 'Project deep dive'}
refs = {(b, int(n)) for b, n in re.findall(r'[Bb]ank (\d+) Q(\d+)', hub) if b not in NEW}
parsed = {}


def bank(b):
    if b not in parsed:
        parsed[b] = parse_questions(next(base.glob(b + '_*.md')).read_text(encoding='utf-8'))
    return parsed[b]


included = {(b, q['num']) for b in NEW for q in bank(b)[2]} | refs


def label_for(b, n):
    return f"{SHORT.get(b) or OLD_LABEL.get(b, 'Answer')} Q{n}"


def linkify(text):
    """Turn "Bank N Qm" into in-page links where the answer is on the page."""
    def repl(m):
        b, n = m.group(1), int(m.group(2))
        if (b, n) in included:
            return f'<a class="ref" href="#q-{b}-{n}">{html.escape(label_for(b, n))}</a>'
        return f'<span class="xref" title="In the source repository, not on this page">{m.group(0)}</span>'
    return re.sub(r'[Bb]ank (\d+) Q(\d+)', repl, text)


def render(text):
    out = md.render(text)
    out = out.replace('<table>', '<div class="tw"><table>').replace('</table>', '</table></div>')
    return linkify(out)


def question_html(b, q, topic, group):
    secs = []
    if not q['sections']:   # crib-sheet answers have no labelled sections
        secs.append(f'<section class="sec plain">{render(q["body"])}</section>')
    for s in q['sections']:
        cls = 'spoken' if s['key'] == 'spoken' else ''
        secs.append(f'<section class="sec {cls}" data-key="{s["key"]}"><h4>{html.escape(s["label"])}</h4>{render(s["md"])}</section>')
    plain = ' '.join([q['title'], ' '.join(q['tags']), q['body']]).lower()
    plain = html.escape(re.sub(r'[*`|#>_\-]+', ' ', plain), quote=True)
    level = q.get('level') or 'mid'
    title = md.renderInline(q['title'])
    tags = html.escape(' '.join(q['tags']), quote=True)
    return (f'<details class="q" id="q-{b}-{q["num"]}" data-topic="{topic}" data-level="{level}" data-text="{plain}" data-tags="{tags}">'
            f'<summary><span class="lvl lvl-{level}">{level}</span><span class="qt">{title}</span>'
            f'<span class="qsrc">{html.escape(group)}</span></summary>'
            f'<div class="ans"><label class="done"><input type="checkbox" id="done-{b}-{q["num"]}" data-done="{b}-{q["num"]}"> I can say this aloud</label>'
            f'{"".join(secs)}</div></details>')


def tables_only(intro):
    """Keep only the tables from a bank's introduction; the prose there talks about repo paths."""
    return '\n'.join(l for l in intro.split('\n') if l.startswith('|'))


# ---- answers ----
blocks, total = [], 0
for b, name, topic in GROUPS:
    meta, intro, qs = bank(b)
    extra = ''
    if b in ('95', '69'):
        note = ('<p>The five things to say on any streams question. This is the difference between an SDE-1 and an SDE-2 answer.</p>' if b == '95'
                else '<p>Where each of the 40 concepts is answered, by question number in this group. Top-k here means choosing the next token. In RAG, it means how many chunks to retrieve.</p>')
        table = tables_only(intro)
        if b == '69':
            table = re.sub(r'\| Q(\d+) \|', lambda m: f'| [Q{m.group(1)}](#q-69-{m.group(1)}) |', table)
        extra = f'<div class="gintro">{note}{render(table)}</div>'
    items = ''.join(question_html(b, q, topic, name) for q in qs)
    total += len(qs)
    blocks.append(f'<section class="group" id="bank-{b}" data-topic="{topic}"><h3>{html.escape(name)} <small>{len(qs)}</small></h3>{extra}{items}</section>')

older = []
for b, n in sorted(refs):
    q = next(x for x in bank(b)[2] if x['num'] == n)
    older.append(question_html(b, q, 'Earlier', OLD_LABEL[b]))
blocks.append(f'<section class="group" id="bank-earlier" data-topic="Earlier"><h3>Answers the rounds also point to <small>{len(older)}</small></h3>{"".join(older)}</section>')

# ---- plans by experience (Java). Answers on the page open inline; the rest are listed as questions to practise.
library = Library.load()
page_ids = {}
for b, _, _ in GROUPS:
    for q in bank(b)[2]:
        page_ids[(b, q['num'])] = f'q-{b}-{q["num"]}'
for b, n in refs:
    page_ids[(b, n)] = f'q-{b}-{n}'
plans_data, cribs = [], {}
# Answers read and approved for publishing, batch by batch. Older content stays question-only until it has been read.
reviewed = []
for batch in sorted((here / 'reviewed').glob('batch*.json'), key=lambda p: int(re.search(r'\d+', p.name).group())):
    reviewed += [i for i in json.loads(batch.read_text()) if i not in reviewed]
TIDY = [('This corrects the idea of using it interchangeably with Kafka.', ''),
        ('\n- A JPMC SDE-3 candidate reports being asked this question directly.', ''),
        ('EPAM candidates mention "find the optimal path in a tree".', 'Candidates report being asked to "find the optimal path in a tree".'),
        (' JPMorgan Chase is publicly cited as using it at large scale.', ''),
        ('EPAM candidates report "the', 'Candidates report "the'),
        ('A JPMC candidate reported exactly this follow-up', 'Candidates report exactly this follow-up'),
        (' A JPMC candidate reported a design question of exactly this shape.', ''),
        (' (Infosys, EPAM and similar)', '')]
CROSS_REF = re.compile(r' \((?:see (?:the \w+ bank, )?)?Q\d+\)')
COMPANY_TAG = re.compile(r'chase|jpmc|jpmorgan|epam|nagarro|persistent', re.I)
for summary in tracks.summaries('java'):
    plan = tracks.plan(library, 'java', summary['id'])
    topics = []
    for t in plan['topics']:
        rows = []
        for item in t['questions']:
            full = library.question(item['id'])
            anchor = None
            if full['kind'] == 'scenario':
                anchor = page_ids.get((pathlib.Path(full['source']).name.split('_')[0], full['num']))
                if anchor is None and item['id'] in reviewed:
                    anchor = f'q-x-{item["id"]}'
            elif full['kind'] == 'crib':
                anchor = f'q-c-{item["id"]}'
                cribs[item['id']] = (full, t['title'])
            rows.append({'h': md.renderInline(full['title']), 'l': item['level'], 'a': anchor, 'r': item['reported'], 'id': item['id']})
        topics.append({'title': t['title'], 'weight': t['weight'], 'why': t['why'], 'rows': rows})
    plans_data.append({k: plan[k] for k in ('id', 'label', 'range', 'title', 'expect', 'advice', 'total', 'hours', 'stages', 'stage_order', 'stage_label')} | {'topics': topics})
extra_names = {t.id: t.title for t in library.stack('java').topics}
def tidy(full):
    q = dict(full, num=full['id'])
    q['sections'] = [dict(x, md=x['md']) for x in full['sections']]
    for a, c in TIDY:
        q['body'] = q['body'].replace(a, c)
        for sec in q['sections']:
            sec['md'] = sec['md'].replace(a, c)
    # "(Q10)" points at a number inside the source bank, which means nothing on this page.
    q['body'] = CROSS_REF.sub('', q['body'])
    for sec in q['sections']:
        sec['md'] = CROSS_REF.sub('', sec['md'])
    q['tags'] = [t for t in full['tags'] if not COMPANY_TAG.search(t)]
    return q
quick = [question_html('c', dict(tidy(full), tags=[]), 'Quick', topic) for qid, (full, topic) in cribs.items()]
blocks.append(f'<section class="group" id="bank-quick" data-topic="Quick"><h3>Foundation answers from the plans <small>{len(quick)}</small></h3>{"".join(quick)}</section>')
more = [question_html('x', tidy(library.question(i)), 'Plan answers', extra_names[library.question(i)['topic']]) for i in reviewed]
if more:
    blocks.append(f'<section class="group" id="bank-more" data-topic="Plan answers"><h3>More answers from the plans <small>{len(more)}</small></h3>{"".join(more)}</section>')
total_all = total + len(older) + len(quick) + len(more)
plan_json = json.dumps(plans_data, ensure_ascii=False).replace('</', '<\\/')

# ---- mapped tables from the hub ----


def hub_section(start, end):
    i = hub.index(start)
    j = hub.index(end, i + 1)
    return hub[i:j]


def fix_links(text):
    text = re.sub(r'\(\.\./interview-scenarios/(\d+)_[^)]+\)', lambda m: f'(#bank-{m.group(1)})', text)
    return text


rounds = fix_links(hub_section('### 35 Java Streams questions', '---\n\n## GenAI study material'))
rounds = rounds.replace("The list's tip about complexity, null handling, duplicate keys, performance, and streams vs loops is the table at the top of bank 95.",
                        "The list's tip about complexity, nulls, duplicate keys, performance and loops is the table at the top of the coding group.")
rounds = rounds.replace('Answered in full in banks [95](#bank-95) (coding Q1-Q20) and\n[96](#bank-96) (concepts Q1-Q15), in the same order as the list.',
                        'Answered in full in the [coding](#bank-95) and [concepts](#bank-96) groups, in the same order as the list.')
rounds = rounds.replace('with the coach\'s *Mock interview*, and answer in full sentences.', 'out loud, and answer in full sentences.')
rounds = rounds.replace('Bank 33 (all 15), starting with Q1, Q2, Q5, Q6 and Q7', '[AWS basics](#bank-33): start with Bank 33 Q1, Bank 33 Q2, Bank 33 Q5, Bank 33 Q6, Bank 33 Q7')
genai = fix_links(hub_section('### Gen AI fundamentals (40 concepts)', '### 25 repositories for AI agent developers'))
genai = genai.replace('All 40 are in [bank 69](#bank-69), which opens with a concept-to-answer table.', 'All 40 are in the [GenAI fundamentals](#bank-69) group, which opens with a concept-to-answer table.')
repos = hub_section('### 25 repositories for AI agent developers', '---\n\n## Corrections')
repos = repos.replace('Courses\nback up a project; they don\'t replace one.', 'Courses back up a project; they don\'t replace one.')
corrections = hub_section('## Corrections to the source material', '## Known gaps').split('\n', 1)[1]
corrections = corrections.replace('bank 67 Q6', 'Bank 67 Q6').replace('Bank 68 Q14', 'Bank 68 Q14')

programs = []
for fn, what in [('07_streams_sde2_employee_drills.java', '60 checks: the 35 streams questions on data with ties and nulls'),
                 ('08_reported_rounds_coding_and_internals.java', '32 checks: coins, nearest pair, months, immutable class, proxies, parallel Collector, locks'),
                 ('09_vector_search_and_llm_sampling_from_scratch.java', '32 checks: cosine, ANN recall, chunking, rank fusion, temperature and top-p')]:
    src = (examples / fn).read_text(encoding='utf-8').replace('\r\n', '\n')
    programs.append(f'<details class="prog"><summary><code>{fn}</code><span>{what}</span></summary>'
                    f'<button class="copy" type="button" data-copy>Copy code</button><pre><code>{html.escape(src)}</code></pre></details>')

CSS = (here / 'page.css').read_text(encoding='utf-8')
JS = (here / 'page.js').read_text(encoding='utf-8')
SIDE_HTML = (here / 'side.html').read_text(encoding='utf-8')
SIDE_JS = (here / 'side.js').read_text(encoding='utf-8')
page = f"""<title>Interview Answer Map</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
{SIDE_HTML}
<header class="top">
  <div class="wrap">
    <p class="eyebrow">Java backend and GenAI interviews</p>
    <h1>Interview Answer Map</h1>
    <p class="lede">Questions from real interview reports and popular GenAI study material, each linked to a full answer you can say aloud. {total_all} answers, free to read, and written for working developers.</p>
  </div>
</header>
<nav class="tabs" aria-label="Sections"><div class="wrap">
  <a href="#start">Start here</a><a href="#plans">Plans by experience</a><a href="#rounds">Company rounds</a><a href="#genai">GenAI sources</a><a href="#answers">All answers</a><a href="#code">Run the code</a><a href="#resources">Resources</a><a href="#corrections">Corrections</a>
</div></nav>
<main class="wrap">
<section id="start" class="panel">
  <h2>Start here</h2>
  <div class="how">
    <div><h3>Find your target</h3><p>Look up a company round or a GenAI topic. Each question links to its answer.</p></div>
    <div><h3>Say it aloud</h3><p>Every answer ends with a 60-second version for rapid-fire rounds. The longer points are for when they say "go deeper".</p></div>
    <div><h3>Make it yours</h3><p>The scenarios are examples. Swap in your own work, and never claim experience you don't have. Interviewers ask for details.</p></div>
  </div>
  <p class="caution"><strong>Treat this as likely topics, not a syllabus.</strong> Interview reports are one person's experience, and they vary by team, level and year. Scenarios are illustrative and don't describe any named company's systems. Social-media infographics are often wrong, so <a href="#corrections">check the corrections</a> before repeating them.</p>
  <h3>Study paths</h3>
  <div class="tw"><table>
    <thead><tr><th>Your goal</th><th>Time</th><th>Do this</th></tr></thead>
    <tbody>
    <tr><td>Java interview this week</td><td>5 days</td><td>Day 1-2: <a href="#bank-95">streams coding</a> and <a href="#bank-96">concepts</a>, coding each drill without looking. Day 3: <a href="#bank-98">Spring backend</a>. Day 4: <a href="#bank-97">senior core Java</a>. Day 5: <a href="#bank-89">production and Kafka</a>, <a href="#bank-33">AWS basics</a> Q1-Q7, then a mock interview with a friend.</td></tr>
    <tr><td>New to GenAI</td><td>1 week</td><td><a href="#bank-69">GenAI fundamentals</a> Q1-Q5 and Q9, then <a href="#bank-67">RAG</a> Q1-Q6. Build the mini project in <a class="ref" href="#q-67-14">RAG Q14</a>. Then <a href="#bank-66">Spring AI</a> Q1-Q2.</td></tr>
    <tr><td>Java developer moving to GenAI</td><td>3 weeks</td><td>Week 1: fundamentals and Spring AI. Week 2: RAG, and build it in Spring AI. Week 3: <a href="#bank-68">agents and MCP</a>, and build an MCP server and one agent.</td></tr>
    <tr><td>Senior or architect round</td><td>1 week</td><td><a href="#bank-89">Production and Kafka</a>, <a class="ref" href="#q-99-1">the 12 API patterns</a>, <a class="ref" href="#q-97-5">shared HashMap</a>, <a class="ref" href="#q-97-6">all requests timing out</a>, <a class="ref" href="#q-88-1">MVCC</a>, <a class="ref" href="#q-88-4">SQL vs NoSQL for money</a>, <a class="ref" href="#q-68-3">workflow or agent</a>, <a class="ref" href="#q-68-8">MCP security</a>.</td></tr>
    </tbody></table></div>
</section>
<section id="plans" class="panel">
  <h2>Plans by experience</h2>
  <p>Choose your level to see the topics and questions that matter most for it. The choice of topics is an experienced trainer's judgement, based on the reported rounds here, not survey data. These plans are for Java roles.</p>
  <div class="tp" id="tp" role="group" aria-label="Choose your experience"></div>
  <div id="tp-body"></div>
</section>
<section id="rounds" class="panel prose"><h2>Company rounds</h2>{render(rounds)}<p class="note">The Mastercard list was only partly visible in the post it came from, so questions 1-12 are missing.</p></section>
<section id="genai" class="panel prose"><h2>GenAI sources</h2>{render(genai)}</section>
<section id="answers" class="panel">
  <h2>All answers</h2>
  <div class="tools" role="search">
    <label class="srch"><span>Search answers</span><input id="q" type="search" placeholder="Try: HashMap, hybrid search, 429, OAuth" autocomplete="off"></label>
    <div class="chips" id="topics" role="group" aria-label="Filter by topic"></div>
    <div class="row2">
      <div class="seg" role="group" aria-label="Answer length"><button type="button" id="m-full" class="on">Full answers</button><button type="button" id="m-short">60-second only</button></div>
      <select id="lvl" aria-label="Filter by level"><option value="">All levels</option><option value="fresher">Fresher</option><option value="mid">Mid</option><option value="senior">Senior</option><option value="architect">Architect</option></select>
      <p id="count" class="count" aria-live="polite"></p>
    </div>
  </div>
  <p class="note">Open a question to read its answer. A dotted reference such as <span class="xref">bank 31 Q10</span> points to fuller material in the source repository, which isn't on this page.</p>
  <p id="empty" class="empty" hidden>No answers match. Try a shorter word, or clear the filters.</p>
  {"".join(blocks)}
</section>
<section id="code" class="panel"><h2>Run the code</h2>
  <p>These three programs ran and passed, and they're where the numbers in the answers come from. Each is a single file with no dependencies. Copy one, then run it on JDK 21 or later: <code>java FileName.java</code>.</p>
  {"".join(programs)}
</section>
<section id="resources" class="panel prose"><h2>Resources</h2>{render(repos)}</section>
<section id="corrections" class="panel prose"><h2>Corrections to the source material</h2>{render(corrections)}
  <h3>Sources for these checks</h3>
  <ul class="srcs">
    <li><a href="https://docs.spring.io/spring-boot/4.0/system-requirements.html">Spring Boot 4.0 system requirements</a></li>
    <li><a href="https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.0.0-M1-Release-Notes">Spring Boot 2.0 M1 release notes</a></li>
    <li><a href="https://docs.spring.io/spring-boot/docs/1.2.1.RELEASE/reference/html/getting-started-system-requirements.html">Spring Boot 1.2 system requirements</a></li>
    <li><a href="https://spring.io/blog/2026/06/12/spring-ai-2-0-0-GA-available-now/">Spring AI 2.0 GA</a> and <a href="https://spring.io/blog/2026/09/25/spring-ai-2-1-0-M1-available-now/">2.1.0-M1</a></li>
    <li><a href="https://docs.spring.io/spring-ai/reference/api/advisors.html">Spring AI reference</a></li>
    <li><a href="https://modelcontextprotocol.net/specification/2026-07-28/changelog.md">MCP 2026-07-28 changelog</a></li>
    <li><a href="https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year?hs_amp=true">A2A at one year, Linux Foundation</a></li>
    <li><a href="https://claude.com/platform/claude-managed-agents">Claude Managed Agents</a> and <a href="https://code.claude.com/docs/en/agent-sdk/overview">Agent SDK overview</a></li>
    <li><a href="https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html">Lambda quotas</a>, <a href="https://aws.amazon.com/s3/consistency/">S3 consistency</a>, <a href="https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/quotas-messages.html">SQS quotas</a></li>
    <li><a href="https://www.habuma.com/springairecipes/">Spring AI Recipes by Craig Walls</a></li>
  </ul>
  <p class="note">Facts were checked on 3 and 4 November 2026. Versions and limits change, so confirm anything you plan to rely on.</p>
</section>
</main>
<script type="application/json" id="plan-data">{plan_json}</script>
<script>{JS}</script>
<script>{SIDE_JS}</script>
"""
out = here / 'out'
out.mkdir(exist_ok=True)
page = page.replace('EPAM candidates report &quot;the', 'Candidates report &quot;the').replace(' in JPMC system-design rounds', ' in system-design rounds')
(out / 'interview-answer-map.html').write_text(page, encoding='utf-8', newline='\n')
print('questions', total, '+', len(older), 'bytes', len(page.encode('utf-8')))
plan_anchors = set(re.findall(r'"a": "(q-[^"]+)"', page))
print('plan anchors without an answer', sorted(a for a in plan_anchors if f'id="{a}"' not in page)[:5])
dead = sorted(set(re.findall(r'href="#(q-[\d]+-\d+|bank-\w+)"', page)) - set(re.findall(r'id="(q-[\d]+-\d+|bank-\w+)"', page)))
print('dead in-page links', dead)
# Private words to check for go in out/banned.txt, one per line. The repo is public, so they can't live here.
banned = out / 'banned.txt'
words = ['../', 'interview-coach', 'reported-interviews', 'coach', 'gmail', 'hackathon'] + (banned.read_text(encoding='utf-8').split('\n') if banned.exists() else [])
print('leftovers', {k: page.count(k) for k in words if k})
print([(p['label'], p['total'], sum(1 for t in p['topics'] for r in t['rows'] if r['a'])) for p in plans_data])

# ---- what still needs reading: questions in a plan with no answer on the page
unread = sorted({r['id'] for p in plans_data for t in p['topics'] for r in t['rows'] if not r['a']},
                key=lambda i: (library.question(i)['source'], library.question(i)['num']))
(out / 'unread.json').write_text(json.dumps(unread), encoding='utf-8')
with (out / 'unread.txt').open('w', encoding='utf-8', newline='\n') as f:
    for i in unread:
        q = library.question(i)
        f.write(f"\n##### {pathlib.Path(q['source']).name} Q{q['num']} {q['title']}\n")
        f.write(''.join(f"**{sec['label']}**\n{sec['md']}\n\n" for sec in q['sections']) or q['body'] + '\n')
print('unread', len(unread), 'questions,', (out / 'unread.txt').stat().st_size, 'bytes')
