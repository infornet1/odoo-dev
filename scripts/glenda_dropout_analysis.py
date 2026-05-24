#!/usr/bin/env python3
"""
Glenda Dropout Correlation Analysis
Hypothesis: longer Glenda outbound messages correlate with parent drop-off.
Runs against production via XML-RPC (read-only).
"""

import xmlrpc.client
import json
import statistics
from collections import defaultdict

CFG_FILE = '/opt/odoo-dev/config/production.json'

with open(CFG_FILE) as f:
    cfg = json.load(f)['production']['xmlrpc']

url, db, user, api_key = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, user, api_key, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def search_read(model, domain, fields, limit=0, order=''):
    kwargs = {'fields': fields}
    if limit:
        kwargs['limit'] = limit
    if order:
        kwargs['order'] = order
    return models.execute_kw(db, uid, api_key, model, 'search_read', [domain], kwargs)

print("=== Glenda Dropout Correlation Analysis ===\n")

# 1. Pull all conversations with state
convs = search_read(
    'ai.agent.conversation',
    [('skill_id.code', '=', 'general_inquiry')],
    ['id', 'state', 'channel', 'create_date', 'phone'],
    order='create_date asc'
)
print(f"Total general_inquiry conversations: {len(convs)}")

conv_ids = [c['id'] for c in convs]
conv_map = {c['id']: c for c in convs}

# 2. Pull all outbound messages for those conversations
messages = search_read(
    'ai.agent.message',
    [('conversation_id', 'in', conv_ids), ('direction', '=', 'outbound')],
    ['id', 'conversation_id', 'body', 'create_date'],
)
print(f"Total outbound messages: {len(messages)}\n")

# 3. Group messages by conversation
conv_messages = defaultdict(list)
for m in messages:
    conv_id = m['conversation_id'][0] if isinstance(m['conversation_id'], list) else m['conversation_id']
    conv_messages[conv_id].append(m)

# 4. Analyse by conversation state
state_stats = defaultdict(lambda: {
    'count': 0, 'msg_lengths': [], 'first_reply_lengths': [], 'msg_counts': []
})

for conv in convs:
    cid = conv['id']
    state = conv['state']
    msgs = sorted(conv_messages.get(cid, []), key=lambda x: x['create_date'])

    if not msgs:
        continue

    lengths = [len(m['body'] or '') for m in msgs]
    first_len = lengths[0] if lengths else 0

    state_stats[state]['count'] += 1
    state_stats[state]['msg_lengths'].extend(lengths)
    state_stats[state]['first_reply_lengths'].append(first_len)
    state_stats[state]['msg_counts'].append(len(msgs))

print("--- By Conversation State ---")
print(f"{'State':<12} {'Convs':>6} {'Avg Msgs':>9} {'Avg Char':>9} {'Med Char':>9} {'Avg 1st':>9} {'>500 1st':>9}")
print("-" * 72)

state_order = ['resolved', 'timeout', 'failed', 'active', 'waiting', 'draft']
for state in state_order:
    s = state_stats.get(state)
    if not s or s['count'] == 0:
        continue
    all_lens = s['msg_lengths']
    first_lens = s['first_reply_lengths']
    avg_char = statistics.mean(all_lens) if all_lens else 0
    med_char = statistics.median(all_lens) if all_lens else 0
    avg_first = statistics.mean(first_lens) if first_lens else 0
    pct_long_first = sum(1 for l in first_lens if l > 500) / len(first_lens) * 100 if first_lens else 0
    avg_msgs = statistics.mean(s['msg_counts']) if s['msg_counts'] else 0
    print(f"{state:<12} {s['count']:>6} {avg_msgs:>9.1f} {avg_char:>9.0f} {med_char:>9.0f} {avg_first:>9.0f} {pct_long_first:>8.0f}%")

print()

# 5. Overall distribution of first-reply lengths
all_first = []
for conv in convs:
    cid = conv['id']
    msgs = sorted(conv_messages.get(cid, []), key=lambda x: x['create_date'])
    if msgs:
        all_first.append(len(msgs[0]['body'] or ''))

if all_first:
    print("--- First Reply Length Distribution (all states) ---")
    buckets = [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500), (500, 700), (700, 900), (900, 9999)]
    for lo, hi in buckets:
        count = sum(1 for l in all_first if lo <= l < hi)
        bar = '█' * (count * 2)
        pct = count / len(all_first) * 100
        print(f"  {lo:>4}–{hi:<5}: {count:>3} ({pct:>4.0f}%) {bar}")
    print(f"\n  Total first replies: {len(all_first)}")
    print(f"  Avg: {statistics.mean(all_first):.0f} chars | Median: {statistics.median(all_first):.0f} chars")
    print(f"  >500 chars: {sum(1 for l in all_first if l > 500)} ({sum(1 for l in all_first if l > 500)/len(all_first)*100:.0f}%)")
    print(f"  >800 chars: {sum(1 for l in all_first if l > 800)} ({sum(1 for l in all_first if l > 800)/len(all_first)*100:.0f}%)")

# 6. Long first reply → resolved vs dropped?
print("\n--- First Reply > 500 chars: resolution rate vs short ---")
long_states = defaultdict(int)
short_states = defaultdict(int)
for conv in convs:
    cid = conv['id']
    state = conv['state']
    msgs = sorted(conv_messages.get(cid, []), key=lambda x: x['create_date'])
    if not msgs:
        continue
    first_len = len(msgs[0]['body'] or '')
    if first_len > 500:
        long_states[state] += 1
    else:
        short_states[state] += 1

long_total = sum(long_states.values())
short_total = sum(short_states.values())
print(f"\n  First reply > 500 chars ({long_total} convs):")
for state in ['resolved', 'timeout', 'failed', 'active']:
    n = long_states.get(state, 0)
    pct = n / long_total * 100 if long_total else 0
    print(f"    {state:<12}: {n:>3} ({pct:.0f}%)")

print(f"\n  First reply ≤ 500 chars ({short_total} convs):")
for state in ['resolved', 'timeout', 'failed', 'active']:
    n = short_states.get(state, 0)
    pct = n / short_total * 100 if short_total else 0
    print(f"    {state:<12}: {n:>3} ({pct:.0f}%)")

# 7. Longest individual messages sample
print("\n--- Top 10 Longest Glenda Messages (chars) ---")
all_msgs_with_len = [(len(m['body'] or ''), m) for m in messages if m.get('body')]
all_msgs_with_len.sort(key=lambda x: x[0], reverse=True)
for char_len, m in all_msgs_with_len[:10]:
    conv_id = m['conversation_id'][0] if isinstance(m['conversation_id'], list) else m['conversation_id']
    state = conv_map.get(conv_id, {}).get('state', '?')
    preview = (m['body'] or '')[:80].replace('\n', ' ')
    print(f"  {char_len:>5} chars [{state:>9}] {preview}…")

# 8. Channel breakdown
print("\n--- By Channel ---")
channel_stats = defaultdict(lambda: {'count': 0, 'lengths': []})
for conv in convs:
    cid = conv['id']
    channel = conv.get('channel', 'whatsapp')
    msgs = conv_messages.get(cid, [])
    for m in msgs:
        channel_stats[channel]['lengths'].append(len(m['body'] or ''))
    channel_stats[channel]['count'] += 1

for ch, s in channel_stats.items():
    avg = statistics.mean(s['lengths']) if s['lengths'] else 0
    print(f"  {ch:<12}: {s['count']} convs, avg {avg:.0f} chars/msg")

print("\n=== Done ===")
