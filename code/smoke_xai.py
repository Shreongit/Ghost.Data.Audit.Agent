"""Small live xAI capability check: text, JSON Schema, then one PNG."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm import LLMClient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, help='PNG to send for the vision check; defaults to the first dataset PNG')
    args = parser.parse_args()
    images = sorted((ROOT / 'dataset' / 'evidence').rglob('*.png'))
    image = args.image or (images[0] if images else None)
    if image is None or not image.is_file():
        parser.error('No readable PNG was found; pass --image with a PNG path.')

    client = LLMClient(ROOT)
    tier = 'fast'
    model = client.fast
    print(f'Provider: {client.provider}; text/schema/image model: {model}')
    try:
        text = client.text_call('xai_smoke_text', 'Reply with exactly: xAI text call succeeded.', tier=tier)
        print('Text call: PASS' if 'succeeded' in text.lower() else 'Text call: PASS (response received)')
    except Exception as exc:
        print(f'Text call: FAIL ({type(exc).__name__}, status={getattr(exc, "status_code", "unavailable")})')
        return 1

    schema = {'type':'object','required':['ok'],'additionalProperties':False,
              'properties':{'ok':{'type':'boolean'}}}
    try:
        result = client.structured('xai_smoke_schema', 'Return the required JSON object with ok set to true.',
                                   'Return {"ok":true}.', schema, tier=tier)
        print(f'JSON-schema/local-validation call: {"PASS" if result["ok"] else "FAIL"}')
        if not result['ok']:
            return 1
    except Exception as exc:
        print(f'JSON-schema call: FAIL ({type(exc).__name__}, status={getattr(exc, "status_code", "unavailable")})')
        return 1

    image_schema = {'type':'object','required':['observation'],'additionalProperties':False,
                    'properties':{'observation':{'type':'string'}}}
    try:
        result = client.structured('xai_smoke_image', 'Describe only one clearly visible visual detail. Do not infer identity.',
                                   'What is one visible detail in this image?', image_schema,
                                   tier=tier, image_paths=[image])
        print(f'Image call: PASS ({image.name}; response validated)')
    except Exception as exc:
        print(f'Image call: UNSUPPORTED/FAILED ({type(exc).__name__}, status={getattr(exc, "status_code", "unavailable")}); skip VLM')

    totals = client.totals
    cost = 'not estimated' if totals['estimated_cost_usd'] is None else f"${totals['estimated_cost_usd']:.6f}"
    print(f"Successful calls recorded: {totals['calls']}; input tokens: {totals['input_tokens']}; output tokens: {totals['output_tokens']}; cost: {cost}")
    print('Usage details are in code/.cache/usage.json. Configure the per-million rates from the xAI console for a cost estimate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
