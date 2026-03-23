from flask import Flask, render_template, request, jsonify
import sys, re, requests, base64, os
from datetime import datetime
from werkzeug.utils import secure_filename

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from langdetect import detect as _detect, LangDetectException
    def detect_language(text):
        try:
            code = _detect(text)
            names = {"en":"English","te":"Telugu","hi":"Hindi","ta":"Tamil",
                     "fr":"French","de":"German","es":"Spanish","ja":"Japanese",
                     "zh-cn":"Chinese","ar":"Arabic","pt":"Portuguese"}
            return {"code": code, "name": names.get(code, code.upper())}
        except LangDetectException:
            return {"code":"en","name":"English"}
except ImportError:
    def detect_language(text):
        return {"code":"en","name":"English"}

INTENTS = {
    "greeting":     r"\b(hello|hi|hey|good\s*(morning|evening|afternoon)|howdy)\b",
    "farewell":     r"\b(bye|goodbye|see\s*you|take\s*care|later)\b",
    "question":     r"\b(what|who|where|when|why|how|which|can\s*you|do\s*you)\b",
    "help_request": r"\b(help|assist|support|guide|show\s*me|explain|teach)\b",
    "thanks":       r"\b(thank|thanks|thank\s*you|appreciate|grateful)\b",
    "complaint":    r"\b(problem|issue|error|bug|broken|wrong|bad|terrible|hate)\b",
    "search":       r"\b(search|find|look\s*up|locate|fetch|get)\b",
    "create":       r"\b(create|make|build|generate|write|produce|draft)\b",
    "calculate":    r"\b(calculate|compute|solve|math|number|add|subtract)\b",
    "translate":    r"\b(translate|convert|change\s*to)\b",
    "image":        r"\b(image|photo|picture|diagram|chart|screenshot|describe)\b",
    "file":         r"\b(file|document|pdf|spreadsheet|analyze|summarize|read)\b",
}

def detect_intent(text):
    lower = text.lower()
    scores = {k: len(re.findall(v, lower)) for k,v in INTENTS.items()}
    scores = {k:v for k,v in scores.items() if v}
    if not scores:
        return {"label":"general","confidence":0.5}
    best = max(scores, key=scores.get)
    return {"label": best, "confidence": round(min(0.95, 0.6 + scores[best]*0.1), 2)}

POS = {"good","great","excellent","amazing","awesome","love","happy","fantastic","wonderful","best","perfect","nice","like"}
NEG = {"bad","terrible","awful","hate","horrible","worst","poor","ugly","wrong","broken","error","fail","sad","angry","frustrated"}

def analyze_sentiment(text):
    words = set(re.findall(r'\b\w+\b', text.lower()))
    p, n = len(words & POS), len(words & NEG)
    if p > n:  return {"label":"positive","score": round(min(0.95, 0.6+p*0.1),2)}
    if n > p:  return {"label":"negative","score": round(min(0.95, 0.6+n*0.1),2)}
    return {"label":"neutral","score":0.70}

LOCS = {"india","usa","uk","china","japan","germany","france","australia","canada",
        "hyderabad","delhi","mumbai","bangalore","chennai","kolkata","london","paris",
        "new york","los angeles","tokyo","beijing","sydney","dubai","singapore"}

def extract_entities(text):
    found, seen = [], set()
    def add(t, label):
        k = t.lower().strip()
        if k not in seen:
            seen.add(k); found.append({"text":t.strip(),"label":label})
    for m in re.finditer(r'[\$\€\£\u20b9]\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s*(?:dollars?|euros?|rupees?|usd|inr)\b', text, re.I): add(m.group(),"MONEY")
    for m in re.finditer(r'\b\d+(?:\.\d+)?\s*%', text): add(m.group(),"PERCENT")
    for m in re.finditer(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+\d{1,2},?\s*\d{0,4}|today|tomorrow|yesterday)\b', text, re.I): add(m.group(),"DATE")
    for m in re.finditer(r'\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]m)?|\d{1,2}\s*[ap]m)\b', text, re.I): add(m.group(),"TIME")
    for m in re.finditer(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', text): add(m.group(),"EMAIL")
    for m in re.finditer(r'https?://[^\s]+', text): add(m.group(),"URL")
    for m in re.finditer(r'\b[A-Z][A-Za-z&\s]{2,}(?:Inc|LLC|Ltd|Corp|Co|Group|Technologies|University|Hospital|Bank|Airlines?|Systems?)\b', text): add(m.group(),"ORG")
    for m in re.finditer(r'\b([A-Z][a-z]{2,})(?:\s+[A-Z][a-z]{2,}){0,2}\b', text):
        t = m.group().strip(); low = t.lower()
        skip = {"the","this","that","these","those","there","what","when","where","which",
                "while","with","will","would","should","could","your","from","into","about",
                "after","before","because","hello","please","thank","sorry","okay","yes",
                "not","but","and","for","are","has","have","had","was","were","been","being"}
        if low in skip or low in seen: continue
        add(t, "LOCATION" if low in LOCS else "PERSON/ORG")
    for m in re.finditer(r'\b\d+(?:[,]\d{3})*(?:\.\d+)?\b', text):
        if m.group() not in seen: seen.add(m.group()); found.append({"text":m.group(),"label":"NUMBER"})
    return found

def run_nlp(text):
    if not text: return {"language":{"code":"en","name":"English"},"intent":{"label":"general","confidence":0.5},"sentiment":{"label":"neutral","score":0.70},"entities":[],"word_count":0,"char_count":0}
    return {"language":detect_language(text),"intent":detect_intent(text),
            "sentiment":analyze_sentiment(text),"entities":extract_entities(text),
            "word_count":len(text.split()),"char_count":len(text)}

app = Flask(__name__)
app.secret_key = "nexusai-2026"
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {'image/jpeg','image/png','image/gif','image/webp'}
ALLOWED_FILE_TYPES  = {'application/pdf','text/plain','text/csv','application/json',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}

@app.after_request
def add_charset(response):
    if response.content_type.startswith('text/html'):
        response.content_type = 'text/html; charset=utf-8'
    return response

SYSTEM = """You are a helpful, friendly general-purpose AI assistant.
Always reply in the SAME language the user writes in.
When the user shares an image, describe it in detail and answer their question about it.
When the user shares a file, analyze its content thoroughly and answer questions about it."""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/favicon.ico")
def favicon():
    return "", 204

@app.route("/chat", methods=["POST"])
def chat():
    data    = request.get_json(force=True)
    message = data.get("message","").strip()
    history = data.get("history",[])
    api_key = data.get("api_key","").strip()
    attachments = data.get("attachments", [])

    if not message and not attachments:
        return jsonify({"error":"Empty message"}), 400
    if not api_key:
        return jsonify({"error":"API key missing — click the API Key button to set it."}), 401

    user_content = []
    has_images = False
    file_names = []

    # --- Process each attachment ---
    for att in attachments:
        if att.get("type") == "file" and att.get("content"):
            fname = att.get("name", "file")
            file_names.append(fname)
            user_content.append({
                "type": "text",
                "text": f"[File attached: {fname}]\n\n{att['content']}\n\n[End of file]"
            })
        elif att.get("type") == "image" and att.get("data"):
            has_images = True
            fname = att.get("name", "image")
            file_names.append(fname)
            user_content.append({
                "type": "image_url",
                "image_url": {"url": att["data"]}
            })

    # --- Build the user text block ---
    if message:
        user_text = message
    elif file_names:
        if has_images:
            user_text = "Please describe this image in detail and provide any relevant analysis."
        else:
            user_text = f"Please analyze the attached file(s) ({', '.join(file_names)}) and provide a detailed summary of their contents."
    else:
        user_text = ""

    if user_text:
        user_content.append({"type": "text", "text": user_text})

    # Guard: nothing to send
    if not user_content:
        return jsonify({"error": "Nothing to send"}), 400

    model = "llama-3.2-11b-vision-preview" if has_images else "llama-3.3-70b-versatile"

    msgs = [{"role":"system","content":SYSTEM}]
    for m in history:
        msgs.append({"role":m["role"],"content":m["content"]})

    if not has_images and len(user_content) == 1:
        msgs.append({"role": "user", "content": user_content[0]["text"]})
    else:
        msgs.append({"role": "user", "content": user_content})

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
            json={"model":model,"messages":msgs,"max_tokens":1024,"temperature":0.7},
            timeout=30
        )
        result = resp.json()
        if resp.status_code != 200:
            err = result.get("error",{})
            msg = err.get("message",str(result)) if isinstance(err,dict) else str(err)
            return jsonify({"error":msg}), resp.status_code
        reply = result["choices"][0]["message"]["content"]
    except requests.Timeout:
        return jsonify({"error":"Request timed out. Try again."}), 504
    except Exception as e:
        return jsonify({"error":str(e)}), 500

    # For NLP sidebar: use message text if present, otherwise file content, otherwise filename
    nlp_text = message
    if not nlp_text and attachments:
        nlp_text = attachments[0].get("content", attachments[0].get("name", "file"))
    
    return jsonify({"reply":reply,"nlp":run_nlp(nlp_text),"timestamp":datetime.now().strftime("%H:%M")})

@app.route("/nlp", methods=["POST"])
def nlp_only():
    data = request.get_json(force=True)
    return jsonify(run_nlp(data.get("text","")))

@app.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        return jsonify({"error":"No file provided"}), 400
    f = request.files['file']
    mime = f.mimetype or ''
    name = secure_filename(f.filename or 'upload')

    if mime in ALLOWED_IMAGE_TYPES or name.lower().endswith(('.jpg','.jpeg','.png','.gif','.webp')):
        raw  = f.read()
        b64  = base64.b64encode(raw).decode('utf-8')
        actual_mime = mime if mime in ALLOWED_IMAGE_TYPES else 'image/jpeg'
        data_url = f"data:{actual_mime};base64,{b64}"
        return jsonify({"type":"image","name":name,"data":data_url,"mime":actual_mime})

    text_exts = ('.txt','.md','.csv','.json','.py','.js','.ts','.html','.css','.xml','.yaml','.yml')
    if mime in ALLOWED_FILE_TYPES or name.lower().endswith(text_exts):
        try:
            text = f.read().decode('utf-8', errors='replace')
            if len(text) > 15000:
                text = text[:15000] + "\n\n[... file truncated for context ...]"
            return jsonify({"type":"file","name":name,"content":text,"mime":mime})
        except Exception as e:
            return jsonify({"error":f"Could not read file: {e}"}), 400

    return jsonify({"error":f"Unsupported file type. Supported: images (jpg/png/gif/webp), text, csv, json, pdf, docx, xlsx."}), 415

if __name__ == "__main__":
    app.run(debug=True, port=5000)
