import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('score_alerts',Path(__file__).resolve().parents[1]/'score_alerts.py')
score=importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


class ScoreTests(unittest.TestCase):
    def test_chrome_copy_requires_full_copy_confirmation(self):
        video={'id':'abcdefghijk','length':'10:00'}
        header='Video ID: abcdefghijk\nSource: chrome_copy\n'
        with self.assertRaises(ValueError):
            score.transcript_info(header+'\nFull text without timestamps',video)
        info=score.transcript_info(header+'Full transcript verified: true\n\nFull text without timestamps',video)
        self.assertEqual(info['duration'],600)
        self.assertEqual(info['timestamps'],set())
        review={'status':'scored','scores':[10,10,10,10,5,5], 'points':[{'start_sec':None,'weight':.5,'evidence':'Full text'}]}
        score.validate_review(review,'Full text without timestamps',info)
        review['points'][0]['start_sec']=0
        with self.assertRaises(ValueError):
            score.validate_review(review,'Full text without timestamps',info)

    def test_wrong_video_and_partial_transcript_rejected(self):
        video={'id':'abcdefghijk','length':'10:00'}
        with self.assertRaises(ValueError):
            score.transcript_info('Video ID: different\n\n[0:00] hi\n[9:59] bye',video)
        with self.assertRaises(ValueError):
            score.transcript_info('Video ID: abcdefghijk\n\n[0:00] hi\n[1:00] bye',video)
        info=score.transcript_info('Video ID: abcdefghijk\nLanguage: en\n\n[0:00] hi\n[9:59] bye',video)
        self.assertEqual(info['duration'],600)

    def test_hallucinated_evidence_and_scores_rejected(self):
        review={'status':'scored','scores':[20,15,10,9,7,9], 'points':[{'start_sec':0,'weight':.5,'evidence':'very clean station'}]}
        info={'timestamps':{0}}
        score.validate_review(review,'[0:00] very clean station',info)
        review['points'][0]['evidence']='invented quote'
        with self.assertRaises(ValueError): score.validate_review(review,'[0:00] very clean station',info)
        review['points']=[]
        for invalid in (True,26,1.5,float('nan')):
            review['scores'][0]=invalid
            with self.assertRaises(ValueError): score.validate_review(review,'text',info)

    def test_public_whitelist_removes_private_details(self):
        item={'id':'abcdefghijk','ver':'jp','t':'Title','source':'claude_fm','fm_sha256':'a'*64,'transcript_sha256':'b'*64,
              'checked_at':'2026-10-21','min':10,'p':2.5,'s':[20,15,10,9,7,9], 'tw':'PRIVATE','points':['PRIVATE'],'email':'PRIVATE'}
        public=score.safe_public(item)
        self.assertNotIn('tw',public)
        self.assertNotIn('points',public)
        self.assertNotIn('email',public)
        self.assertEqual(public['p'],2.5)
        item['source']='gemini_fm'
        self.assertIn('Gemini',score.safe_public(item)['warn'][0])
        item['source']='deepseek_fm'
        with self.assertRaises(ValueError): score.safe_public(item)
        item['source']='gemini_fm'
        item['held']=True
        public=score.safe_public(item)
        self.assertNotIn('s',public)
        self.assertTrue(public['held'])

    def test_duplicate_points_rejected(self):
        point={'start_sec':0,'weight':1,'evidence':'a clean station'}
        review={'status':'scored','scores':[20,15,10,9,7,9],'points':[point,point]}
        with self.assertRaises(ValueError):
            score.validate_review(review,'a clean station',{'timestamps':{0}})

    def test_quote_must_match_its_timestamp(self):
        review={'status':'scored','scores':[20,15,10,9,7,9], 'points':[{'start_sec':0,'weight':1,'evidence':'clean station'}]}
        with self.assertRaises(ValueError):
            score.validate_review(review,'[0:00] hello\n[0:10] clean station',{'timestamps':{0,10}})


if __name__=='__main__': unittest.main()
