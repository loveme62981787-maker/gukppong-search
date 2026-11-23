"""사용자가 제외한 채널을 모든 Pages 데이터에서 제거한다. 원본 저장소는 보존한다."""
import json
import re

ASSIGN = re.compile(r'(?:^|;)[ \t]*window\.\w+[ \t]*=[ \t]*', re.M)
DECODER = json.JSONDecoder()


def assignments(text):
    for match in ASSIGN.finditer(text):
        try:
            value, end = DECODER.raw_decode(text, match.end())
        except ValueError:
            continue
        if isinstance(value, (list, dict)):
            yield match.end(), end, value


def normalize(value):
    return str(value or '').strip().casefold().replace('https://www.youtube.com/', '').rstrip('/')


def matched(record, config):
    for channel in config.get('channels', []):
        cid = channel['id']
        if record.get('channel_id') == cid or record.get('id') == cid:
            return True
        aliases = {normalize(x) for x in channel.get('names', []) + [channel.get('handle', ''), 'channel/' + cid]} - {''}
        if any(normalize(record.get(k)) in aliases for k in ('channel', 'channel_name', 'channel_title', 'handle', 'channel_handle', 'channel_url')):
            return True
    return False


def records(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from records(item)
    elif isinstance(value, list):
        for item in value:
            yield from records(item)


def blocked_ids(texts, config):
    ids = set(config.get('video_ids', []))
    for text in texts:
        for _, _, value in assignments(text):
            ids.update(r['id'] for r in records(value) if matched(r, config) and isinstance(r.get('id'), str))
    return ids


def clean(value, config, ids):
    if isinstance(value, dict):
        if matched(value, config) or value.get('id') in ids:
            return None
        result = {}
        for key, item in value.items():
            if key in ids:
                continue
            cleaned = clean(item, config, ids)
            if cleaned is not None or item is None:
                result[key] = cleaned
        return result
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := clean(item, config, ids)) is not None or item is None]
    return value


def filter_text(text, config, ids):
    for start, end, value in reversed(list(assignments(text))):
        filtered = clean(value, config, ids)
        if filtered != value:
            replacement = json.dumps(filtered, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
            text = text[:start] + replacement + text[end:]
    return text
