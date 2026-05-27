import os
import json

log_path = r"C:\Users\Hi\.gemini\antigravity\brain\af3e22ee-c546-4e38-ba94-d86d0eae831c\.system_generated\logs\transcript.jsonl"

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        step = json.loads(line)
        if step.get('type') == 'USER_INPUT':
            content = step.get('content', '')
            if 'FINAL PRODUCT VISION' in content or 'Bhishmaa ERP' in content:
                # Write the original request content to a text file for review
                with open('original_request.txt', 'w', encoding='utf-8') as out:
                    out.write(content)
                print("Successfully extracted original request to original_request.txt")
                break
