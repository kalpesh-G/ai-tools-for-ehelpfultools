
import os
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

FSM_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "name": {"type": "STRING"},
        "start_state": {"type": "STRING"},
        "states": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"id": {"type": "STRING"}, "output": {"type": "STRING"}}
            }
        },
        "transitions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"from": {"type": "STRING"}, "to": {"type": "STRING"}, "input": {"type": "STRING"}}
            }
        }
    }
}
SYSTEM_INSTRUCTION = (
    "You are an expert in Automata Theory. Your task is to generate a logically correct Moore Finite State Machine (FSM) in strict JSON format based on the user's request. "
    "Crucial Rules: 1. Ensure ALL transitions for the standard binary alphabet {0, 1} are included for every state. 2. The output representing successful detection must be emitted by the final state. 3. The entire response must be a single JSON object. "
    "The output MUST match the schema exactly: " + json.dumps(FSM_SCHEMA) + ". "
    
    "\n\n--- WORKED EXAMPLES FOR REFERENCE ---"
    
    "\n\n1. EXAMPLE: Detect sequence '101' (Success Output 'Y'):"
    '{"name":"101 Detector","start_state":"S0","states":[{"id":"S0","output":"N"},{"id":"S1","output":"N"},{"id":"S2","output":"N"},{"id":"S3","output":"Y"}],'
    '"transitions":['
    '{"from":"S0","to":"S0","input":"0"},{"from":"S0","to":"S1","input":"1"},'
    '{"from":"S1","to":"S2","input":"0"},{"from":"S1","to":"S1","input":"1"},'
    '{"from":"S2","to":"S0","input":"0"},{"from":"S2","to":"S3","input":"1"},'
    '{"from":"S3","to":"S0","input":"0"},{"from":"S3","to":"S1","input":"1"}]}'
    
    "\n\n2. EXAMPLE: Detect sequence '00' (Success Output '1'):"
    '{"name":"00 Detector","start_state":"S0","states":[{"id":"S0","output":"0"},{"id":"S1","output":"0"},{"id":"S2","output":"1"}],'
    '"transitions":['
    '{"from":"S0","to":"S1","input":"0"},{"from":"S0","to":"S0","input":"1"},'
    '{"from":"S1","to":"S2","input":"0"},{"from":"S1","to":"S0","input":"1"},'
    '{"from":"S2","to":"S2","input":"0"},{"from":"S2","to":"S0","input":"1"}]}'
    
    "\n\n--- END OF EXAMPLES ---\n\n"
)
# SYSTEM_INSTRUCTION = (
#     "You are an expert in automata theory. Given a natural language prompt, generate a valid Moore Finite State Machine (FSM) in strict JSON format. "
#     "The output must match this schema exactly: " + json.dumps(FSM_SCHEMA) + ". "
#     "All string values must follow the schema types exactly (STRING, ARRAY, OBJECT). "
#     "Do not include any explanations, comments, or extra text. Only output a single JSON object that fully conforms to the schema. "
#     "Here is an example for reference: "
#     '{"name":"EXAMPLE","start_state":"S0","states":[{"id":"S0","output":"0"},{"id":"S1","output":"1"}],'
#     '"transitions":[{"from":"S0","to":"S1","input":"1"},{"from":"S1","to":"S0","input":"0"}]}'
# )

# SYSTEM_INSTRUCTION = (
#     "You are an expert in automata theory. Given a natural language prompt, you must generate a valid Moore Finite State Machine (FSM) in strict JSON format. "
#     "The output must match the following schema exactly: " + json.dumps(FSM_SCHEMA) + ". "
#     "Do not include any explanation, only the JSON object."
# )

# Home page (list of tools)
@app.route('/')
def home():
    # In future, render a list of available tools/pages
    return render_template('home.html')

# Moore Machine Generator page
@app.route('/moore-machine-generator')
def moore_machine_generator():
    return render_template('moore-machine-generator.html')

# API endpoint for Moore Machine Generator
@app.route('/generate-machine', methods=['POST'])
def generate_machine():
    data = request.get_json()
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({'error': 'Prompt is required.'}), 400
    if not GEMINI_API_KEY:
        return jsonify({'error': 'Gemini API key not configured.'}), 500
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': GEMINI_API_KEY
    }
    # Gemini API only accepts 'user' and 'model' roles. Combine system instruction and prompt as a single user message.
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": SYSTEM_INSTRUCTION + "\n" + prompt}]}
        ]
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=60)
        # Log status code and response text for debugging
        print(f"Gemini API status: {response.status_code}")
        print(f"Gemini API response: {response.text}")
        response.raise_for_status()
        result = response.json()
        # Extract the JSON from the AI response
        text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        # Remove markdown code block markers if present
        if text.strip().startswith('```'):
            text = text.strip()
            # Remove triple backticks and optional 'json' language
            text = text.replace('```json', '').replace('```', '').strip()
        machine = None
        try:
            machine = json.loads(text)
        except Exception:
            print(f"AI returned invalid JSON: {text}")
            return jsonify({'error': 'AI returned invalid JSON.', 'raw': text}), 502

        # --- Post-process for frontend compatibility ---
        # Add 'alphabet' field by extracting unique inputs from transitions
        if 'transitions' in machine:
            machine['alphabet'] = sorted(list({t['input'] for t in machine['transitions'] if 'input' in t}))
        # Normalize state IDs and outputs
        if 'states' in machine:
            # Map original state IDs to S0, S1, ...
            id_map = {}
            for idx, s in enumerate(machine['states']):
                id_map[s['id']] = f"S{idx}"
            # Update states
            for s in machine['states']:
                s['id'] = id_map[s['id']]
                # Only allow outputs '0' or '1', default to '0' if not valid
                s['output'] = str(s.get('output', '0'))
                if s['output'] not in ['0', '1']:
                    s['output'] = '0'
            # Update transitions
            if 'transitions' in machine:
                for t in machine['transitions']:
                    t['from'] = id_map.get(t['from'], t['from'])
                    t['to'] = id_map.get(t['to'], t['to'])
            # Update start_state
            if 'start_state' in machine:
                machine['start_state'] = id_map.get(machine['start_state'], machine['start_state'])
            # Add 'start' boolean to states
            for s in machine['states']:
                s['start'] = (s['id'] == machine['start_state'])

        return jsonify({'machine': machine})
    except requests.RequestException as e:
        # Print full error response for debugging
        if hasattr(e, 'response') and e.response is not None:
            print(f"Gemini API error response: {e.response.text}")
        print(f"Gemini API exception: {str(e)}")
        return jsonify({'error': 'Failed to contact Gemini API.', 'details': str(e)}), 502

# if __name__ == '__main__':
#     app.run(debug=True)
