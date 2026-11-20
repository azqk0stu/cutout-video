import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('candidates', Path(__file__).resolve().parents[1]/'scripts/candidates.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CandidateTests(unittest.TestCase):
    def test_duration_diversity_and_topic_reason(self):
        segments = [dict(start=i*5,end=i*5+4,text='なるほど！' if i%3==0 else '次のお知らせです') for i in range(120)]
        embeddings = [[1,0] if i//12%2==0 else [0,1] for i in range(120)]
        candidates = module.suggest_candidates(segments, embeddings)
        self.assertEqual(len(candidates), 10)
        self.assertTrue(any(c['topic_start'] for c in candidates))
        for i,c in enumerate(candidates):
            self.assertTrue(30<=c['end']-c['start']<=60)
            for d in candidates[:i]:
                overlap=max(0,min(c['end'],d['end'])-max(c['start'],d['start']))
                self.assertLessEqual(overlap/min(c['end']-c['start'],d['end']-d['start']),.25)

    def test_short_silent_and_no_embeddings(self):
        self.assertEqual(module.suggest_candidates([]), [])
        self.assertEqual(module.suggest_candidates([dict(start=0,end=10,text='短い')]), [])
        result=module.suggest_candidates([dict(start=i*5,end=i*5+4,text='普通の会話') for i in range(20)])
        self.assertTrue(result)
        self.assertFalse(any(c['topic_start'] for c in result))
        with self.assertRaises(ValueError):
            module.suggest_candidates([dict(start=0,end=40,text='x')], [])

    def test_later_bands_survive_strong_opening(self):
        segments=[dict(start=i*5,end=i*5+4,text='なるほど！すごい！' if i<120 else '会話です') for i in range(600)]
        result=module.suggest_candidates(segments,limit=10)
        self.assertTrue(any((c['start']+c['end'])/2>2400 for c in result))
        self.assertTrue(any(1200<c['start']<1800 for c in result))

    def test_summary_is_from_candidate_only_and_reasons_explain_selection(self):
        segments=[dict(start=i*5,end=i*5+4,text=f'企画{i}について相談します。') for i in range(30)]
        for candidate in module.suggest_candidates(segments):
            self.assertTrue(candidate['summary'])
            self.assertLessEqual(len(candidate['summary']),220)
            source=''.join(s['text'] for s in segments if s['end']>candidate['start'] and s['start']<candidate['end'])
            for excerpt in candidate['summary'].split(' … '):
                self.assertIn(excerpt,source)
            self.assertIn(candidate['selection_basis'],candidate['reasons'])
        self.assertEqual(module.summarize_excerpt([]),'')
        self.assertEqual(module.summarize_excerpt([{'text':'同じ文。'},{'text':'同じ文。'}]),'同じ文。')
