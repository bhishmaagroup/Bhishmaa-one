import json

log_path = r"C:\Users\Hi\.gemini\antigravity\brain\af3e22ee-c546-4e38-ba94-d86d0eae831c\.system_generated\logs\transcript.jsonl"

with open(log_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        step = json.loads(line)
        if step.get('type') == 'USER_INPUT' and i == 226:
            content = step.get('content', '')
            with open('input_226.txt', 'w', encoding='utf-8') as out:
                out.write(content)
            print("Successfully extracted input 226 to input_226.txt")
            break
