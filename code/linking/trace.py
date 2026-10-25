"""Parse line-oriented service logs and join related events into trace facts."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any

RESOURCE_RE = re.compile(r"\b(?:account|search|support|analytics|telemetry|export|backup|audit_record|data_flow|tombstone|cache|marketing|email_delivery)_\d+\b", re.I)
TIME_RE = re.compile(r"20\d\d-\d\d-\d\d(?:T| )\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:?\d\d)?")
GROUP_KEYS = ('trace_id','traceid','request_id','requestid','correlation_id','correlationid','correlation_key','session_id','sessionid','span_id')


def parse_time(value: str, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return fallback


def parse_line(line: str, fallback: datetime) -> dict[str, Any]:
    """Read JSON-in-text, quoted/unquoted key-value, and positional syslog dialects."""
    out: dict[str, Any] = {'_raw': line, '_time': parse_time((TIME_RE.search(line) or [None])[0] or '', fallback)}
    start = line.find('{')
    if start >= 0:
        try:
            obj, _ = json.JSONDecoder().raw_decode(line[start:])
            if isinstance(obj, dict):
                out.update({str(k).casefold(): v for k, v in obj.items()})
        except json.JSONDecodeError:
            pass
    # Accept JSON-style quoted keys as well as logfmt k=v and k: v fields.
    for m in re.finditer(r'''["']?([A-Za-z_][\w.-]*)["']?\s*(?:=|:)\s*(?:"([^"]*)"|'([^']*)'|([^,;\s}\]]+))''', line):
        key = m.group(1).casefold().replace('-', '_')
        value = next((x for x in m.groups()[1:] if x is not None), '')
        out.setdefault(key, value)
    # Syslog dialect: timestamp PRI version host service trace_id ...
    if not any(out.get(k) for k in GROUP_KEYS):
        m = re.search(r"\b(?:account_service|search_service|support_platform|analytics_platform|export_service|backup_service|security_service|integration_service|identity_service|notification_service)\s+\[?(tr-[\w-]+)\]?", line, re.I)
        if m:
            out['trace_id'] = m.group(1)
    return out


def trace_facts(path: Path, source_id: str, captured_at: datetime, *, fact_fn: Callable, system_fn: Callable, category_fn: Callable) -> list[dict[str, Any]]:
    lines = [line for line in path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
    events = [parse_line(line, captured_at) for line in lines]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    proximity: dict[tuple[str,str], tuple[int,datetime,str]] = {}
    for index, event in enumerate(events):
        token = next((str(event[k]) for k in GROUP_KEYS if event.get(k)), '')
        group='trace:' + token.casefold() if token else ''
        if not group:
            pod=str(event.get('pod','')).casefold();service=str(event.get('service',event.get('logger',''))).casefold()
            raw=str(event.get('_raw',''));has_resource=bool(RESOURCE_RE.search(raw));has_identity=bool(re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:lookup_key|match_key|subject_key|customer_reference|subject_ref)\s*[=:]',raw,re.I))
            prior=proximity.get((pod,service)) if pod and service else None
            if prior and abs((event['_time']-prior[1]).total_seconds())<=5 and ((has_resource and not has_identity) or (has_identity and not has_resource)):
                group=prior[2]
                proximity.pop((pod,service),None)
            elif pod and service and (has_resource != has_identity):
                group=f'proximity:{pod}:{service}:{index}'
                proximity[(pod,service)]=(index,event['_time'],group)
            else:
                group=f'line:{index}'
        groups[group].append(event)

    facts = []
    for group_id, group in groups.items():
        merged: dict[str, Any] = {}
        # The last event usually carries the observed result; earlier events
        # contribute identity lookup keys and request context.
        for event in group:
            for key, value in event.items():
                if not key.startswith('_') and value not in (None, ''):
                    merged[key] = value
        text = '\n'.join(str(event['_raw']) for event in group)
        resource_ids = sorted({rid for event in group for rid in RESOURCE_RE.findall(str(event.get('_raw', '')) + ' ' + str(event.get('resource_id', '')))}, key=str.casefold)
        if not resource_ids:
            continue
        when = max((event['_time'] for event in group), default=captured_at)
        # A grouped fact is emitted per resource. All line-level identifiers in
        # this trace are visible to the same-resource fact and retain provenance.
        for rid in resource_ids:
            data = dict(merged)
            data.update({'resource_id': rid, '_trace_group': group_id, '_trace_events': len(group)})
            system = system_fn(data, {}, str(path))
            item = fact_fn(source_id, when, system, rid, category_fn(data, {}), data, False, text)
            item.update({'file_time': captured_at, 'source_type': 'evidence', 'confidence': 0.9, '_trace_group': group_id})
            facts.append(item)
    return facts
