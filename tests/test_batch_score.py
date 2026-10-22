import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import batch_score as b
import batch_daily as daily


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for obj, attr, value in [(b.s, 'PRIVATE', self.root), (b, 'STATE', self.root / 'state.json'),
                                 (b.s, 'PUBLIC', self.root / 'public.json')]:
            p = patch.object(obj, attr, value)
            p.start()
            self.addCleanup(p.stop)

    def video(self, i=0, length='10:01'):
        return {'id': f'{i:011d}', 'country': '한국', 'length': length, 'title': 'test'}

    def test_filter_boundary_unknown_dedup_and_done(self):
        rows = [self.video(0, '10:00'), self.video(1, ''), self.video(2), self.video(2), self.video(3)]
        with patch.object(b.s, 'alerts', return_value=rows), patch.object(b.s, 'manual_ids', return_value={self.video(3)['id']}):
            selected, stats = b.candidates(b.default_state())
        self.assertEqual([x['id'] for x in selected], [self.video(2)['id']])
        self.assertEqual(stats['short_or_unknown'], 2)
        self.assertEqual(stats['duplicate'], 1)

    def test_paused_never_calls_models_or_network(self):
        with patch.object(b, 'process') as process, patch.object(daily, 'command') as cmd:
            self.assertEqual(b.run_batch()['status'], 'paused')
            self.assertEqual(daily.daily()['status'], 'paused')
        process.assert_not_called()
        cmd.assert_not_called()

    def test_taiwan_candidates_and_private_fm(self):
        rows = [dict(self.video(i), country=c) for i, c in enumerate(['한국', '일본', '대만'])]
        with patch.object(b.s, 'alerts', return_value=rows), patch.object(b.s, 'manual_ids', return_value=set()):
            selected, _ = b.candidates(b.default_state())
        self.assertEqual([v['country'] for v in selected], ['한국', '일본', '대만'])
        self.assertEqual(b.s.fm_path('tw'), self.root / 'fm' / 'tw.md')
        with patch.object(b.s, 'alerts', return_value=rows), patch.object(b.s, 'manual_ids', return_value={rows[2]['id']}):
            selected, _ = b.candidates(b.default_state())
        self.assertNotIn(rows[2]['id'], [v['id'] for v in selected])

    def test_pilot_20_cumulative_and_restart(self):
        state = b.default_state()
        state.update(enabled=True, pilot_attempts=18)
        b.save(state)
        with patch.object(b, 'candidates', return_value=([self.video(i) for i in range(30)], {})), patch.object(b, 'process', return_value=(None, 'held')) as proc:
            self.assertEqual(b.run_batch()['attempted'], 2)
            self.assertEqual(b.run_batch()['attempted'], 0)
            self.assertEqual(proc.call_count, 2)
        saved = b.s.read_json(b.STATE, {})
        self.assertEqual(saved['pilot_attempts'], 20)
        with patch.object(b, 'now', return_value=datetime(2030, 1, 1, tzinfo=b.KST)):
            self.assertEqual(b.remaining(saved), 0)

    def test_daily_200_reserves_before_process(self):
        state = b.default_state()
        state.update(enabled=True, phase='production')
        day = b.now().date().isoformat()
        state['days'][day] = ['old'] * 199
        b.save(state)
        def process(v):
            self.assertEqual(len(b.s.read_json(b.STATE, {})['days'][day]), 200)
            raise RuntimeError('quota')
        with patch.object(b, 'candidates', return_value=([self.video(), self.video(1)], {})), patch.object(b, 'process', side_effect=process) as proc:
            self.assertEqual(b.run_batch()['attempted'], 1)
            self.assertEqual(proc.call_count, 1)
        self.assertFalse(b.s.read_json(b.STATE, {})['enabled'])

    def test_midnight_does_not_approve_incomplete_pilot(self):
        state = b.default_state()
        state['enabled'] = True
        b.save(state)
        first = datetime(2030, 1, 1, 23, 59, tzinfo=b.KST)
        next_day = datetime(2030, 1, 2, 0, 1, tzinfo=b.KST)
        with patch.object(b, 'candidates', return_value=([self.video(i) for i in range(10)], {})), patch.object(b, 'process', return_value=(None, 'held')), patch.object(b, 'now', side_effect=[first, first, first, next_day]):
            summary = b.run_batch()
        self.assertEqual(summary['attempted'], 1)
        self.assertFalse(b.s.read_json(b.STATE, {})['pilot_report_ready'])

    def test_lock_exclusion(self):
        with b.locked():
            with self.assertRaises(FileExistsError):
                with b.locked():
                    pass

    def test_ambiguity_gate(self):
        review = {'status': 'scored', 'scores': [20, 10, 10, 10, 5, 5],
                  'points': [{'start_sec': 0, 'weight': 1, 'evidence': 'clean station'}], 'uncertain': False, 'issues': []}
        self.assertEqual(b.assess(review, '[0:00] clean station', {'timestamps': {0}}), [])
        review['scores'] = [20, 15, 10, 10, 5, 10]
        self.assertIn('grade_boundary', b.assess(review, '[0:00] clean station', {'timestamps': {0}}))
        review['points'] = []
        self.assertIn('missing_evidence', b.assess(review, '', {'timestamps': {0}}))

    def test_cache_binds_provider_text_and_fm(self):
        with patch.object(b, 'call_model', return_value={'status': 'held'}) as call:
            for args in [('gemini', 't', 'f'), ('gemini', 't', 'f'), ('gemini', 'changed', 'f'), ('claude', 't', 'f'), ('gemini', 't', 'new')]:
                provider, text, fm = args
                b.model_review(provider, 'prompt', self.video(), text, fm)
            self.assertEqual(call.call_count, 4)

    def test_no_codex_verification_claim(self):
        item = {'id': 'abcdefghijk', 'ver': 'kr', 't': 'test', 'source': 'gemini_fm',
                'fm_sha256': 'a'*64, 'transcript_sha256': 'b'*64, 'checked_at': 'today',
                'min': 11, 'p': 1, 's': [20,10,10,10,5,5], 'verified_by': 'program'}
        clean = b.s.safe_public(item)
        self.assertNotIn('Codex', clean['warn'][0])
        self.assertEqual(clean['verified_by'], 'program')

    def test_pilot_publication_blocked(self):
        with self.assertRaises(ValueError):
            b.publish()
        self.assertFalse(b.s.PUBLIC.exists())

    def test_invalid_duration_excluded(self):
        for value in ('10:99', '-1:00', 'unknown', None, '', '00:10:99'):
            self.assertEqual(b.duration(value), 0)
        self.assertEqual(b.duration('10:00'), 600)
        self.assertEqual(b.duration('10:01'), 601)

    def test_model_failure_stops_on_malformed_envelope(self):
        with patch.object(b.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'not-json', '')):
            with self.assertRaises(b.ModelFailure):
                b.call_model('gemini', 'input')

    def test_long_prompt_uses_stdin_and_removes_api_env(self):
        envelope = json.dumps({'status': 'SUCCESS', 'response': '{"status":"held"}'})
        with patch.dict(b.os.environ, {'GEMINI_API_KEY': 'fake', 'ANTHROPIC_API_KEY': 'fake'}), patch.object(b.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, envelope, '')) as call:
            prompt = 'x' * 100000
            b.call_model('gemini', prompt)
            self.assertEqual(json.loads(call.call_args.kwargs['input'])['message']['content'], prompt)
            self.assertNotIn(prompt, call.call_args.args[0])
            self.assertNotIn('GEMINI_API_KEY', call.call_args.kwargs['env'])

    def test_antigravity_documented_stream_envelope_and_usage(self):
        envelope = {'event': 'result', 'result': {'status': 'SUCCESS', 'response': '{"status":"held"}', 'usage': {'input_tokens': 11, 'output_tokens': 3}}}
        stdout = json.dumps({'event': 'init'}) + '\n' + json.dumps(envelope) + '\n'
        with patch.object(b.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout, '')) as call:
            self.assertEqual(b.call_model('gemini', 'text')['status'], 'held')
            self.assertEqual(json.loads(call.call_args.kwargs['input']), {'event': 'user', 'message': {'content': 'text'}})
        record = json.loads((self.root / 'batch_usage.jsonl').read_text(encoding='utf-8'))
        self.assertEqual(record['usage']['usage']['input_tokens'], 11)

    def test_claude_structured_success_and_error_usage(self):
        review = {'status': 'held', 'reason': 'unrelated', 'resolved': False, 'uncertain': False, 'issues': []}
        envelope = {'subtype': 'success', 'result': '', 'structured_output': review, 'usage': {'output_tokens': 5}}
        with patch.object(b.shutil, 'which', return_value='claude'), patch.object(b.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(envelope), '')):
            self.assertEqual(b.call_model('claude', 'text'), review)
        envelope['subtype'] = 'error_max_turns'
        with patch.object(b.shutil, 'which', return_value='claude'), patch.object(b.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, json.dumps(envelope), '')):
            with self.assertRaises(b.ModelFailure):
                b.call_model('claude', 'text')
        records = [json.loads(line) for line in (self.root / 'batch_usage.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(records[-1]['usage']['usage']['output_tokens'], 5)
        self.assertEqual(records[-1]['error'], 'nonzero_exit')

    def test_caption_empty_is_classified(self):
        video = self.video()
        with patch.object(b.caption_fetch, 'download', side_effect=b.CaptionFailure('caption_empty_response')):
            with self.assertRaisesRegex(b.CaptionFailure, 'caption_empty_response'):
                b.transcript(video)
        self.assertFalse((self.root / 'transcripts' / (video['id'] + '.txt')).exists())

    def test_new_pilot_preserves_daily_budget_and_archive(self):
        ids = [self.video(i)['id'] for i in range(20)]
        state = b.default_state()
        state.update(pilot_attempts=20, videos={vid: {'status': 'held'} for vid in ids})
        state['days']['old'] = ids.copy()
        b.new_pilot(state, ids)
        self.assertEqual(state['days']['old'], ids)
        self.assertEqual(state['pilot_attempts'], 0)
        self.assertFalse(state['enabled'])
        self.assertEqual(len(list((self.root / 'batch_archive').glob('*/state.json'))), 1)

    def test_production_approval_requires_success_and_report(self):
        state = b.default_state()
        state.update(pilot_attempts=20, pilot_report_ready=True)
        with self.assertRaises(ValueError):
            b.approve_production(state, 'incorrect')
        vid = self.video()['id']
        state['videos'][vid] = {'status': 'staged'}
        b.s.atomic(self.root / 'batch_staged' / (vid + '.json'), '{}')
        report = {'infrastructure_failed': False, 'staged_hashes': b.staged_hashes(state)}
        b.s.atomic(self.root / 'batch_report.json', json.dumps(report))
        digest = b.hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
        state['report_hash'] = digest
        b.approve_production(state, digest)
        self.assertEqual(state['phase'], 'production')
        self.assertFalse(state['enabled'])

    def test_clear_gemini_skips_claude_and_ambiguous_routes(self):
        video = self.video()
        text = 'Video ID: ' + video['id'] + '\n\n[0:00] clean station ' + 'x'*400 + '\n[10:00] bye'
        review = {'status': 'scored', 'scores': [20,10,10,10,5,5], 'points': [{'start_sec': 0, 'weight': 1, 'evidence': 'clean station'}], 'uncertain': False, 'issues': []}
        skill = self.root / 'skills' / 'gukppong-score-kr' / 'SKILL.md'
        b.s.atomic(skill, 'FM')
        with patch.object(b.s, 'SKILLS', self.root / 'skills'), patch.object(b, 'transcript', return_value=text), patch.object(b, 'model_review', return_value=review) as call:
            item, _ = b.process(video)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(item['verified_by'], 'program')
        ambiguous = dict(review, uncertain=True, issues=['relationship'])
        resolved = dict(review, resolved=True)
        with patch.object(b.s, 'SKILLS', self.root / 'skills'), patch.object(b, 'transcript', return_value=text), patch.object(b, 'model_review', side_effect=[ambiguous, resolved]) as call:
            item, _ = b.process(video)
            self.assertEqual([x.args[0] for x in call.call_args_list], ['gemini', 'claude'])
            self.assertEqual(item['verified_by'], 'claude')

    def test_notes_do_not_block_resolved_review_but_real_issues_do(self):
        review = {'status': 'scored', 'scores': [20,10,10,10,5,5], 'points': [{'start_sec': 0, 'weight': 1, 'evidence': 'clean station'}], 'uncertain': False, 'resolved': True, 'unresolved_issues': [], 'notes': ['오인식 구간은 점수에서 제외함']}
        text, info = '[0:00] clean station', {'timestamps': {0}}
        self.assertEqual(b.disposition(review, text, info, final=True)[0], 'scored')
        for change in ({'unresolved_issues': ['화자 불명']}, {'uncertain': True}, {'resolved': False}, {'issues': ['구형 경고']}, {'points': [{'start_sec': 0, 'weight': 1, 'evidence': 'fabricated quote'}]}):
            with self.subTest(change=change):
                self.assertEqual(b.disposition(dict(review, **change), text, info, final=True)[0], 'review')

    def test_clear_held_skips_claude(self):
        video = self.video()
        text = 'Video ID: ' + video['id'] + '\n\n[0:00] ' + 'x'*400 + '\n[10:00] bye'
        b.s.atomic(self.root / 'skills' / 'gukppong-score-kr' / 'SKILL.md', 'FM')
        review = {'status': 'held', 'reason': 'unrelated', 'uncertain': False, 'unresolved_issues': [], 'notes': ['대상국과 무관']}
        with patch.object(b.s, 'SKILLS', self.root / 'skills'), patch.object(b, 'transcript', return_value=text), patch.object(b, 'model_review', return_value=review) as call:
            self.assertEqual(b.process(video), (None, 'gemini_held_unrelated'))
            self.assertEqual(call.call_count, 1)
        self.assertEqual(b.disposition(dict(review, uncertain=True), text, {'timestamps': {0}})[0], 'review')

    def test_site_input_merges_missing_duration_and_preserves_scored(self):
        b.s.atomic(self.root / 'web' / 'videos.js', 'window.SETTINGS={};window.VIDEOS=' + json.dumps([self.video(1), self.video(2), self.video(3, '10:00')]) + ';')
        state = dict(b.default_state(), input_source='all')
        with patch.object(b.s, 'BASE', self.root), patch.object(b.s, 'alerts', return_value=[self.video(1, '')]), patch.object(b.s, 'manual_ids', return_value={self.video(2)['id']}):
            rows, stats = b.candidates(state)
        self.assertEqual([v['id'] for v in rows], [self.video(1)['id']])
        self.assertEqual(stats['duplicate'], 1)
        self.assertEqual(stats['done'], 1)

    def test_prepare_site_pilot_stays_paused_preserves_budget(self):
        state = b.default_state()
        state.update(pilot_attempts=20, pilot_ids=['old'], days={'today': ['old']})
        with patch.object(b, 'candidates', return_value=([self.video(i) for i in range(30)], {})):
            ids = b.prepare_pilot(state, 'site')
        self.assertEqual(len(ids), 20)
        self.assertEqual(state['days'], {'today': ['old']})
        self.assertFalse(state['enabled'])
        self.assertEqual(state['input_source'], 'site')
        self.assertEqual(state['pilot_attempts'], 0)

    def test_gemini_repairs_once_before_claude_without_lowering_gate(self):
        video = self.video()
        text = 'Video ID: ' + video['id'] + '\n\n[0:00] clean station ' + 'x'*400 + '\n[10:00] bye'
        b.s.atomic(self.root / 'skills' / 'gukppong-score-kr' / 'SKILL.md', 'FM')
        good = {'status': 'scored', 'scores': [20,10,10,10,5,5], 'points': [{'start_sec': 0, 'weight': 1, 'evidence': 'clean station'}], 'uncertain': False, 'unresolved_issues': [], 'notes': []}
        bad = dict(good, points=[{'start_sec': 0, 'weight': 1, 'evidence': 'not in transcript'}])
        ambiguous = dict(bad, uncertain=True, unresolved_issues=['화자 불명'])
        final = dict(good, resolved=True)
        cases = [([bad, good], ['gemini', 'gemini']),
                 ([dict(bad, scores=[20,15,10,10,5,10]), good, final], ['gemini', 'gemini', 'claude']),
                 ([bad, bad, final], ['gemini', 'gemini', 'claude']),
                 ([ambiguous, good, final], ['gemini', 'gemini', 'claude']),
                 ([ambiguous, {'status': 'held', 'reason': 'unrelated', 'uncertain': False, 'unresolved_issues': []}, final], ['gemini', 'gemini', 'claude'])]
        for responses, providers in cases:
            with self.subTest(providers=providers), patch.object(b.s, 'SKILLS', self.root / 'skills'), patch.object(b, 'transcript', return_value=text), patch.object(b, 'model_review', side_effect=responses) as call:
                item, reason = b.process(video)
                self.assertEqual(reason, 'staged')
                self.assertEqual([c.args[0] for c in call.call_args_list], providers)
                self.assertIn('validation_error', call.call_args_list[1].args[5])
        with patch.object(b.s, 'SKILLS', self.root / 'skills'), patch.object(b, 'transcript', return_value=text), patch.object(b, 'model_review', side_effect=[bad, b.ModelFailure('offline')]) as call:
            with self.assertRaises(b.ModelFailure):
                b.process(video)
            self.assertEqual(call.call_count, 2)

    def test_failed_push_retries_without_model_or_early_published(self):
        vid = self.video()['id']
        state = b.default_state()
        state.update(enabled=True, phase='production', videos={vid: {'status': 'staged'}})
        b.save(state)
        daily.write_journal({'phase': 'committed', 'commit': 'our_commit', 'ids': [vid], 'hashes': {'x': 'h'}})
        def fail_push(args, **kwargs):
            if args[:2] == ['git', 'push']:
                raise RuntimeError('offline')
            if args[:2] == ['git', 'rev-parse']:
                return 'our_commit'
            return ''
        with patch.object(daily, 'file_hashes', return_value={'x': 'h'}), patch.object(daily, 'command', side_effect=fail_push):
            with self.assertRaises(RuntimeError): daily.recover_deployment()
        self.assertEqual(b.s.read_json(b.STATE, {})['videos'][vid]['status'], 'staged')
        with patch.object(daily, 'file_hashes', return_value={'x': 'h'}), patch.object(daily, 'command', side_effect=lambda args, **kw: 'our_commit' if args[:2] == ['git', 'rev-parse'] else ''), patch.object(b, 'process') as model:
            daily.recover_deployment()
            model.assert_not_called()
        self.assertEqual(b.s.read_json(b.STATE, {})['videos'][vid]['status'], 'published')

    def test_changed_file_blocks_recovery(self):
        state = b.default_state()
        state.update(enabled=True, phase='production')
        b.save(state)
        daily.write_journal({'phase': 'ready', 'hashes': {'x': 'old'}})
        with patch.object(daily, 'file_hashes', return_value={'x': 'changed'}), patch.object(daily, 'command', return_value='') as call:
            with self.assertRaises(RuntimeError): daily.recover_deployment()
            self.assertFalse(any(x.args[0][:2] == ['git', 'push'] for x in call.call_args_list))


if __name__ == '__main__':
    unittest.main()
