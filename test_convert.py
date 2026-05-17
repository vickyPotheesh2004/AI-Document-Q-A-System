import os
from google import genai
from google.genai import types

def convert_messages(messages):
    system_instruction = None
    contents = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            system_instruction = content
        elif role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
        elif role == "assistant":
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
    return system_instruction, contents

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]
sys_inst, contents = convert_messages(messages)
print("Sys Inst:", sys_inst)
for c in contents:
    print(f"Role: {c.role}, Parts: {c.parts[0].text}")

config = types.GenerateContentConfig(system_instruction=sys_inst)
print("Config:", config)
