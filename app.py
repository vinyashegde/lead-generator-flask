import os
import json
import time
from flask import Flask, render_template, request, Response, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import uuid
from scraper import generate_leads
from scraper_linkedin import generate_linkedin_leads
from analyzer import analyze_csv_file

# Load environment variables
load_dotenv('.env.local')
api_key = os.getenv("SERPAPI_KEY")

if not api_key:
    load_dotenv('.env')
    api_key = os.getenv("SERPAPI_KEY")

if not api_key:
    print("WARNING: SERPAPI_KEY not found in environment. Scraping will fail.")

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(app.root_path, 'generated_leads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ping')
def ping():
    return jsonify({"status": "ok", "message": "Server is awake!"})

@app.route('/generate')
def generate():
    keyword = request.args.get('keyword', '')
    location = request.args.get('location', '')
    try:
        limit = int(request.args.get('limit', 10))
    except ValueError:
        limit = 10
    
    require_email = request.args.get('require_email', 'false').lower() == 'true'
    require_website = request.args.get('require_website', 'false').lower() == 'true'
    user_api_key = request.args.get('api_key', '').strip()
    
    # Use user provided key if exists, otherwise fallback to system
    final_api_key = user_api_key if user_api_key else api_key
    
    if not keyword or not location:
        return jsonify({"error": "Keyword and location are required"}), 400
        
    if not final_api_key:
        return jsonify({"error": "No SerpAPI key provided! Please enter one in the UI or set it in .env.local"}), 400

    def generate_events():
        try:
            for event in generate_leads(keyword, location, limit, final_api_key, require_email, require_website):
                # SSE dictates messages start with 'data: ' and end with two newlines
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
    return Response(generate_events(), mimetype='text/event-stream')

@app.route('/generate_linkedin')
def generate_linkedin():
    goal = request.args.get('goal', '')
    location = request.args.get('location', '')
    try:
        limit = int(request.args.get('limit', 10))
    except ValueError:
        limit = 10
    
    user_api_key = request.args.get('api_key', '').strip()
    final_api_key = user_api_key if user_api_key else api_key
    gemini_key = user_api_key if user_api_key else os.getenv("GEMINI_API_KEY")
    
    if not goal or not location:
        return jsonify({"error": "Business goal and location are required"}), 400
        
    if not final_api_key:
        return jsonify({"error": "No SerpAPI key provided! Please enter it in the UI or set SERPAPI_KEY in .env.local"}), 400
        
    if not gemini_key:
        return jsonify({"error": "No Gemini API key provided! Please enter it in the UI or set GEMINI_API_KEY in .env.local"}), 400

    def generate_events():
        try:
            for event in generate_linkedin_leads(goal, location, limit, final_api_key, gemini_key):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
    return Response(generate_events(), mimetype='text/event-stream')

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(f"upload_{uuid.uuid4().hex[:8]}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({"success": True, "filename": filename})
    return jsonify({"error": "Invalid file type. Please upload a .csv"}), 400

@app.route('/analyze')
def analyze():
    filename = request.args.get('filename', '')
    user_api_key = request.args.get('api_key', '').strip()
    
    # Needs a real Gemini key
    gemini_key = user_api_key if user_api_key else os.getenv("GEMINI_API_KEY")
    
    if not filename:
        return jsonify({"error": "File name is required"}), 400
        
    if not gemini_key:
        return jsonify({"error": "No Gemini API key provided! Please enter one in the UI or set GEMINI_API_KEY in .env.local"}), 400
        
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    def analyze_events():
        try:
            for event in analyze_csv_file(filepath, gemini_key):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
    return Response(analyze_events(), mimetype='text/event-stream')

@app.route('/download/<path:filename>')
def download(filename):
    # Ensure it only downloads from generated_leads
    safe_path = os.path.join(app.root_path, 'generated_leads', filename)
    if os.path.exists(safe_path) and os.path.isfile(safe_path):
        return send_file(safe_path, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
