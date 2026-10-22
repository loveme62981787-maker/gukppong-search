"""모델/브라우저 제어 없이 공개 YouTube 자막을 수집한다. 표준 라이브러리만 사용."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


class CaptionFailure(ValueError):
    pass


def request(url, payload=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('www.youtube.com', 'youtube.com'):
        raise CaptionFailure('caption_host_invalid')
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            final = urllib.parse.urlsplit(response.geturl())
            if final.scheme != 'https' or final.hostname not in ('www.youtube.com', 'youtube.com'):
                raise CaptionFailure('caption_redirect_invalid')
            raw = response.read(12_000_001)
    except urllib.error.HTTPError as error:
        raise CaptionFailure('caption_http_' + str(error.code)) from None
    except (urllib.error.URLError, TimeoutError):
        raise CaptionFailure('caption_network_error') from None
    if len(raw) > 12_000_000:
        raise CaptionFailure('caption_response_too_large')
    if not raw.strip():
        raise CaptionFailure('caption_empty_response')
    return raw.decode('utf-8')


def parse_xml(raw):
    if '<!DOCTYPE' in raw.upper() or '<!ENTITY' in raw.upper():
        raise CaptionFailure('caption_xml_declaration_rejected')
    try:
        root = ET.fromstring(raw)
        if root.tag == 'timedtext':
            rows = [(int(p.attrib['t']) // 1000, ''.join(p.itertext())) for p in root.findall('./body/p')]
        elif root.tag == 'transcript':
            rows = [(int(float(p.attrib['start'])), ''.join(p.itertext())) for p in root.findall('text')]
        else:
            raise CaptionFailure('caption_xml_format_unknown')
    except (ET.ParseError, KeyError, ValueError, OverflowError):
        raise CaptionFailure('caption_xml_invalid') from None
    lines = [(sec, re.sub(r'\s+', ' ', words).strip()) for sec, words in rows]
    lines = [(sec, words) for sec, words in lines if words]
    if not lines or any(sec < 0 for sec, _ in lines):
        raise CaptionFailure('caption_segments_missing')
    return '\n'.join(f'[{sec // 60}:{sec % 60:02d}] {words}' for sec, words in lines)


def download(video):
    vid = video['id']
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
        raise CaptionFailure('caption_video_invalid')
    page = request('https://www.youtube.com/watch?v=' + vid)
    match = re.search(r'(?:var\s+)?ytInitialPlayerResponse\s*=\s*', page)
    if not match:
        raise CaptionFailure('caption_player_unavailable')
    try:
        web_player, _ = json.JSONDecoder().raw_decode(page[match.end():])
    except ValueError:
        raise CaptionFailure('caption_player_invalid') from None
    # 로그인/연령/접근 제한을 다른 클라이언트로 우회하지 않는다.
    if web_player.get('playabilityStatus', {}).get('status') != 'OK':
        raise CaptionFailure('caption_video_not_publicly_playable')
    if web_player.get('videoDetails', {}).get('videoId') != vid:
        raise CaptionFailure('caption_video_mismatch')
    key = re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([a-zA-Z0-9_-]+)"', page)
    if not key:
        raise CaptionFailure('caption_public_client_config_missing')
    payload = {'context': {'client': {'clientName': 'ANDROID', 'clientVersion': '20.10.38'}}, 'videoId': vid}
    try:
        player = json.loads(request('https://www.youtube.com/youtubei/v1/player?key=' + key.group(1), payload))
    except ValueError as error:
        if isinstance(error, CaptionFailure):
            raise
        raise CaptionFailure('caption_player_invalid') from None
    if player.get('playabilityStatus', {}).get('status') != 'OK':
        raise CaptionFailure('caption_video_not_publicly_playable')
    if player.get('videoDetails', {}).get('videoId') != vid:
        raise CaptionFailure('caption_video_mismatch')
    tracks = player.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
    if not tracks:
        raise CaptionFailure('captions_unavailable')
    track = sorted(tracks, key=lambda t: (t.get('kind') == 'asr', t.get('languageCode') != 'en'))[0]
    body = parse_xml(request(track['baseUrl']))
    return f'YouTube transcript\nVideo ID: {vid}\nLanguage: {track.get("languageCode", "unknown")}\nSource: youtube_public_client\n\n' + body
