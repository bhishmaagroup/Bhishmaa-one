import json

log_path = r"C:\Users\Hi\.gemini\antigravity\brain\af3e22ee-c546-4e38-ba94-d86d0eae831c\.system_generated\logs\transcript.jsonl"

with open(log_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        step = json.loads(line)
        if step.get('type') == 'USER_INPUT':
            content = step.get('content', '')
            print(f"INPUT {i}: length {len(content)}")
            if len(content) < 500:
                print(f"Content: {content}")
            else:
                print(f"Content: {content[:200]}... [truncated]")
            print("-" * 40)
