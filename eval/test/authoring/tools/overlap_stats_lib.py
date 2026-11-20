import re
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because been before being below
    between both but by can could did do does doing done down during each few for from further get got
    had has have having he her here hers herself him himself his how i if in into is it its itself just
    me more most my myself no nor not now of off on once only or other our ours ourselves out over own
    same she should so some such than that the their theirs them themselves then there these they this
    those through to too under until up very was we were what when where which while who whom why will
    with would you your yours yourself yourselves s t don ever also many much kind kinds type types
    like likely
    """.split()
)
# Mean question-evidence overlap of the public LoCoMo train split (581 questions).
TRAIN_MEANS = {"ALL": 0.437, "multi_hop": 0.472, "open_domain": 0.14, "single_hop": 0.427, "temporal": 0.518}


def _stem(t):
    for s in ("ing", "ed", "es", "s"):
        if t.endswith(s) and len(t) - len(s) >= 3:
            return t[: -len(s)]
    return t


def overlap_words(question, ev_texts, names):
    q = {}
    for t in TOKEN_RE.findall(question.lower()):
        if t not in STOPWORDS and t not in names:
            q[_stem(t)] = t
    if not q:
        return 0.0, set()
    ev = {_stem(t) for txt in ev_texts for t in TOKEN_RE.findall(txt.lower()) if t not in STOPWORDS}
    shared = {q[s] for s in q if s in ev}
    return len(shared) / len(q), shared
