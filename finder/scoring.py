"""Deal Ladder scoring: ranks UK roles for an ICAEW ACA-qualified auditor (Assistant Manager,
about five years at a Big 4 firm, with a degree) moving into transaction services, corporate finance,
investment banking or private equity. Roles that require previous deal experience are marked so
the page can hide them; "deal experience desirable" is fine.

Scores each vacancy for: pay, how reachable it is for this candidate,
fit with the target areas, and work-from-home options.

All pay figures are annual GBP (US dollar pay is converted, and the dollar figure kept).
When an advert shows no salary, pay is estimated from the employer type and the role's
seniority using the bands below (rough London market levels for 2025-26: base plus
typical bonus; big US finance centres run higher). They are deliberately round numbers;
edit them if you know better.

Every role also gets a one-line summary taken from the advert's own words, the parts of the
advert that play to the candidate's experience ("pros") and the gaps ("flags"). All of it is
plain pattern matching on the advert text - nothing is guessed from the title alone.
"""
import re

from .text import is_london, region_of, US_HUBS

# GBP per USD. run.py replaces this with the day's rate when it can fetch one.
USD_TO_GBP = 0.75
# US pay against the London bands above, in GBP terms.
US_PAY = {"hub": 1.35, "other": 1.15}

LEVELS = ["apprentice", "intern", "entry", "mid", "senior", "exec"]

# Typical total compensation (base + bonus), London, £k, front-office roles.
BANDS = {
    #               apprentice intern entry mid  senior exec
    "prop_trading":  (45, 90, 170, 260, 380, 600),
    "hedge_fund":    (35, 70, 110, 170, 260, 450),
    "pe_megafund":   (35, 70, 120, 210, 320, 600),
    "pe_midmarket":  (30, 50, 75, 120, 190, 320),
    "bulge_bracket": (32, 60, 100, 160, 260, 450),
    "boutique":      (30, 60, 105, 165, 270, 480),
    "big4":          (26, 35, 38, 58, 85, 140),
    "mid_tier":      (24, 30, 34, 52, 75, 120),
    "asset_manager": (28, 40, 52, 80, 120, 200),
    "retail_bank":   (25, 32, 40, 60, 85, 140),
    "fintech":       (28, 40, 52, 80, 110, 170),
    "other":         (23, 28, 34, 48, 68, 105),
}
# Pay multiplier for support functions (ops, control, compliance...) by employer type.
BACK_OFFICE = {"prop_trading": .35, "hedge_fund": .4, "pe_megafund": .35, "pe_midmarket": .55, "bulge_bracket": .45,
               "boutique": .45, "big4": .92, "mid_tier": .92, "asset_manager": .7, "retail_bank": .85,
               "fintech": .85, "other": .95}
# Typical bonus on top of an advertised base salary.
BONUS = {"prop_trading": .8, "hedge_fund": .5, "pe_megafund": .5, "pe_midmarket": .3, "bulge_bracket": .35,
         "boutique": .4, "big4": .05, "mid_tier": .05, "asset_manager": .2, "retail_bank": .1,
         "fintech": .1, "other": .05}
ELITE = {"prop_trading", "hedge_fund", "pe_megafund", "pe_midmarket", "bulge_bracket", "boutique"}
CATEGORY_LABEL = {
    "prop_trading": "Prop trading / market maker", "hedge_fund": "Hedge fund", "pe_megafund": "Private equity (large)",
    "pe_midmarket": "Private equity (mid-market)", "bulge_bracket": "Investment bank", "boutique": "IB boutique / advisory",
    "big4": "Big 4", "mid_tier": "Mid-tier advisory", "asset_manager": "Asset manager / markets infra",
    "retail_bank": "UK bank", "fintech": "Fintech / broker", "other": "Other employer",
}

# ---------------------------------------------------------------- interest areas
TRACKS = [
    ("Transaction services", 1.0, r"transaction services|transactions? advisory|(?<!customer )(?<!enhanced )(?<!client )(?<!vendor )(?<!third party )due diligence|"
                                  r"\bfdd\b|deal advisory|\bdeals?\b(?! desk)|quality of earnings|\btas\b|lead advisory|financial advisory"),
    ("Corporate finance / M&A", 1.0, r"corporate finance|m ?& ?a\b|mergers|acquisitions|corporate development|lead advisory|\becm\b|\bdcm\b|"
                                     r"leveraged finance|lev ?fin|debt advisory|capital markets advisory|financial sponsors|origination"),
    ("Investment banking", 1.0, r"investment bank|\bibd?\b|(banking|advisory|m&a) (analyst|associate)|coverage (analyst|associate|banker)|\bbanker\b"),
    ("Private equity", 1.0, r"private equity|\bpe\b(?![- ]backed)|buy-?out|growth equity|private capital|private markets|infrastructure invest|"
                            r"investment (associate|professional|team|analyst|manager)|direct lending|private credit|venture capital"),
    ("PE portfolio / fund finance", .8, r"portfolio (company|companies|finance|cfo|operations|monitoring)|(pe|private equity)[- ]backed|"
                                        r"fund (accountant|accounting|finance|controller|cfo|reporting)|fund finance|value creation|portco|investor reporting"),
    ("Valuations / restructuring", .4, r"valuations?\b|restructuring|turnaround|insolvency|forensic"),
    ("Finance", .2, r"financ|account|audit|controller|analyst"),
]
TRACKS = [(n, w, re.compile(rx, re.I)) for n, w, rx in TRACKS]
TECH = re.compile(r"engineer|developer|software|devops|\bsre\b|infrastructure|data scien|machine learning|"
                  r"cyber|security|\bit\b|technolog|desktop|help ?desk|service desk|cloud|platform|architect|network|systems|java|python|c\+\+|"
                  r"quant(itative)? (dev|research)|researcher|fpga|hardware|kdb|\bdba\b|database|postgres|\bsql\b|\biam\b|"
                  r"identity (and|&) access|csirt|\bsoc\b|incident response|application support", re.I)
NON_FIN = re.compile(r"\b(hr|human resources|people partner|recruit\w*|talent|front desk|meteorolog\w*|scientist|social media|team assistant|office assistant|legal|counsel|paralegal|marketing|"
                     r"communications|customer experience|branch|cashier|contact centre|account executive|reporter|journalist|editor|lawyer|solicitor|attorney|designer|office manager|receptionist|facilities|executive assistant|"
                     r"personal assistant|administrator|chef|cleaner|driver|nurse|teacher|customer service|"
                     r"call centre|retail assistant|barista|warehouse|hospitality|coffee|food service|catering|concierge|"
                     r"housekeeping|mailroom|interest form|discovery event|chess academy|high school|pact \d{4}|conference|"
                     r"administrative (assistant|support|coordinator)|admin assistant|register your interest|expression of interest|"
                     r"general application|proposal writer|bids? (executive|writer|manager|coordinator)|training specialist|"
                     r"financial guide)\b", re.I)


# Titles that share deal words but aren't deal roles (KYC due diligence, transaction banking, tax, tech M&A integration...).
NOT_DEALS = re.compile(r"\btax\b|\bvat\b|\bkyc\b|\baml\b|onboarding|customer due diligence|client due diligence|\bcdd\b|\bedd\b|"
                       r"transaction (monitoring|banking|reporting|processing|screening)|payments?|cash management|trade finance|"
                       r"operations|\bops\b|settlement|\bsales\b|business development|marketing|technology|\bit\b|cyber|data|"
                       r"software|engineer|integration|transformation|\blegal\b|lawyer|solicitor|paralegal|counsel|actuar|insurance|"
                       r"real estate|property|surveyor|wealth|financial planner|paraplanner|mortgage|lending officer|"
                       r"recruit|talent|\bhr\b|executive assistant|personal assistant|secretary|administrator|coordinator|"
                       r"\bpartner\b|managing director|head of", re.I)
FIN_TITLE = re.compile(r"financial controller|finance manager|head of finance|finance director|\bcfo\b|fp&a|financial analyst|"
                       r"group (accountant|reporting)|finance business partner|reporting (manager|accountant)", re.I)


def interest_of(title, text):
    """(score 0-1, matched track names). Title counts fully; body text is capped."""
    title = title or ""
    if NON_FIN.search(title) or NOT_DEALS.search(title):
        return 0.02, []
    if TECH.search(title) and not re.search(r"\btrader\b|investment bank|private equity|\bdeals?\b", title, re.I):
        return 0.05, ["Technology"]
    hits, best = [], 0.0
    for name, w, rx in TRACKS:
        if rx.search(title):
            hits.append(name)
            best = max(best, w)
    if text:
        for name, w, rx in TRACKS[:6]:
            if name not in hits and len(rx.findall(text)) >= 2:
                hits.append(name)
                best = max(best, min(w, .5))
        # Finance roles in PE-backed companies or PE funds are the "portfolio finance" route.
        if FIN_TITLE.search(title) and re.search(r"(private equity|pe)[- ]backed|portfolio compan|private equity (fund|firm|house)|"
                                                 r"backed by (a |leading )?(private equity|pe)", text, re.I):
            if "PE portfolio / fund finance" not in hits:
                hits.append("PE portfolio / fund finance")
            best = max(best, .7)
    return best, hits


# ---------------------------------------------------------------- seniority & function
def level_of(title, dept=""):
    t = (title or "").lower()
    if re.search(r"\bintern(ship)?s?\b|placement|summer|spring (week|insight)|insight (week|programme|day)|"
                 r"off[- ]cycle|industrial|work experience|year in industry|\bco-?op\b", t):
        return "intern"
    if re.search(r"apprentic|school leaver", t) or dept == "Apprenticeship":
        return "apprentice"
    if re.search(r"managing director|\bmd\b|\bpartner\b|chief|\bhead\b|global head|"
                 r"(?<!associate )(?<!executive )(?<!assistant )director", t):
        return "exec"
    if re.search(r"vice president|\b[as]?vp\b|senior manager|(?<!assistant )manager\b|\blead\b|principal|"
                 r"associate director|executive director|assistant director|team leader", t):
        return "senior"
    if re.search(r"assistant manager|\bavp\b|assistant vice president|\bsenior\b", t):
        return "mid"
    if re.search(r"rotational|\b20\d\d (start|program)|program(me)?:? (january|june|july|august|september|fall|summer) 20\d\d|"
                 r"graduates?|\bgrads?\b|junior|trainee|entry|new grad|campus|\banalyst\b(?!.*senior)|\bassistant\b|\bexecutive\b", t) \
            and not re.search(r"senior|\bassociate\b(?!.*analyst)", t):
        return "entry"
    if re.search(r"analyst ?/ ?associate|associate ?/ ?analyst", t):
        return "entry"
    return "mid"


def function_of(title, dept=""):
    s = f"{title} | {dept}"
    if re.search(r"trade support|operations|\bops\b|settlement|reconcil|compliance|\bkyc\b|\baml\b|onboarding|"
                 r"control(ler)?\b|administrat|coordinator|middle office|back office|fund account|fund services|"
                 r"accountant|\bap\b|payroll|accounts (payable|receivable)|bookkeep|credit control|market data|"
                 r"\bpmo\b|project manag|business manag|reporting", s, re.I):
        return "back"
    front_title = any(rx.search(title or "") for _, _, rx in TRACKS[:5])
    if front_title and not re.search(r"engineer|developer|software|devops|\bsre\b", title or "", re.I):
        return "front"
    if TECH.search(title or ""):
        return "tech"
    if any(rx.search(s) for _, _, rx in TRACKS[:5]):
        return "front"
    return "other"


# ---------------------------------------------------------------- salary parsing
_NUM = r"(\d{1,3}(?:[, \u00a0]\d{3})+(?:[.,]\d{2}(?!\d))?|\d+(?:\.\d+)?)\s?(k\b)?"
_MONEY = {"GBP": re.compile(r"(?:£|\bgbp\s?)\s?" + _NUM, re.I),
          "USD": re.compile(r"(?:\$|\busd\s?)\s?" + _NUM, re.I)}
# A range's second figure often drops the symbol: "$1,000-2,000", "$159-193K", "£30k to 35k".
_RANGE_TAIL = {c: re.compile(r"\s*(?:-|–|—|to)\s*(?:" + sym + r")?\s?" + _NUM, re.I)
               for c, sym in (("GBP", r"£|gbp\s?"), ("USD", r"\$|usd\s?"))}
_PAY_WORDS = re.compile(r"salary|base pay|base compensation|pay range|compensation|annual(ly)?|hiring range|wage|\bpay\b|\bbase\b|"
                        r"hourly rate|day rate", re.I)
_PERIOD_AFTER = [(r"per hour|an hour|/ ?h(ou)?r|hourly|p/?h\b", "hour"), (r"per day|a day|/ ?day|daily|p/?d\b", "day"),
                 (r"per week|a week|/ ?week|weekly|p/?w\b", "week"), (r"per month|a month|/ ?month|monthly|pcm", "month")]
# "weekly base salary range $3,500-5,700", "an hourly rate of $36-37": the period word sits a few words before the figure.
_PERIOD_BEFORE = re.compile(r"\b(hourly|weekly|monthly|daily)\b(?:\W+\w+){0,4}\W*$", re.I)


def _amount(num, k):
    num = re.sub(r"[ \u00a0]", ",", num)
    num = re.sub(r",(\d{2})$", r".\1", num)  # "76,560,00" (European cents) -> "76,560.00"
    v = float(num.replace(",", ""))
    return v * 1000 if k else v


def find_pay_text(desc, currency):
    """US adverts often put the legally required pay range near the end: find it anywhere."""
    for m in _MONEY[currency].finditer(desc or ""):
        if _PAY_WORDS.search(desc[max(0, m.start() - 160):m.start()]):
            return desc[max(0, m.start() - 60):m.start() + 90]
    return ""


def parse_salary(text, currency="GBP"):
    """Return (min, max) annual pay in the advert's currency from text such as
    '£45,000 - £55,000 a year', '£500 a week', '$150,000 - $200,000' or '$159-193K'."""
    if not text:
        return None, None
    text = re.sub(r"(\d) ?(\d{0,2}) ,?(\d{3})\b", lambda g: g.group(0) if " " not in g.group(0) else
                  (g.group(1) + g.group(2) + "," + g.group(3) if "," in g.group(0) else g.group(0)), text)  # "$15 0 ,000" -> "$150,000"
    vals, used = [], 0
    for m in list(_MONEY[currency].finditer(text))[:4]:
        if m.start() < used:
            continue  # second half of a range already read
        if re.match(r",\d", text[m.end():m.end() + 2]):
            continue  # malformed figure such as "$200,00"
        if re.match(r"\s?(m|mn|bn|million|billion|trillion|%)(\b|\+)", text[m.end():m.end() + 9], re.I):
            continue  # "$250bn a day", "£500m fund", "£1m+" are not pay
        figs = [(m.group(1), m.group(2))]
        end = m.end()
        tail = _RANGE_TAIL[currency].match(text, end)
        if tail and not _MONEY[currency].match(text, end):
            figs.append((tail.group(1), tail.group(2)))
            end = tail.end()
        nums = [_amount(n, k) for n, k in figs]
        used = end
        if len(nums) == 2 and figs[1][1] and not figs[0][1] and nums[0] < 1000:
            nums[0] *= 1000  # "$159-193K": the K covers both figures
        if len(nums) == 2 and figs[0][1] and not figs[1][1] and nums[1] < 1000:
            nums[1] *= 1000  # "$192K - $234"
        after = text[end: end + 25].lower()
        period = next((p for rx, p in _PERIOD_AFTER if re.match(r"^\W*(?:usd|gbp)?\W*(?:" + rx + ")", after)), None)
        if not period:
            before = _PERIOD_BEFORE.search(text[max(0, m.start() - 60):m.start()])
            period = {"hourly": "hour", "weekly": "week", "monthly": "month", "daily": "day"}[before.group(1).lower()] if before else None
        if not period and all(10 <= v <= 300 for v in nums) and _PAY_WORDS.search(text[max(0, m.start() - 80):m.start()]):
            period = "hour"  # "$24.00 - $33.50 USD" in a US pay-transparency line is an hourly rate
        mult = {"hour": 2080 if currency == "USD" else 1950, "day": 230, "week": 52, "month": 12}.get(period, 1)
        vals += [v * mult for v in nums if 8_000 <= v * mult <= 1_500_000]
        if len(vals) >= 2:
            break
    if not vals:
        return None, None
    vals = vals[:2]
    return min(vals), max(vals)


# ---------------------------------------------------------------- employer classification
def classify(company, aliases):
    c = f" {(company or '').lower()} "
    for cat, names in aliases.items():
        if cat.startswith("_"):
            continue
        for n in names:
            if re.search(r"(?<![a-z0-9])" + re.escape(n.strip()) + r"(?![a-z0-9])", c):
                return cat
    return "other"


# ---------------------------------------------------------------- work-from-home
def workplace_of(job):
    if job.get("workplace"):
        w = job["workplace"].lower()
        if "remote" in w:
            return "remote"
        if "hybrid" in w:
            return "hybrid"
        if "site" in w or "office" in w:
            return "office"
    s = " ".join([job.get("title", ""), job.get("location", ""), job.get("description", "")]).lower()
    if re.search(r"fully remote|remote[- ]first|100% remote|work from home|home[- ]based|remote \(uk\)|uk remote|"
                 r"remote working|\bremote\b", s):
        if re.search(r"hybrid|days? (a|per) week in (the )?office|in the office \d", s):
            return "hybrid"
        return "remote"
    if re.search(r"hybrid|flexible working|agile working|days? (a|per) week in (the )?office|work from home \d", s):
        return "hybrid"
    if re.search(r"office[- ]based|on[- ]site|onsite|5 days (a|per) week in|fully in[- ]office", s):
        return "office"
    return "unknown"


# ---------------------------------------------------------------- requirements vs this candidate
_WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_N = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)"
_YEARS = re.compile(r"\b" + _N + r"\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*" + _N + r"\s*)?\+?\s*(?:or more\s+)?(?:years?|yrs)\b", re.I)
_EXP_AFTER = re.compile(r"^[’'s\s]*(?:\+\s*)?(?:of\s+)?(?:(?:relevant|professional|proven|practical|hands-on|demonstrable|"
                        r"previous|prior|industry|work|working|post[- ]?qualifi\w*|pqe)\s+)*"
                        r"(?:experience|exp\b|in\b|within\b|at\b|as\b|working|pqe|post[- ]?qual)"
                        r"|^[’'s\s]*(?:\+\s*)?of\s+(?:[\w,/&()-]+\s+){0,8}?(?:experience|exp\b)", re.I)
_EXP_BEFORE = re.compile(r"(minimum of|at least|experience of|experience:|requires?|you have|you'll have|with)\s*$", re.I)
_NOT_REQ = re.compile(r"\b(we|we've|our|firm|company|founded|history|over the (past|last)|for over|ago|age|aged|"
                      r"next|every|each|term|contract|fixed)\b[^.]{0,25}$", re.I)
# Experience where two years of audit count in full.
_RELEVANT_EXP = re.compile(r"audit|accountan|accounting|assurance|financial (reporting|statements|control|accounting)|"
                           r"finance (function|team)|professional services|big ?(4|four)|practice|controls? testing|"
                           r"reconcil|regulatory reporting|statutory|qualified|pqe|post[- ]?qual|\bfinance\b|"
                           r"quantitative or technical|analytical|professional experience|relevant experience|"
                           r"work experience|related (role|field|experience)", re.I)
# Experience audit only partly stands in for (operations, risk, control-type work).
_NEAR_EXP = re.compile(r"client services|settlement|middle office|back office|operations|\bops\b|risk|compliance|\baml\b|"
                       r"\bkyc\b|product control|treasury|fund admin|fund account|valuation|due diligence|transaction services|"
                       r"credit|insurance|tax\b|lending|wealth|data\b|reporting|modelling|fp&a|business analys", re.I)
# Experience audit doesn't give at all.
_FAR_EXP = re.compile(r"trad(e|er|ers|ing)\b|forecast|software|engineer|develop(er|ment)|sales|portfolio manag|"
                      r"investment bank|m ?& ?a\b|mergers|corporate finance|private equity|principal invest|\bdeals?\b|"
                      r"leveraged finance|capital markets|quant|research|legal|marketing|recruit|python|coding|"
                      r"programming|energy|commodit|fixed income|derivativ|equities|actuar|buy[- ]side|hedge fund|"
                      r"asset management|investing|investment (team|analyst|experience)", re.I)


def years_required(low):
    """Every experience requirement in the advert: [(years, post-qualification?, context, credit)] where
    credit is how much of the candidate's audit experience counts (1, .5 or 0)."""
    out = []
    for m in _YEARS.finditer(low):
        n = m.group(1)
        n = int(n) if n.isdigit() else _WORDNUM[n]
        pre, post = low[max(0, m.start() - 60):m.start()], low[m.end():m.end() + 140]
        if n == 0 or n > 15 or _NOT_REQ.search(pre[-40:]):
            continue
        if not (_EXP_AFTER.search(post) or (_EXP_BEFORE.search(pre) and "experience" in post[:90])):
            continue
        ctx = re.split(r"[.;•·]", post)[0][:110].strip(" '+s")
        ctx = re.sub(r"^(of\s+)?((relevant|professional|proven|work|working|industry)\s+)*(experience\s+)?"
                     r"((in|of|with|within|across)\s+)?", "", ctx)
        ctx = re.split(r"\s(?:and|with|including|plus)\s(?:at least|a minimum|minimum|strong|excellent|proven)\b", ctx)[0]
        pqe = bool(re.search(r"pqe|post[- ]?qualif|since qualif|qualified experience", pre[-30:] + post[:60]))
        credit = _credit(ctx)
        out.append((n, pqe, ctx, credit))
    return out


# "Skills you'll need: experience in a trading operations role" - specific experience with no years given.
_NEEDS_EXP = re.compile(r"(?:(you have|you'll have|you will have|you'll need|you need|you must have|must have|required|requirements|"
                        r"essential|skills and experience|what you need|what you'll bring|you bring|you'll bring|ideal candidate)"
                        r"\W{0,4}(?:significant |proven |strong |solid |demonstrable |relevant |prior |previous |direct |hands-on )*"
                        r"|\b(?:previous|prior|proven|demonstrable|direct|hands-on|solid|strong|significant|extensive|substantial|deep|relevant) )"
                        r"(?:[\w-]+ ){0,3}?experience (?:(?:gained|acquired|built|working) )?(?:in|of|with|within|across|at)\s+([^.;•]{0,90})", re.I)
# Roles that need an existing client book, deal leadership or people management.
_BOOK = re.compile(r"book of business|portfolio of clients|client book|established (network|relationships|client)|"
                   r"deep (industry|client) relationships|lead coverage|assume (lead )?coverage|track record of (generating|originating|winning|"
                   r"bringing in)|originat\w* (new )?(business|clients|mandates)", re.I)
_LEADS = re.compile(r"track record of leading|managing junior|manage junior|leading (live )?(deals|transactions)|lead(ing)? bond transactions|"
                    r"line management|people management experience|managing (a|the) team of|experience (of |in )?managing (a )?team", re.I)

# Coding. The candidate can't write code yet, so a hard Python/SQL requirement is a big gap at either stage.
_CODE = re.compile(r"\b(python|sql|vba|c\+\+|c#|java|javascript|kdb\+?|powershell|programming languages?|coding|scripting)(?![\w+#])", re.I)
_CODE_SOFT = re.compile(r"\b(a plus|plus\b|desirable|advantag\w*|nice to have|we'd love|bonus|prefer\w*|willing to learn|basic|"
                        r"ideally|beneficial|exposure|would be|helpful|a benefit|interest\w*|keen to|appetite|not required|"
                        r"not essential|or similar tools|curious|great fit|might be a|could be a)\b", re.I)


def coding_need(low):
    """'hard' if the advert needs real coding, 'soft' if it's only a plus, else None."""
    found = None
    for m in _CODE.finditer(low):
        a = max(0, low.rfind(".", 0, m.start()), low.rfind("•", 0, m.start()), m.start() - 250)
        b = min([x for x in (low.find(".", m.end()), low.find("•", m.end())) if x != -1] + [m.end() + 160])
        if _CODE_SOFT.search(low[a:b]):
            found = found or "soft"
        else:
            return "hard", m.group(1)
    return (found, None) if found else (None, None)


def _credit(ctx):
    """How much audit experience counts towards experience described by ctx: 1, .5 or 0."""
    if re.search(r"audit|accountan|accounting|assurance|financial (reporting|statements|control)|big ?(4|four)|"
                 r"reconcil|quantitative or technical", ctx):
        return 1
    related = re.search(r"related (role|field|area|discipline)|similar (role|field)", ctx)
    if _FAR_EXP.search(ctx):
        return .5 if related else 0
    if _NEAR_EXP.search(ctx):
        return .75 if related else .5
    if not ctx or related or _GENERIC_EXP.match(ctx):
        return 1
    return .5  # experience in some other named field (consulting, corporate actions...): audit only partly stands in


_GENERIC_EXP = re.compile(r"^((is |are )?(preferred|required|desirable|essential|needed|ideal)|would|will|or more|experience\b|"
                          r"professional|relevant|work|working|industry|full[- ]time|post|of\b|and\b|"
                          r"(in|within|at) (a|an) (professional|similar|relevant|fast|busy|office|corporate|client|large|global|team)|"
                          r"a (professional|corporate|similar|relevant|business))", re.I)


_LANGS = (r"japanese|mandarin|cantonese|chinese|french|german|spanish|portuguese|italian|arabic|korean|russian|dutch|"
          r"hindi|turkish|polish|hebrew|swedish|norwegian|danish|greek")


def _soft_years(ctx):
    return bool(re.search(r"preferred|not required|desirable|a plus", ctx or ""))


def _short(t, n=60):
    t = t.strip(" ,")
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(" ,") + "…"


def _gap_factor(gap):
    if gap <= 0:
        return 1.0
    return .6 if gap <= 1 else .3 if gap <= 2 else .15 if gap <= 3 else .07


_SOFT = re.compile(r"^[^.]{0,40}\b(preferred|preferable|desirable|advantage|advantageous|a plus|nice to have|bonus|beneficial)\b", re.I)
_SOFT_BEFORE = re.compile(r"\b(ideally|preferably|desirable|nice to have|bonus|plus)\b[^.]{0,30}$", re.I)
_ADV_DEGREE = re.compile(r"\b(master'?s(?! (of|in) (none|excel))|msc|m\.sc|mba|ph\.?d|doctorate|doctoral|advanced degree|"
                         r"postgraduate (degree|qualification))\b", re.I)
_DEGREE = re.compile(r"\bbachelor|degree or equivalent|(undergraduate|university|third[- ]level|3rd[- ]level|college) degree|degree[- ](level|educated)|"
                     r"educated to degree|tertiary (qualification|degree|education)|\b2[:.]1\b|degree (is )?(required|essential)|hold a degree|have a degree|"
                     r"(a|relevant|strong) degree in|\bbsc\b|\bb\.?a\.? in\b|\bbs\b (in|degree)|degree in (finance|economics|"
                     r"accounting|business|math)", re.I)
_STEM_DEGREE = re.compile(r"degree[^.]{0,30}?\b(in|of)\b([^.]{0,90})", re.I)
_STEM = re.compile(r"meteorolog|atmospheric|physics|mathemat|\bmaths\b|computer science|engineering|statistics|chemistry|"
                   r"biology|\blaw\b|medicine|data science|machine learning|actuarial science", re.I)
_FIN_SUBJ = re.compile(r"financ|account|econom|business", re.I)
_NO_DEGREE = re.compile(r"(don'?t|do not|doesn'?t|does not) (need|require|have to have) a degree|with or without a degree|"
                        r"degree (is )?not (required|necessary|essential|needed)|no degree (required|needed|necessary)|"
                        r"regardless of (your )?degree", re.I)
# Specialist qualifications the candidate doesn't hold (AAT/ACA don't cover them).
_OTHER_QUAL = re.compile(r"\b(m?rics)\b|chartered surveyor|qualified (real estate )?valu\w* professional|statement of professional standing|"
                         r"\bdippfs\b|diploma in (regulated )?financial planning|chartered financial planner|"
                         r"qualified financial (adviser|advisor|planner)|\bcta[- ]qualified|qualified cta\b|\batt[- ]qualified|"
                         r"cfa charter ?holder", re.I)
_OTHER_QUAL_NAME = [("rics", "RICS (chartered surveyor)"), ("surveyor", "RICS (chartered surveyor)"),
                    ("valu", "a property-valuation (RICS) qualification"), ("professional standing", "a regulated financial-adviser qualification"),
                    ("financial planning", "a regulated financial-adviser qualification"), ("dippfs", "a regulated financial-adviser qualification"),
                    ("planner", "a regulated financial-adviser qualification"), ("adviser", "a regulated financial-adviser qualification"),
                    ("advisor", "a regulated financial-adviser qualification"), ("cta", "a tax qualification (CTA)"),
                    ("att", "a tax qualification (ATT)"), ("cfa", "the CFA charter")]
_QUALIFIED = re.compile(r"newly[- ]qualified|\bnq\b|fully[- ]qualified|qualified \(?(aca|acca|cima|cpa|accountant|chartered|auditors?|"
                        r"(audit|assurance) (or (audit|assurance) )?professional)|"
                        r"\b(aca|acca|cima|cpa|icaew)\b[^.]{0,30}?\bqualified\b|chartered accountan(t|cy)|post[- ]qualification|"
                        r"\bpqe\b|qualified accountant|(accountancy|accounting) qualification( or equivalent)?( is)? (required|essential)|"
                        r"(aca|acca|cima|cpa)( or (aca|acca|cima|cpa|equivalent))*,? (is )?(required|essential)|"
                        r"must be (aca|acca|a qualified|a chartered)|professionally qualified", re.I)
_PART_QUALIFIED = re.compile(r"part[- ]qualified|studying (towards|for)|working towards|qualified or (part|studying|nearly)|"
                             r"\bqbe\b|qualified by experience|nearly qualified|finalist", re.I)


# ---------------------------------------------------------------- what the role is (advert's own words)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])|\s*[•·▪●]\s*|\n+")
_ROLE_RX = [re.compile(rx, re.I) for rx in (
    r"\b(we (require|need|are looking for|are seeking|are hiring|seek|are recruiting)|we're (looking for|seeking|hiring|recruiting)|"
    r"(is|are) (looking|seeking|hiring) (for )?(an?|the) )",
    r"\bin this role,? you\b|\bas (an?|the|our) [^,.]{3,70}, you('ll| will)\b|"
    r"\byou (will|'ll) (be responsible|be joining|join|work|support|lead|help|own|manage|provide|play|sit|report|be working)",
    r"\b(this|the) (role|position|opportunity|job) (is|will|involves|sits|offers|focuses|requires|supports|reports)\b",
    r"\b(role|position|job) (overview|summary|purpose|description)\b|\bpurpose of the role\b|\babout the (role|job|position)\b|"
    r"\bthe opportunity\b|\bwhat you('ll| will) (do|be doing)\b|\byour role\b|\bresponsibilities\b",
)]
_HEADER = re.compile(r"^(job description|description|job summary|overview|about the (role|job|position)|the role|role overview|"
                     r"purpose of the role|position summary|role summary|the opportunity|your role|what you('ll| will) (do|be doing)|"
                     r"responsibilities|key responsibilities)\s*[:\-–]?\s*", re.I)
_BOILER = re.compile(r"\b(founded|is a leading|is one of the|equal opportunit|headquartered|our (mission|culture|values|people)|"
                     r"we are (a|an|the|one)|we're (a|an|the|one)|award[- ]winning|diversity|inclusion|privacy|cookies|"
                     r"benefits|recruitment agenc|reasonable adjustment|salary|compensation|pay range|start date|timelines?|"
                     r"exciting opportunity|highly motivated|apply now|closing date)\b|[$£]\s?\d", re.I)


def _clip(t, n):
    t = t.strip(" -–:;,")
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"


_STOP = {"and", "the", "of", "for", "to", "in", "a", "an", "&", "-", "–", "with", "on", "at", "or", "uk", "london", "new",
         "york", "senior", "junior", "associate", "analyst", "manager", "assistant", "vice", "president", "vp", "avp",
         "director", "lead", "head", "officer", "specialist", "team", "role", "2025", "2026", "2027", "programme", "program"}
_BOILER2 = re.compile(r"if you are looking for|if you're looking for|our roles generate|working with us|close (for )?applications|"
                      r"place for you|build a future|make an impact|true self|individuality|why join|life at|join us\b|"
                      r"great place to work|we offer|we provide|you('ll| will) (enjoy|receive|get)|hybrid working|flexible working|"
                      r"\d[\d,]* (people|employees|colleagues)|countries|years of (history|heritage)|our clients include", re.I)


def _boiler(x, title_low=""):
    """Company blurb / pay / HR wording - unless the word is the job's own subject (a Compensation Analyst's advert says "compensation")."""
    if _BOILER2.search(x):
        return True
    return any(m.group(0).lower() not in title_low for m in _BOILER.finditer(x))


def role_summary(desc, title="", n=210):
    """The advert's own sentence(s) on what the job is; '' if the advert text is too short to tell.
    Picks the early sentence that best describes the job: role wording ("you will", "we are looking for")
    and the title's own words count for it, company blurb counts against it."""
    if not desc or len(desc) < 120:
        return ""
    tl = (title or "").lower()
    words = {w for w in re.findall(r"[a-z&]+", tl) if w not in _STOP and len(w) > 2}
    sents = [x.strip() for x in _SENT_SPLIT.split(desc[:9000]) if x and len(x.strip()) > 25][:45]
    best, best_score = None, 0
    for i, x in enumerate(sents):
        body = _HEADER.sub("", x)
        if not 40 <= len(body) <= 600 or _boiler(x, tl):
            continue
        sc = sum(3 - k * .5 for k, rx in enumerate(_ROLE_RX) if rx.search(x))
        sc += 1.5 * min(3, sum(1 for w in words if re.search(r"\b" + re.escape(w), x.lower())))
        sc -= i * .04  # earlier is better
        if sc > best_score:
            best, best_score = i, sc
    if best is None:
        best = next((i for i, x in enumerate(sents) if len(x) >= 50 and not _boiler(x, tl)), None)
    if best is None:
        return ""
    out = _HEADER.sub("", sents[best])
    out = re.sub(r"^(purpose of the role|about the role|the role)\s+", "", out, flags=re.I)
    nxt = sents[best + 1] if best + 1 < len(sents) else ""
    if len(out) < 120 and nxt and not _boiler(nxt, tl):
        out = out.rstrip(".") + ". " + _HEADER.sub("", nxt)
    out = out[0].upper() + out[1:] if out else out
    return _clip(out, n)


def _sentence(low, start, end, before=220, after=160):
    """The sentence or bullet around low[start:end]."""
    a = max(low.rfind(". ", max(0, start - before), start), low.rfind("•", max(0, start - before), start),
            low.rfind("\n", max(0, start - before), start), start - before, 0)
    nxt = [x for x in (low.find(". ", end), low.find("•", end), low.find("\n", end)) if x != -1]
    b = min(nxt + [end + after])
    return low[a:b]


# ---------------------------------------------------------------- specialist systems the candidate hasn't used
SYSTEMS = [(n, re.compile(rx, re.I)) for n, rx in (
    ("Oracle", r"\boracle\b(?! (corporation|park|arena))|\bebs r12\b|\botbi\b"),
    ("SAP", r"\bsap\b|s/?4 ?hana"),
    ("Workday Financials", r"workday (financials|adaptive|prism|accounting)|adaptive insights"),
    ("Hyperion/HFM", r"hyperion|\bhfm\b|essbase"),
    ("OneStream", r"onestream"), ("BlackLine", r"blackline"), ("Anaplan", r"anaplan"), ("NetSuite", r"netsuite"),
    ("Coupa", r"\bcoupa\b"), ("Tagetik", r"tagetik"), ("Workiva", r"workiva"), ("Kyriba", r"kyriba"),
    ("Murex", r"\bmurex\b"), ("Calypso", r"\bcalypso\b"), ("Aladdin", r"\baladdin\b"), ("SimCorp", r"simcorp"),
    ("Advent Geneva", r"advent geneva|\bgeneva\b(?=[^.]{0,25}(system|platform|accounting))"),
    ("Investran", r"investran"), ("eFront", r"\befront\b"), ("Allvue", r"allvue"), ("Yardi", r"\byardi\b"),
    ("Charles River", r"charles river (ims|development)"), ("Temenos", r"temenos"),
    ("AxiomSL", r"axiom ?sl\b|axiom (cv|controllerview)"),
    ("Microsoft Dynamics", r"dynamics 365|\bd365\b|navision|business central"), ("Salesforce", r"salesforce"),
)]
_SYS_REQ = re.compile(r"experience|expertise|knowledge|proficien|hands[- ]on|skilled|specialist|expert|implement|configur|"
                      r"functional|consultant|certif|background|familiar|working with|track record|understanding", re.I)
_SYS_DEEP = re.compile(r"\b(deep|extensive|expert|in-depth|advanced|strong|proven|significant|hands[- ]on|certified|\d+\+? ?years?)\b", re.I)
_SYS_GENERIC = re.compile(r"such as|e\.g|\beg\b|for example|or similar|or equivalent|or other|any (major )?erp|\blike\b|i\.e", re.I)
_SYS_SOFT = re.compile(r"\b(a plus|plus\b|desirable|advantag\w*|nice to have|bonus|prefer\w*|ideally|beneficial|exposure|"
                       r"helpful|a benefit|not (required|essential)|highly valued|valued)\b", re.I)
_SYS_RANK = {"title": 0, "deep": 1, "req": 2, "generic": 3, "soft": 4}
_SYS_MULT = {"title": .25, "deep": .4, "req": .55, "generic": .85, "soft": .95}


def systems_need(title, low, known=()):
    """(kind, [system names]) for the hardest specialist-system demand in the advert, or (None, [])."""
    known = {k.lower() for k in known}
    hits = []
    for name, rx in SYSTEMS:
        if name.lower() in known:
            continue
        if rx.search(title or ""):
            hits.append(("title", name))
            continue
        for m in rx.finditer(low):
            sent = _sentence(low, m.start(), m.end())
            if _SYS_GENERIC.search(sent):
                kind = "generic"
            elif _SYS_SOFT.search(sent):
                kind = "soft"
            elif _SYS_REQ.search(sent):
                kind = "deep" if _SYS_DEEP.search(sent) else "req"
            else:
                continue
            hits.append((kind, name))
            break
    if not hits:
        return None, []
    worst = min(hits, key=lambda h: _SYS_RANK[h[0]])[0]
    return worst, [n for k, n in hits if k == worst][:3]


# ---------------------------------------------------------------- what in the advert plays to an audit background
_ASKS = re.compile(r"experience|background|knowledge|understanding|exposure|familiar|skills?\b|you (have|bring|will have|'ll have|'ll bring)|"
                   r"candidate|ideally|essential|required|requirements|preferred|desirable|qualifi|track record|proficien|"
                   r"demonstrat|grounding|expertise|comfortable", re.I)
# Where the advert's requirements start; strengths found after this count without a sentence check.
_REQ_HEAD = re.compile(r"essential (skills|criteria|requirements)|you must have|requirements:|what you('ll| will)? need|what we('re| are) looking for|"
                       r"skills (and|&) experience|experience (and|&) skills|qualifications:|about you|to be successful|"
                       r"the ideal candidate|who you are|what you('ll| will)? bring|you will have|you('ll| will) need|your (skills|experience|profile)|"
                       r"basic qualifications|preferred qualifications|minimum qualifications|requirements of the role|key requirements|"
                       r"candidate profile|person specification", re.I)
_STRENGTH_SKIP = re.compile(r"may be assessed|critical skills relevant|all colleagues will be expected", re.I)
STRENGTHS = [(k, re.compile(rx, re.I)) for k, rx in (
    ("audit", r"\b(audit(ing)? (experience|background|firm|practice|requirements|skills)|external audit|statutory audit|"
              r"big ?(4|four)|(audit|assurance) (and|&) (assurance|advisory)|assurance|(?<!internal )audit(?! (committee|evidence|trail|log)))\b"),
    ("reporting", r"financial (reporting|statements|accounts)|statutory (accounts|reporting)|\bifrs\b|\b(uk |us )?gaap\b|"
                  r"(year|period|month|quarter)[- ]end( close| reporting| processes)?|financial close"),
    ("controls", r"\bsox\b|sarbanes|internal controls?|controls? testing|control (framework|environment)|risk and controls?"),
    ("recs", r"reconciliations?|balance sheet (review|substantiation|reconciliation)"),
    ("accounting", r"accounting (background|knowledge|experience|principles|standards|skills)|accountancy|\baccounting\b"),
    ("diligence", r"due diligence|transaction services|financial diligence|\bfdd\b|quality of earnings"),
    ("excel", r"\bexcel\b"),
)]


def strengths_in(low):
    """{key: matched phrase} for audit-relevant things the advert asks for (in a requirement sentence)."""
    out = {}
    head = _REQ_HEAD.search(low)
    for key, rx in STRENGTHS:
        for m in rx.finditer(low):
            sent = _sentence(low, m.start(), m.end())
            if _STRENGTH_SKIP.search(sent):
                continue
            if (head and m.start() > head.start()) or (not head and _ASKS.search(sent)):
                out[key] = m.group(0).strip()
                break
    return out


def _soft(low, m):
    return bool(_SOFT.search(low[m.end():m.end() + 70]) or _SOFT_BEFORE.search(low[max(0, m.start() - 40):m.start()]))


# ---------------------------------------------------------------- deal experience: required, desirable or open to audit
DEAL_RX = re.compile(r"transaction services|transactions? advisory|transactions? (experience|background|work|execution|exposure)|"
                     r"(?<!customer )(?<!enhanced )(?<!client )(?<!vendor )(?<!supplier )(?<!kyc )(?<!third party )(?<!third-party )"
                     r"(?:financial )?due diligence|\bfdd\b|\bts\b|\btas\b|m ?& ?a\b|mergers|acquisitions|corporate finance|lead advisory|"
                     r"deal advisory|\bdeals?\b|investment banking|\bibd?\b|private equity|leveraged finance|buy[- ]side|sell[- ]side|"
                     r"corporate development|capital markets|\becm\b|\bdcm\b|valuations?\b|transactional|transactions\b", re.I)
_EXP_WORD = re.compile(r"experience|experienced|background|track record|worked (on|in|within|across)|working (on|in|within|across)|"
                       r"exposure|history of|from an? |currently (in|working|within|based in)|time (in|spent)|"
                       r"years? (in|of|within)|having (worked|completed|executed|delivered|led)|executed|led|leading|deal list", re.I)
_LEARN = re.compile(r"you('ll| will) (gain|get|develop|build|be exposed|learn|have the (chance|opportunity)|work|support|assist|be working|"
                    r"be involved|be part|join|help)|opportunit(y|ies) to|gain (exposure|experience)|develop (your|their)|"
                    r"exposure to (a )?(wide|broad|varied|range|variety|diverse)|we (offer|provide|will|are|have)|"
                    r"\bour (team|experience|track record|clients|practice|firm)|(firm|team|group|practice)('s)? (has|have|is)|"
                    r"has (a |an )?(strong |proven |excellent |enviable )?track record|training|career (development|progression)|"
                    r"responsibilities|you('ll| will) be responsible", re.I)
_SOFT_DEAL = re.compile(r"desirable|preferred|preferable|advantage|advantageous|a plus|nice to have|bonus|beneficial|ideally|"
                        r"would be (great|good|helpful|useful|welcome|valued|an asset|ideal)|helpful|welcomed?|valued|an asset|"
                        r"not (essential|required|necessary|mandatory)|useful|but not required|is a plus|considered", re.I)
_AUD = r"(audit|assurance|accountancy|accounting|financial reporting)"
_DEALW = (r"(transaction services|transactions?|due diligence|fdd|\bts\b|deals?|deal advisory|m ?& ?a|corporate finance|"
          r"valuations?|restructuring|advisory)")
# "Big 4 audit or transaction services experience": audit offered as the alternative to deal experience.
_AUDIT_OR_DEAL = re.compile(r"\b" + _AUD + r"\b(?:\W+\w+){0,4}?\W*(?:\bor\b|/|and/or)\W*(?:\w+\W+){0,4}?" + _DEALW +
                            r"|" + _DEALW + r"(?:\W+\w+){0,4}?\W*(?:\bor\b|/|and/or)\W*(?:\w+\W+){0,4}?\b" + _AUD + r"\b", re.I)
_OPEN = re.compile(r"(no|without) (prior |previous |any )?(deal|transaction|m&a|ts|due diligence|corporate finance) experience|"
                   r"(deal|transaction|m&a|due diligence|corporate finance) experience (is )?not (required|essential|necessary)|"
                   r"(mov(e|ing)|transition(ing)?|step(ping)?|switch(ing)?) (from|out of) (an? )?(audit|assurance)|"
                   r"(audit|assurance) (to|into) (ts|transaction|deals|due diligence|corporate finance|advisory)|"
                   r"from (an? )?(audit|assurance) background|(audit|assurance) (professionals|backgrounds?|candidates)|"
                   r"(audit|assurance) or (ts|transaction|deals|due diligence|fdd|corporate finance)|"
                   r"(ts|transaction services|due diligence|fdd|deals) or (big ?(4|four) )?(audit|assurance)", re.I)


def deal_experience(low, head=None):
    """('required' | 'desirable' | 'open' | None, quoted phrase) - what the advert says about previous deal experience."""
    found = {}
    for m in DEAL_RX.finditer(low):
        sent = _sentence(low, m.start(), m.end(), before=170, after=150)
        if not _EXP_WORD.search(sent):
            continue
        strong = re.search(r"\b(must|essential|required|requirement|mandatory|need(ed)?|proven|demonstrable|\d+\+? ?(years?|yrs))\b", sent)
        if _OPEN.search(sent) or _AUDIT_OR_DEAL.search(sent):
            kind = "open"
        elif _LEARN.search(sent) and not strong:
            continue
        elif head is not None and m.start() < head and not strong:
            continue  # described in the job's own work, not asked of the candidate
        elif _SOFT_DEAL.search(sent):
            kind = "desirable"
        else:
            kind = "required"
        found.setdefault(kind, sent.strip(" .•,;:-"))
    if _OPEN.search(low) and "open" not in found:
        x = _OPEN.search(low)
        found["open"] = _sentence(low, x.start(), x.end(), 120, 100).strip(" .•,;:-")
    for kind in ("open", "required", "desirable"):
        if kind in found:
            return kind, found[kind], found
    return None, "", found


_MODEL = re.compile(r"(financial|lbo|three[- ]statement|3[- ]statement|integrated|valuation|dcf) model(l)?ing|modell?ing (skills|experience|ability)|"
                    r"build(ing)? (financial )?models", re.I)
_TWO_ONE = re.compile(r"\b2[:.]1\b|upper second", re.I)


def eligibility(job, level, profile):
    """(reach, flags, pros, deal status, deal quote) for this candidate: ACA-qualified auditor, Assistant Manager,
    about five years in audit, degree, no deal experience yet."""
    years = float(profile.get("experience_years", 5))
    pqe = float(profile.get("pqe_years", 2))
    text = " ".join([job.get("title", ""), job.get("description", "")])
    low = text.lower().replace("’", "'")
    title = (job.get("title") or "").lower()
    flags, pros, m = [], [], 1.0
    base = {"apprentice": .02, "intern": .03, "entry": .5, "mid": .62, "senior": .35, "exec": .03}[level]
    advert_read = len(job.get("description") or "") >= 300

    if level in ("intern", "apprentice") or re.search(r"\b(intern(ship)?|placement|summer|spring week|insight|off[- ]cycle|apprentic\w*)\b", title):
        m *= .2
        flags.append("Internship / apprenticeship - not for a qualified Assistant Manager")
    if re.search(r"currently (studying|enrolled)|penultimate year|final[- ]year (student|undergrad)|graduating in 20\d\d|"
                 r"expected graduation|recent graduates?|class of 20\d\d|(in|of) your (final|penultimate) year", low):
        m *= .2
        flags.append("Student / recent-graduate only")
    elif level == "entry" and re.search(r"\bgraduates?\b|\bgrad\b|\bcampus\b|\b20\d\d (start|intake|programme|program)\b", title):
        m *= .35
        flags.append("Graduate programme - you'd restart at graduate grade and pay")

    # Previous deal experience: the deciding rule for this list.
    head = _REQ_HEAD.search(low) if advert_read else None
    status, quote, _ = deal_experience(low, head.start() if head else None) if advert_read else (None, "", {})
    if status == "required":
        m *= .12
        flags.append(f'Requires previous deal experience ("{_short(quote, 90)}")')
    elif status == "desirable":
        m *= .95
        flags.append(f'Deal experience is a plus, not required ("{_short(quote, 80)}")')
    elif status == "open":
        m *= 1.2
        pros.append(f'Open to audit backgrounds ("{_short(quote, 80)}")')

    # Years of experience: audit years count in full for general experience; deal-specific years are the rule above.
    reqs = years_required(low) if advert_read else []
    worst = None
    for n, is_pqe, ctx, credit in reqs:
        if DEAL_RX.search(ctx) or _soft_years(ctx):
            continue
        have = pqe if is_pqe else years * max(credit, .5)
        f = _gap_factor(n - have)
        if f < 1 and (worst is None or f < worst[0]):
            worst = (f, n, is_pqe, ctx)
    if worst:
        f, n, is_pqe, ctx = worst
        m *= f
        what = f"{n}+ years post-qualification" if is_pqe else f"{n}+ years' experience"
        have = f"you have about {pqe:g} PQE" if is_pqe else f"you have {years:g}"
        flags.append(f"Asks for {what}" + (f" ({_short(ctx)})" if ctx and not is_pqe else "") + f" - {have}")
    else:
        met = [(n, ctx) for n, is_pqe, ctx, credit in reqs if not DEAL_RX.search(ctx) and (pqe if is_pqe else years) >= n]
        if met:
            n, ctx = max(met)
            pros.append(f"Asks for {n}+ yrs" + (f" ({_short(ctx, 45)})" if ctx else "") + f" - you have {years:g}")

    if advert_read:
        if _BOOK.search(low):
            m *= .3
            flags.append("Wants an established client book / origination record")
        if re.search(r"line management|people management|managing (a |the )?team|manage junior|managing junior|supervis\w+ (junior|team)", low):
            pros.append("Wants people management - you run audit teams as an Assistant Manager")
        mod = _MODEL.search(low)
        if mod:
            if _soft(low, mod):
                flags.append("Financial modelling is a plus - worth a modelling course")
            else:
                m *= .8
                flags.append("Wants financial modelling skills - audit doesn't build these; a modelling course would help")

    # Languages
    langs = profile.get("languages", ["english"])
    lang = re.search(r"\b(?:fluen\w*|native|proficien\w*|business[- ]level|bilingual|strong)\b[^.•]{0,25}?\b(" + _LANGS + r")\b|"
                     r"\b(" + _LANGS + r")\b[^.•]{0,15}?\b(fluency|fluent|speaker|speaking|language skills|(is )?required|proficiency)\b", low)
    if advert_read and lang and (lang.group(1) or lang.group(2)) not in langs:
        near = low[max(0, lang.start() - 50):lang.end() + 40]
        if not _SYS_SOFT.search(near):
            m *= .2
            flags.append(f"Needs fluent {(lang.group(1) or lang.group(2)).title()}")

    # Coding
    if advert_read and not profile.get("can_code"):
        need_code, code = coding_need(low)
        if need_code == "hard":
            m *= .5
            flags.append(f"Needs coding ({'Python/SQL' if code in ('python', 'sql') else code})")
        elif need_code == "soft":
            flags.append("Python/SQL is a plus, not required")

    # Degree: held. Flag requirements that depend on details to check.
    if advert_read:
        adv = next((x for x in _ADV_DEGREE.finditer(low)
                    if not re.search(r"(bachelor|undergraduate|bsc|first degree|\bor\b|and/or)[^.]{0,30}$", low[max(0, x.start() - 45):x.start()])
                    and not re.search(r"^[^.]{0,40}or equivalent", low[x.end():x.end() + 60])), None)
        if adv and not _soft(low, adv):
            m *= .6
            flags.append("Asks for a master's / MBA - check whether your degree counts")
        if _TWO_ONE.search(low):
            flags.append("Asks for a 2:1 degree - check your class meets it")
        if re.search(r"\b(a\*?a\*?a|aab|abb)\b|\bucas\b", low):
            flags.append("Screens on A-level / UCAS grades - check yours meet it")

    # Qualifications
    other = next((x for x in _OTHER_QUAL.finditer(low)
                  if not _soft(low, x) and not re.search(r"(\bor\b|towards|studying|working)[^.]{0,25}$", low[max(0, x.start() - 30):x.start()])),
                 None) if advert_read else None
    if other:
        g = other.group(0)
        name = next((n for k, n in _OTHER_QUAL_NAME if k in g), "a specialist qualification")
        m *= .25
        flags.append(f"Needs {name} - ACA doesn't cover it")
    qual = next((x for x in _QUALIFIED.finditer(low) if not _soft(low, x)), None)
    if qual:
        sent = _sentence(low, qual.start(), qual.end())
        if re.search(r"\bcpa\b", sent) and not re.search(r"\b(aca|acca|icaew|chartered|ca\b|cima)|or equivalent", sent):
            m *= .5
            flags.append("Wants a US CPA - ACA may not be accepted on its own")
        else:
            m *= 1.15
            pros.append("Wants a qualified accountant - you're ICAEW ACA qualified")
    elif advert_read and re.search(r"\b(aca|icaew|acca|chartered accountant|qualified accountant|accountancy qualification)\b", low):
        pros.append("Mentions ACA / a professional qualification - you hold the ACA")

    # Specialist systems
    if advert_read:
        kind, names = systems_need(job.get("title", ""), low, profile.get("systems_known", []))
        if kind and kind != "soft":
            m *= _SYS_MULT[kind]
            nm = "/".join(names)
            flags.append(f"Asks for {nm} experience - not something audit gives you")

    # What audit gives him, quoted from the advert
    if advert_read:
        found = strengths_in(low)
        core = [found[k] for k in ("audit", "reporting", "controls", "accounting") if k in found]
        if core:
            m *= 1 + .05 * min(len(core), 3)
            pros.append("Asks for " + ", ".join(dict.fromkeys(core[:3])) + f" - core to your {years:g} yrs of audit")
        if "excel" in found:
            pros.append("Excel-heavy")

    if level == "senior":
        m *= .7
        flags.append("Manager-level: a step up from Assistant Manager while changing field - a stretch")
    if not advert_read:
        m *= .85
        flags.append("Advert text not read - check whether deal experience is required")
    return min(base * m, .95), flags, pros, status, quote



# Banks state the corporate title in the advert ("Vice President Expectations", "Corporate title: Associate").
_CORP_TITLE = re.compile(r"\b(assistant vice president|vice president|managing director|executive director|director|associate|analyst)"
                         r"\s+expectations\b|corporate title:?\s*(assistant vice president|vice president|managing director|"
                         r"executive director|director|associate|analyst)\b", re.I)
_CORP_LEVEL = {"analyst": "entry", "associate": "mid", "assistant vice president": "mid", "vice president": "senior",
               "executive director": "senior", "director": "exec", "managing director": "exec"}


def level_from_advert(title, desc, dept=""):
    level = level_of(title, dept)
    if level in ("entry", "mid") and not re.search(r"assistant manager|\bavp\b|assistant vice president|\bsenior\b", title or "", re.I):
        c = _CORP_TITLE.search(desc or "")
        # "Corporate title: X" is explicit; Barclays-style "X Expectations" only fills in a title with no level words.
        if c and (c.group(2) or level == "mid"):
            return _CORP_LEVEL[(c.group(1) or c.group(2)).lower()]
    return level


# ---------------------------------------------------------------- main scorer
def score(job, profile, aliases):
    cat = job.get("category") or classify(job.get("company"), aliases)
    job["_category"] = cat
    region = job.get("region") or ("UK" if job.get("source") in ("adzuna", "reed", "gov.uk apprenticeships")
                                   else region_of(job.get("location")) or "UK")
    job["_region"] = region
    level = level_from_advert(job["title"], job.get("description", ""), job.get("department", ""))
    func = function_of(job["title"], job.get("department", ""))
    interest, tracks = interest_of(job["title"], f"{job.get('department', '')} {job.get('description', '')}")

    cur = job.get("salary_currency") or ("USD" if region == "US" else "GBP")
    smin, smax = job.get("salary_min"), job.get("salary_max")
    if not smin and not smax:
        smin, smax = parse_salary(job.get("salary_text") or "", cur)
    if not smin and not smax and job.get("source") not in ("gov.uk apprenticeships",):
        # Only trust salaries spelled out in the first part of the description (US: next to a pay word, anywhere).
        desc = job.get("description") or ""
        smin, smax = parse_salary(find_pay_text(desc, cur) if cur == "USD" else desc[:2500], cur)
        if not smin and not smax and cur == "GBP":
            smin, smax = parse_salary(find_pay_text(desc, cur), cur)  # "The starting salary is £25,000" near the end
    # "Total Compensation Range: $150,000-190,000" already includes the bonus.
    desc = job.get("description") or ""
    all_in = bool(re.search(r"total (compensation|comp\b|pay|remuneration|target cash)[^.]{0,40}[$£]\s?\d", desc, re.I)) and \
        not re.search(r"base (salary|pay|compensation)[^.]{0,60}[$£]\s?\d", desc, re.I) and not job.get("salary_min")
    base_pay = None
    if smin or smax:
        base_pay = ((smin or smax) + (smax or smin)) / 2
        if cur == "USD":
            base_pay *= USD_TO_GBP
    # Advertised pay well above entry level means it isn't an entry job, whatever the title says (prop firms excepted).
    if base_pay and cat not in ("prop_trading", "hedge_fund") and level in ("entry", "mid"):
        usd = base_pay / USD_TO_GBP
        if level == "entry" and (usd > 150_000 if region == "US" else base_pay > 90_000):
            level = "mid"
        if level == "mid" and (usd > 260_000 if region == "US" else base_pay > 150_000):
            level = "senior"
    li = LEVELS.index(level)
    london = is_london(job.get("location")) or "remote" in (job.get("location") or "").lower()
    if base_pay:
        bonus = 0 if level in ("apprentice", "intern") or all_in else BONUS[cat] * (1 if func == "front" else .4)
        comp = base_pay * (1 + bonus)
        comp_basis = "advertised"
    else:
        # Recruiter ads and unlisted firms: deal roles are priced like mid-tier advisory, not generic finance.
        band = "mid_tier" if cat == "other" and set(tracks) & {"Transaction services", "Corporate finance / M&A"} else cat
        comp = BANDS[band][li] * 1000
        if level not in ("apprentice", "intern"):
            if func == "back":
                comp *= BACK_OFFICE[cat]
            elif func in ("other", "tech") and cat not in ("big4", "mid_tier", "other"):
                comp *= (.55 if cat in ELITE else .75) if func == "other" else .9
        if region == "US":
            comp *= US_PAY["hub" if US_HUBS.search(job.get("location") or "") else "other"]
        elif not london:
            comp *= .85
        comp_basis = "estimated"

    reach, flags, pros, deal, deal_quote = eligibility(job, level, profile)
    if cat in ELITE and func == "front" and deal != "open":
        if level in ("mid", "senior"):
            reach *= .5
            flags.append("IB / PE associate roles mostly hire ex-analysts or Big 4 deals people - a stretch straight from audit")
        elif level == "entry":
            reach *= .6
            flags.append("Analyst roles at banks and funds are very competitive, and you'd join below your current grade")
    if ("Transaction services" in tracks or "Corporate finance / M&A" in tracks) and cat in ("big4", "mid_tier") and level in ("entry", "mid"):
        reach = min(reach * 1.25, .95)
        pros.append("Audit to TS / corporate finance at a Big 4 or mid-tier firm is the standard move")
    if re.search(r"\bkpmg\b", job.get("company") or "", re.I) and set(tracks) & {"Transaction services", "Corporate finance / M&A"}:
        reach = min(reach * 1.2, .95)
        pros.append("You're already at KPMG - an internal move into Deal Advisory is usually the easiest route")
    wp = workplace_of(job)
    prefs = profile["preferences"]
    wmult = prefs["remote_multiplier"].get(wp, 1.0)
    place = 1.0 if london else prefs.get("outside_london_multiplier", .9)
    fit = (.25 + .75 * interest) * wmult * place
    match = comp * reach * fit

    job.update(
        category=cat, category_label=CATEGORY_LABEL[cat], level=level, function=func, region=region,
        interest=round(interest, 2), tracks=tracks, workplace_type=wp,
        summary=role_summary(job.get("description") or "", job.get("title", "")),
        currency=cur, base_pay=round(base_pay) if base_pay else None, comp=round(comp, -2), comp_basis=comp_basis,
        base_range=[round(smin or smax, -2), round(smax or smin, -2)] if base_pay else None,  # advert's own figures, its currency
        pay_all_in=all_in if base_pay else None,
        reach=round(reach, 2), flags=flags, pros=pros, match=round(match),
        deal_exp=deal, advert_read=len(job.get("description") or "") >= 300,
    )
    job.pop("_category", None)
    job.pop("_region", None)
    return job
