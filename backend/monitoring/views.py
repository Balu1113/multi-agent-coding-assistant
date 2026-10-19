import os
import sys
from pathlib import Path

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class MetricsView(APIView):
    def get(self, request: Request):
        from src.evaluation.monitor import Monitor

        m = Monitor()
        return Response(m.summary())


class RunBenchmarksView(APIView):
    def post(self, request: Request):
        from src.evaluation.benchmarks import CodingBenchmark

        bm = CodingBenchmark()

        def code_gen(prompt: str) -> str:
            from src.code_gen import generate_code

            return generate_code(prompt)

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(bm.run_all(code_gen))
        loop.close()

        summary = bm.summarize(results)
        return Response({
            "summary": summary,
            "results": [
                {
                    "name": r.name,
                    "success": r.success,
                    "duration": r.duration,
                    "score": r.score,
                    "details": r.details,
                }
                for r in results
            ],
        })

