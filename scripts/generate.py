#!/usr/bin/env python3
"""Builds assets/header.svg (terrain = your real contribution history) and
assets/live.svg (live dashboard) from the GitHub API. Run by the
'Update live assets' workflow. Without a token it renders a clearly labelled
preview instead of inventing numbers."""
import os, sys, json, math, random, datetime as dt, urllib.request
from xml.sax.saxutils import escape as esc

USER = os.environ.get('GH_USER') or 'gouravcodessometimes'
TOKEN = os.environ.get('GITHUB_TOKEN', '')
FAKE = '--fake' in sys.argv          # layout testing only
OUT = os.environ.get('OUT_DIR') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')

FG, MID, DIM = '#F2F2F2', '#9A9A9A', '#6B6B6B'
SANS = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
G = "M8.5 0H34V25.5L25.5 34H0V8.5L8.5 0ZM27 18.3901V13.14C27 11.2464 26.2477 9.43029 24.9087 8.09127C23.5697 6.75225 21.7536 6 19.86 6H13.5599C12.3068 6 11.1049 6.49781 10.2188 7.38393C9.33272 8.27004 8.8349 9.47187 8.8349 10.725C8.8349 11.9782 9.33272 13.18 10.2188 14.0661C11.1049 14.9522 12.3068 15.4501 13.5599 15.4501H21.12V11.88H13.5599C13.2536 11.88 12.9598 11.7583 12.7432 11.5417C12.5266 11.3251 12.4049 11.0314 12.4049 10.725C12.4049 10.4187 12.5266 10.1249 12.7432 9.90831C12.9598 9.69171 13.2536 9.57002 13.5599 9.57002H19.86C20.8068 9.57002 21.7148 9.94615 22.3843 10.6157C23.0539 11.2852 23.43 12.1932 23.43 13.14V14.82L27 18.3901ZM5.99989 14.61V19.8601C5.99989 21.7537 6.75214 23.5698 8.09116 24.9088C9.43017 26.2479 11.2463 27.0001 13.1399 27.0001H19.44C20.6931 27.0001 21.8949 26.5023 22.7811 25.6162C23.6672 24.7301 24.165 23.5282 24.165 22.2751C24.165 21.0219 23.6672 19.8201 22.7811 18.934C21.8949 18.0479 20.6931 17.5501 19.44 17.5501H11.8799V21.1201H19.44C19.7463 21.1201 20.0401 21.2418 20.2567 21.4584C20.4733 21.675 20.595 21.9688 20.595 22.2751C20.595 22.5814 20.4733 22.8752 20.2567 23.0918C20.0401 23.3084 19.7463 23.4301 19.44 23.4301H13.1399C12.1931 23.4301 11.285 23.054 10.6155 22.3845C9.94603 21.715 9.56991 20.8069 9.56991 19.8601V18.1801L5.99989 14.61Z"

# ------------------------------------------------------------------ data
def _req(url, body=None):
    h = {'Authorization': 'bearer ' + TOKEN, 'User-Agent': 'profile-readme', 'Accept': 'application/vnd.github+json'}
    if body is not None:
        h['Content-Type'] = 'application/json'
    r = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(r, timeout=30) as f:
        return json.load(f)

Q = '''query($login:String!){user(login:$login){followers{totalCount}
repositories(ownerAffiliations:OWNER,isFork:false,first:100,orderBy:{field:PUSHED_AT,direction:DESC}){totalCount nodes{stargazerCount languages(first:6,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount date weekday}}}}}}'''

def fetch_live():
    u = _req('https://api.github.com/graphql', json.dumps({'query': Q, 'variables': {'login': USER}}).encode())['data']['user']
    weeks = []
    for w in u['contributionsCollection']['contributionCalendar']['weeks']:
        row = [None] * 7
        for d in w['contributionDays']:
            row[d['weekday']] = (dt.date.fromisoformat(d['date']), d['contributionCount'])
        weeks.append(row)
    langs = {}
    stars = 0
    for r in u['repositories']['nodes']:
        stars += r['stargazerCount']
        for e in r['languages']['edges']:
            langs[e['node']['name']] = langs.get(e['node']['name'], 0) + e['size']
    events = []
    try:
        for e in _req(f'https://api.github.com/users/{USER}/events/public?per_page=60'):
            repo = e['repo']['name'].split('/')[-1]
            if e['type'] == 'PushEvent':
                c = e['payload'].get('commits') or []
                msg = (c[-1]['message'].split('\n')[0] if c else 'push')
            elif e['type'] == 'PullRequestEvent':
                msg = 'PR ' + e['payload']['action'] + ': ' + e['payload']['pull_request']['title']
            else:
                continue
            events.append((repo, msg, dt.datetime.fromisoformat(e['created_at'].replace('Z', '+00:00'))))
            if len(events) == 5:
                break
    except Exception:
        pass
    return dict(demo=False, weeks=weeks, repos=u['repositories']['totalCount'], stars=stars,
                followers=u['followers']['totalCount'], langs=sorted(langs.items(), key=lambda x: -x[1])[:5], events=events)

def sample(live):
    rnd = random.Random(3)
    today = dt.date.today()
    sunday = today - dt.timedelta(days=(today.weekday() + 1) % 7)
    start = sunday - dt.timedelta(weeks=52)
    weeks = []
    for wk in range(53):
        lvl = .5 + .5 * math.sin(wk / 5 + 1) + rnd.random() * .6
        row = [None] * 7
        for wd in range(7):
            d = start + dt.timedelta(days=wk * 7 + wd)
            if d <= today:
                row[wd] = (d, int(max(0, rnd.gauss(lvl * 6, 3))) if rnd.random() > .3 else 0)
        weeks.append(row)
    now = dt.datetime.now(dt.timezone.utc)
    ev = [('dibz-web', 'feat: vendor onboarding flow', now - dt.timedelta(hours=3)),
          ('lume', 'fix: 4-7-8 breathing timer drift', now - dt.timedelta(hours=20)),
          ('design-tokens', 'chore: spacing scale v2', now - dt.timedelta(days=2)),
          ('portfolio', 'perf: lazy-load case studies', now - dt.timedelta(days=3)),
          ('lume', 'feat: 12-week mood heatmap', now - dt.timedelta(days=5))]
    return dict(demo=not live, weeks=weeks, repos=18, stars=42, followers=31,
                langs=[('TypeScript', 380), ('JavaScript', 300), ('CSS', 140), ('HTML', 90), ('Python', 60)], events=ev)

def load():
    if FAKE:
        return sample(True)
    if TOKEN:
        try:
            return fetch_live()
        except Exception as ex:
            print('fetch failed:', ex, file=sys.stderr)
    return sample(False)

def streaks(weeks):
    days = [x for w in weeks for x in w if x]
    days.sort()
    cur = best = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    i = len(days) - 1
    if i >= 0 and days[i][1] == 0:
        i -= 1                       # today may not have commits yet
    while i >= 0 and days[i][1] > 0:
        cur += 1
        i -= 1
    return cur, best

# ------------------------------------------------------------------ helpers
def smooth(v, s):
    n = len(v); r = int(s * 3) + 1
    k = [math.exp(-(i * i) / (2 * s * s)) for i in range(-r, r + 1)]; z = sum(k)
    return [sum(k[i + r] * v[(j + i) % n] for i in range(-r, r + 1)) / z for j in range(n)]

def bez(p):
    d = f'M{p[0][0]:.1f},{p[0][1]:.1f}'
    for i in range(len(p) - 1):
        p0, p1, p2, p3 = p[max(i - 1, 0)], p[i], p[i + 1], p[min(i + 2, len(p) - 1)]
        d += f' C{p1[0]+(p2[0]-p0[0])/6:.1f},{p1[1]+(p2[1]-p0[1])/6:.1f} {p2[0]-(p3[0]-p1[0])/6:.1f},{p2[1]-(p3[1]-p1[1])/6:.1f} {p2[0]:.1f},{p2[1]:.1f}'
    return d

def ago(t):
    s = (dt.datetime.now(dt.timezone.utc) - t).total_seconds()
    return 'just now' if s < 3600 and s < 120 else f'{int(s//60)}m' if s < 3600 else f'{int(s//3600)}h' if s < 86400 else f'{int(s//86400)}d'

def num(n): return f'{n:,}'

# ------------------------------------------------------------------ header
def header(D):
    H = 400
    weeks = D['weeks']; n = len(weeks)
    tot = [sum(c for x in w if x for c in [x[1]]) for w in weeks]
    mx = max(tot) or 1
    nv = [(t / mx) ** .65 for t in tot]
    total = sum(tot); cur, best = streaks(weeks)
    layers = ''
    for roll, sig, base, amp, fill, so, dur in ((31, 3.6, 330, 70, '#1B1B1B', .12, 300), (17, 2.2, 366, 86, '#101010', .2, 200), (0, .8, 404, 124, '#050505', .38, 140)):
        v = smooth([nv[(i + roll) % n] for i in range(n)], sig)
        pts = [(i * 1200 / n, base - amp * (.1 + .9 * v[i % n])) for i in range(2 * n + 1)]
        top = bez(pts)
        extra = ''
        if roll == 0 and not D['demo']:
            p = max(range(n), key=lambda i: tot[i]); x = p * 1200 / n; y = pts[p][1]
            first = next(d for d in weeks[p] if d)[0]
            lab = f'PEAK WEEK  {tot[p]}  /  WK OF {first:%d %b}'.upper()
            for off in (0, 1200):
                extra += f'<path d="M{x+off:.1f},{y:.1f}v-16" stroke="#fff" stroke-opacity=".6"/><circle cx="{x+off:.1f}" cy="{y:.1f}" r="2.2" fill="#fff"/><text x="{x+off:.1f}" y="{y-22:.1f}" text-anchor="middle" font-family="{MONO}" font-size="9" letter-spacing="2" fill="{MID}" stroke="none">{lab}</text>'
        layers += f'''<g><animateTransform attributeName="transform" type="translate" from="0 0" to="-1200 0" dur="{dur}s" repeatCount="indefinite"/>
<path d="{top} L2400,{H} L0,{H} Z" fill="{fill}"/><path d="{top}" fill="none" stroke="#fff" stroke-opacity="{so}"/>{extra}</g>'''
    rnd = random.Random(11); stars = ''
    while stars.count('<circle') < 70:
        x, y = rnd.uniform(20, 1180), rnd.uniform(16, 225)
        if 280 < x < 920 and 24 < y < 222: continue
        r, o = rnd.choice([.7, .9, 1.1, 1.4]), rnd.choice([.35, .5, .7])
        stars += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{o}"><animate attributeName="opacity" values="{o};{o*.2:.2f};{o}" dur="{rnd.uniform(3,8):.1f}s" begin="{rnd.uniform(0,6):.1f}s" repeatCount="indefinite"/></circle>'
    roles = ['Designing 0-to-1 products', 'Building design systems', 'Shipping accessible React', 'Prototyping with AI']
    CY = 16.0; rc = ''; rt = ''
    for i, r in enumerate(roles):
        L = len(r) + 2; wd = L * 10; x0 = 600 - wd / 2; s = i * 4.0 / CY; a = s + .9 / CY; b = s + 3.2 / CY; c = s + 3.7 / CY
        rc += f'<clipPath id="r{i}"><rect x="{x0-4:.0f}" y="190" width="0" height="22"><animate attributeName="width" values="0;0;{wd+8};{wd+8};0;0" keyTimes="0;{s:.4f};{a:.4f};{b:.4f};{c:.4f};1" dur="{CY}s" begin="1.6s" repeatCount="indefinite"/></rect></clipPath>'
        rt += f'<g clip-path="url(#r{i})"><text x="{x0:.0f}" y="206" font-family="{MONO}" font-size="14" letter-spacing="1.5" fill="{FG}"><tspan fill="{DIM}">&gt; </tspan>{esc(r)}</text></g>'
    left = 'TERRAIN = YOUR LAST 52 WEEKS  /  SYNC PENDING' if D['demo'] else f'TERRAIN = LAST 52 WEEKS  /  {num(total)} CONTRIBUTIONS  /  {cur}D STREAK'
    right = 'PREVIEW' if D['demo'] else f'SYNCED {dt.datetime.now(dt.timezone.utc):%Y-%m-%d} UTC'
    return f'''<svg width="1200" height="{H}" viewBox="0 0 1200 {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Gourav - Product Designer and Frontend Engineer. The terrain is generated from contribution history.">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#040404"/><stop offset=".72" stop-color="#242424"/><stop offset="1" stop-color="#303030"/></linearGradient>
<radialGradient id="vig" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".7"/></radialGradient>
<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" fill-opacity=".04"/></pattern>
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .9 0"/></filter>
<clipPath id="rd"><rect width="1200" height="{H}" rx="10"/></clipPath>
<clipPath id="nm"><rect x="0" y="100" width="0" height="56"><animate attributeName="width" from="0" to="1200" dur="1.4s" begin=".9s" fill="freeze"/></rect></clipPath>{rc}</defs>
<g clip-path="url(#rd)"><rect width="1200" height="{H}" fill="url(#sky)"/>{stars}
<circle cx="930" cy="262" r="58" fill="#fff" fill-opacity=".06"/><circle cx="930" cy="262" r="84" fill="none" stroke="#fff" stroke-opacity=".07"/><circle cx="930" cy="262" r="116" fill="none" stroke="#fff" stroke-opacity=".04" stroke-dasharray="2 8"/>
{layers}
<rect width="1200" height="{H}" fill="url(#scan)"/><rect y="-90" width="1200" height="90" fill="url(#bar)"><animate attributeName="y" from="-90" to="{H}" dur="9s" repeatCount="indefinite"/></rect>
<rect width="1200" height="{H}" filter="url(#grain)" opacity=".05"/><rect width="1200" height="{H}" fill="url(#vig)"/>
<g transform="translate(576 34) scale(1.4)"><path d="{G}" fill="none" stroke="#fff" stroke-width=".5" stroke-opacity=".9" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100" fill-rule="evenodd"><animate attributeName="stroke-dashoffset" from="100" to="0" dur="1.7s" begin=".2s" fill="freeze"/></path>
<path d="{G}" fill="{FG}" fill-rule="evenodd" opacity="0"><animate attributeName="opacity" from="0" to="1" dur=".7s" begin="1.5s" fill="freeze"/></path></g>
<g clip-path="url(#nm)"><text x="610" y="142" text-anchor="middle" font-family="{SANS}" font-weight="300" font-size="50" letter-spacing="20" fill="{FG}">GOURAV</text></g>
<text x="600" y="176" text-anchor="middle" font-family="{MONO}" font-size="12.5" letter-spacing="6" fill="{MID}" opacity="0">PRODUCT DESIGNER  x  FRONTEND ENGINEER<animate attributeName="opacity" from="0" to="1" dur="1.2s" begin="1.6s" fill="freeze"/></text>
{rt}
<rect y="{H-52}" width="1200" height="52" fill="#000" fill-opacity=".82"/><rect y="{H-52}" width="1200" height="1" fill="#fff" fill-opacity=".1"/>
<g stroke="#fff" stroke-opacity=".28" stroke-width="1.2" fill="none"><path d="M22 44V22H44"/><path d="M1178 44V22H1156"/><path d="M22 {H-44}V{H-22}H44"/><path d="M1178 {H-44}V{H-22}H1156"/></g>
<text x="30" y="{H-21}" font-family="{MONO}" font-size="9.5" letter-spacing="2.5" fill="{DIM}">{left}</text>
<text x="1170" y="{H-21}" text-anchor="end" font-family="{MONO}" font-size="9.5" letter-spacing="2.5" fill="{DIM}">{right}</text></g>
<rect x=".5" y=".5" width="1199" height="{H-1}" rx="10" fill="none" stroke="#fff" stroke-opacity=".08"/></svg>'''

# ------------------------------------------------------------------ live dashboard
def panel(x, y, w, h, title, live=False):
    s = f'<g transform="translate({x} {y})"><rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="6" fill="#000" stroke="#2A2A2A"/>'
    s += f'<rect x="6" y=".5" width="40" height="1.5" fill="#fff"><animate attributeName="x" values="6;{w-46};6" dur="{8+(x+y)%5}s" repeatCount="indefinite"/></rect>'
    s += f'<text x="24" y="30" font-family="{MONO}" font-size="10.5" letter-spacing="3" fill="{DIM}">{title}</text>'
    if live:
        s += f'<circle cx="{w-24}" cy="26" r="2.5" fill="#fff"><animate attributeName="opacity" values="1;.15;1" dur="1.8s" repeatCount="indefinite"/></circle><text x="{w-34}" y="30" text-anchor="end" font-family="{MONO}" font-size="9.5" letter-spacing="2" fill="{DIM}">LIVE</text>'
    return s

def live(D):
    weeks = D['weeks']; demo = D['demo']
    tot = sum(x[1] for w in weeks for x in w if x); cur, best = streaks(weeks)
    mx = max((x[1] for w in weeks for x in w if x), default=1) or 1
    ops = [.07, .28, .5, .75, 1]
    o = panel(0, 0, 780, 214, 'CONTRIBUTION MATRIX' + ('  /  PREVIEW' if demo else ''), not demo)
    gx, gy, p = 46, 58, 13
    prev = None
    for c, w in enumerate(weeks):
        d0 = next((x[0] for x in w if x), None)
        if d0 and d0.day <= 7 and d0.month != prev:
            mon = d0.strftime('%b').upper()
            o += f'<text x="{gx+c*p}" y="50" font-family="{MONO}" font-size="8.5" letter-spacing="1" fill="{DIM}">{mon}</text>'; prev = d0.month
        o += f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur=".35s" begin="{c*.03:.2f}s" fill="freeze"/>'
        for r, x in enumerate(w):
            if not x: continue
            lv = 0 if x[1] == 0 else min(4, max(1, math.ceil(4 * x[1] / mx)))
            o += f'<rect x="{gx+c*p}" y="{gy+r*p}" width="10" height="10" rx="2" fill="#fff" fill-opacity="{ops[lv]*(.55 if demo else 1)}"/>'
        o += '</g>'
    for r, l in ((1, 'MON'), (3, 'WED'), (5, 'FRI')):
        o += f'<text x="24" y="{gy+r*p+8}" font-family="{MONO}" font-size="8.5" fill="{DIM}">{l}</text>'
    o += f'<rect x="{gx}" y="{gy}" width="10" height="91" fill="#fff" fill-opacity=".10"><animate attributeName="x" values="{gx};{gx+53*p-10}" dur="9s" begin="3s" repeatCount="indefinite"/></rect>'
    msg = 'preview data  /  waiting for first sync' if demo else f'{num(tot)} contributions in the last year  /  best streak {best} days'
    o += f'<text x="24" y="196" font-family="{MONO}" font-size="10" letter-spacing="1" fill="{MID}">{esc(msg)}</text>'
    lx = 780 - 24 - 28 - 5 * 14
    o += f'<text x="{lx-8}" y="196" text-anchor="end" font-family="{MONO}" font-size="8.5" letter-spacing="1" fill="{DIM}">LESS</text>'
    for i in range(5):
        o += f'<rect x="{lx+i*14}" y="187.5" width="10" height="10" rx="2" fill="#fff" fill-opacity="{ops[i]}"/>'
    o += f'<text x="756" y="196" text-anchor="end" font-family="{MONO}" font-size="8.5" letter-spacing="1" fill="{DIM}">MORE</text></g>'
    # languages
    o += panel(800, 0, 400, 214, 'LANGUAGES', not demo)
    if demo or not D['langs']:
        o += f'<text x="24" y="100" font-family="{MONO}" font-size="11" fill="{DIM}">awaiting first sync</text></g>'
    else:
        shades = ['#FFFFFF', '#BDBDBD', '#8A8A8A', '#5C5C5C', '#3A3A3A']
        z = sum(b for _, b in D['langs']); x = 0; segs = ''
        for i, (nm, b) in enumerate(D['langs']):
            wseg = 352 * b / z; segs += f'<rect x="{24+x:.1f}" y="52" width="{max(wseg-2,1):.1f}" height="8" fill="{shades[i]}"/>'; x += wseg
        o += f'<clipPath id="lg"><rect x="24" y="48" width="0" height="16"><animate attributeName="width" from="0" to="352" dur="1.3s" begin=".4s" fill="freeze"/></rect></clipPath><g clip-path="url(#lg)">{segs}</g>'
        for i, (nm, b) in enumerate(D['langs']):
            y = 100 + i * 22
            o += f'<rect x="24" y="{y-9}" width="8" height="8" fill="{shades[i]}"/><text x="42" y="{y}" font-family="{MONO}" font-size="12" fill="{FG}">{esc(nm)}</text><text x="376" y="{y}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MID}">{100*b/z:.1f}%</text>'
        o += '</g>'
    # activity
    o += panel(0, 230, 780, 200, 'RECENT ACTIVITY', not demo)
    if demo or not D['events']:
        o += f'<text x="24" y="80" font-family="{MONO}" font-size="12" fill="{DIM}">&gt; awaiting first sync. run the "Update live assets" workflow.</text>'
    else:
        for i, (repo, m, t) in enumerate(D['events'][:5]):
            y = 68 + i * 24; m = m if len(m) <= 58 else m[:57] + '...'
            o += f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur=".5s" begin="{.6+i*.25:.2f}s" fill="freeze"/><text x="24" y="{y}" font-family="{MONO}" font-size="12"><tspan fill="{DIM}">&gt; </tspan><tspan fill="{FG}">{esc(repo)}</tspan><tspan fill="{MID}" dx="14">{esc(m)}</tspan></text><text x="756" y="{y}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{DIM}">{ago(t)}</text><rect x="24" y="{y+10}" width="732" height="1" fill="#fff" fill-opacity=".05"/></g>'
        o += f'<text x="24" y="{68+5*24}" font-family="{MONO}" font-size="12" fill="{DIM}">&gt;</text><rect x="38" y="{68+5*24-11}" width="8" height="13" fill="{FG}"><animate attributeName="opacity" values="1;0" dur="1s" calcMode="discrete" repeatCount="indefinite"/></rect>'
    o += '</g>'
    # numbers
    o += panel(800, 230, 400, 200, 'NUMBERS', not demo)
    vals = [('--' if demo else num(tot), 'CONTRIBUTIONS / YR'), ('--' if demo else f'{cur}', 'CURRENT STREAK (DAYS)'),
            ('--' if demo else num(D['repos']), 'PUBLIC REPOS'), ('--' if demo else num(D['stars']), 'STARS EARNED')]
    for i, (v, l) in enumerate(vals):
        x = 24 + (i % 2) * 188; y = 92 + (i // 2) * 70
        o += f'<text x="{x}" y="{y}" font-family="{SANS}" font-weight="300" font-size="38" fill="{FG}">{v}</text><text x="{x}" y="{y+20}" font-family="{MONO}" font-size="9" letter-spacing="2" fill="{DIM}">{l}</text>'
    o += '</g>'
    return f'<svg width="1200" height="430" viewBox="0 0 1200 430" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Live GitHub activity: contribution matrix, languages, recent activity and numbers">{o}</svg>'

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    D = load()
    open(os.path.join(OUT, 'header.svg'), 'w', encoding='utf-8').write(header(D))
    open(os.path.join(OUT, 'live.svg'), 'w', encoding='utf-8').write(live(D))
    print('demo' if D['demo'] else 'live', 'ok ->', os.path.abspath(OUT))
