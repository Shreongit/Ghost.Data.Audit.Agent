"""Small provenance graph for time-filtered identity-to-resource traversal."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable
import re
import unicodedata


def _norm(value: Any) -> str:
    text=''.join(c for c in unicodedata.normalize('NFKD',str(value or '').casefold()) if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',text).strip()

def _contains(haystack: str, needle: str) -> bool:
    if re.fullmatch(r'[\w ]+',needle,re.UNICODE):
        return re.search(r'(?<!\w)'+re.escape(needle)+r'(?!\w)',haystack,re.UNICODE) is not None
    return needle in haystack

def _matches_fact_alias(fact: EvidenceFact, alias: str, haystack: str) -> bool:
    if re.fullmatch(r'[a-z ]+',alias) and ' ' in alias:
        data=fact.payload.get('data',{})
        names={_norm(data.get(key)) for key in ('name','full_name','customer_name','requester_name','owner_name') if isinstance(data,dict) and data.get(key)}
        if names:
            return alias in names
    return _contains(haystack,alias)


@dataclass(frozen=True)
class EvidenceFact:
    source_id: str
    source_type: str
    observed_at: datetime
    resource_id: str
    system_id: str
    data_category: str
    identifiers: frozenset[str]
    confidence: float
    payload: dict[str, Any] = field(compare=False, hash=False)


@dataclass(frozen=True)
class GraphEdge:
    left: str
    relation: str
    right: str
    source_id: str
    confidence: float


class EvidenceGraph:
    """Indexes participant-visible facts; edges always retain their evidence source."""

    def __init__(self, raw_facts: Iterable[dict[str, Any]]):
        self.facts: list[EvidenceFact] = []
        self.edges: list[GraphEdge] = []
        self._by_resource: dict[str, list[EvidenceFact]] = {}
        self._by_identifier: dict[str, list[EvidenceFact]] = {}
        self._by_word: dict[str, set[EvidenceFact]] = {}
        self._search_text: dict[EvidenceFact, str] = {}
        for raw in raw_facts:
            identifiers = set(raw.get('emails', ())) | set(raw.get('users', ()))
            identifiers |= set(raw.get('hashes', ())) | set(raw.get('phones', ()))
            identifiers |= {str(raw.get('resource', '')).casefold()} if raw.get('resource') else set()
            for key in ('name', 'full_name', 'customer_name', 'requester_name', 'owner_name'):
                value = raw.get('data', {}).get(key)
                if value:
                    identifiers.add(' '.join(str(value).casefold().split()))
            fact = EvidenceFact(
                source_id=str(raw.get('file', '')),
                source_type=str(raw.get('source_type', 'evidence')),
                observed_at=raw['time'],
                resource_id=str(raw.get('resource', '')),
                system_id=str(raw.get('system', 'unknown_service')),
                data_category=str(raw.get('category', 'UNKNOWN')),
                identifiers=frozenset(identifiers),
                confidence=float(raw.get('confidence', 1.0 if raw.get('direct') else 0.7)),
                payload=raw,
            )
            self.facts.append(fact)
            self._search_text[fact]=_norm(str(raw.get('text',''))+' '+str(raw.get('data','')))
            for word in set(re.findall(r'\w+',self._search_text[fact],re.UNICODE)):
                self._by_word.setdefault(word,set()).add(fact)
            if fact.resource_id:
                self._by_resource.setdefault(fact.resource_id, []).append(fact)
            for identifier in identifiers:
                if identifier:
                    self._by_identifier.setdefault(identifier, []).append(fact)
                    if fact.resource_id and identifier != fact.resource_id.casefold():
                        self.edges.append(GraphEdge(identifier, 'co_mentioned_with', fact.resource_id, fact.source_id, fact.confidence))
            if fact.resource_id:
                self.edges.append(GraphEdge(fact.source_id, 'describes', fact.resource_id, fact.source_id, fact.confidence))

    def walk(self, identifiers: Iterable[str], cutoff: datetime) -> tuple[list[dict[str, Any]], list[GraphEdge]]:
        """Return cutoff-valid seed facts and resource-linked snapshots, with paths."""
        seeds: set[EvidenceFact] = set()
        for identifier in identifiers:
            normalized=_norm(identifier)
            seeds.update(self._by_identifier.get(normalized, ()))
            # Email, phone, hash, user-id and resource identifiers use the exact
            # indexes above. Substring search is reserved for full name aliases.
            if normalized not in self._by_identifier and len(normalized)>=5 and re.fullmatch(r'[a-z ]+',normalized) and ' ' in normalized:
                tokens=normalized.split(); pool=set.intersection(*(self._by_word.get(token,set()) for token in tokens)) if tokens else set()
                seeds.update(f for f in pool if _matches_fact_alias(f,normalized,self._search_text[f]))
        seeds = {f for f in seeds if f.observed_at <= cutoff and f.payload.get('file_time', f.observed_at) <= cutoff}
        resources = {f.resource_id for f in seeds if f.resource_id}
        linked = [f for f in self.facts if f.resource_id in resources and f.observed_at <= cutoff and f.payload.get('file_time', f.observed_at) <= cutoff]
        alias_nodes={_norm(x) for x in identifiers}
        paths = [e for e in self.edges if e.right in resources and (e.left in alias_nodes or e.relation == 'describes')]
        for fact in seeds:
            for alias in alias_nodes:
                if alias and len(alias)>=5 and alias not in self._by_identifier and re.fullmatch(r'[a-z ]+',alias) and ' ' in alias and _matches_fact_alias(fact,alias,self._search_text[fact]) and fact.resource_id:
                    paths.append(GraphEdge(alias,'co_mentioned_with',fact.resource_id,fact.source_id,fact.confidence))
        paths=sorted(set(paths),key=lambda e:(e.left,e.relation,e.right,e.source_id,-e.confidence))
        # Preserve input order while de-duplicating linked payloads.
        result = []
        seen: set[int] = set()
        for f in linked:
            if id(f) not in seen:
                seen.add(id(f)); result.append(f.payload)
        return result, paths
