import os
import json
import tempfile
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import bcrypt
import PyPDF2

from database import (
    init_db, create_user, get_user_by_email, get_user_by_id,
    create_interview, update_interview_results, get_interview,
    get_user_interviews, save_question, update_question_answer,
    get_interview_questions, save_resume, get_latest_resume,
    save_performance_details, get_performance_details
)
from ai_engine import configure_ai, generate_questions, evaluate_answer, generate_overall_feedback

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'interview-master-secret-2026')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

ALLOWED_EXTENSIONS = {'pdf'}

# Configure AI
api_key = os.getenv('GEMINI_API_KEY', '')
if api_key:
    configure_ai(api_key)

# Initialize database
init_db()

# ---- Helper Functions ----
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_pdf_text(filepath):
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ---- Routes ----

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        role = request.form.get('role', 'Candidate').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([full_name, email, password]):
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        if create_user(full_name, email, hashed, role):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('An account with this email already exists.', 'error')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = get_user_by_email(email)
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_role'] = user['role']
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user_by_id(session['user_id'])
    interviews = get_user_interviews(session['user_id'])
    resume = get_latest_resume(session['user_id'])

    # Calculate stats
    total_interviews = len(interviews)
    avg_score = 0
    if total_interviews > 0:
        scores = [i['score'] for i in interviews if i['score'] > 0]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    return render_template('dashboard.html',
        user=user,
        interviews=interviews,
        resume=resume,
        total_interviews=total_interviews,
        avg_score=avg_score,
        user_role=session.get('user_role', 'Candidate')
    )

@app.route('/resume')
@login_required
def resume_page():
    resume = get_latest_resume(session['user_id'])
    return render_template('resume.html', resume=resume)

@app.route('/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    if 'resume' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('resume_page'))
    file = request.files['resume']
    if not file or not file.filename or not allowed_file(file.filename):
        flash('Please upload a valid PDF file.', 'error')
        return redirect(url_for('resume_page'))
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session['user_id']}_{filename}")
    file.save(filepath)
    resume_text = extract_pdf_text(filepath)
    save_resume(session['user_id'], filename, resume_text)
    flash('✅ Resume uploaded successfully! It will be used in all future interviews.', 'success')
    return redirect(url_for('resume_page'))

@app.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    if request.method == 'POST':
        job_role = request.form.get('job_role', '').strip()
        custom_role = request.form.get('custom_role', '').strip()
        company = request.form.get('company', '').strip()
        interview_type = request.form.get('interview_type', 'mixed')
        num_questions = int(request.form.get('num_questions', 10))

        if job_role == 'custom' and custom_role:
            job_role = custom_role

        selected_topics = request.form.get('selected_topics', '').strip()
        if selected_topics:
            job_role = f"{job_role} (Focus topics: {selected_topics})"

        if not job_role or not company:
            flash('Please fill in all required fields.', 'error')
            return render_template('setup.html')

        # Handle resume upload
        resume_text = ""
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session['user_id']}_{filename}")
                file.save(filepath)
                resume_text = extract_pdf_text(filepath)
                save_resume(session['user_id'], filename, resume_text)

        # Check for existing resume if none uploaded
        if not resume_text:
            existing_resume = get_latest_resume(session['user_id'])
            if existing_resume:
                resume_text = existing_resume['extracted_text']

        # Clamp num_questions
        num_questions = max(5, min(20, num_questions))

        # Generate questions via AI
        questions = generate_questions(job_role, company, interview_type, resume_text, num_questions)

        # Create interview record
        interview_id = create_interview(session['user_id'], job_role, company, interview_type, len(questions))

        # Save questions
        question_ids = []
        for i, q in enumerate(questions, 1):
            q_id = save_question(
                interview_id, i,
                q.get('question', f'Question {i}'),
                q.get('category', 'General'),
                q.get('difficulty', 'Medium')
            )
            question_ids.append(q_id)

        # Store interview state in session
        session['current_interview_id'] = interview_id
        session['current_question_index'] = 0

        return redirect(url_for('interview', interview_id=interview_id))

    saved_resume = get_latest_resume(session['user_id'])
    return render_template('setup.html', saved_resume=saved_resume)

@app.route('/interview/<int:interview_id>')
@login_required
def interview(interview_id):
    interview_data = get_interview(interview_id)
    if not interview_data or interview_data['user_id'] != session['user_id']:
        flash('Interview not found.', 'error')
        return redirect(url_for('dashboard'))

    questions = get_interview_questions(interview_id)
    return render_template('interview.html',
        interview=interview_data,
        questions=[dict(q) for q in questions]
    )

@app.route('/api/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    data = request.get_json()
    question_id = data.get('question_id')
    user_answer = data.get('answer', '')
    question_text = data.get('question_text', '')
    job_role = data.get('job_role', '')
    company = data.get('company', '')

    # Evaluate answer
    evaluation = evaluate_answer(question_text, user_answer, job_role, company)

    # Save to database
    update_question_answer(
        question_id,
        user_answer,
        evaluation.get('feedback', ''),
        evaluation.get('score', 0)
    )

    return jsonify(evaluation)

@app.route('/api/transcribe-audio', methods=['POST'])
@login_required
def transcribe_audio():
    """Receive an audio blob, transcribe it using Gemini, and return the text."""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    
    # Save to a temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
    try:
        audio_file.save(tmp.name)
        tmp.close()

        # Use Gemini to transcribe the audio
        import google.generativeai as genai
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Upload the audio file to Gemini
        uploaded = genai.upload_file(tmp.name, mime_type='audio/webm')

        response = model.generate_content([
            "Transcribe the following audio exactly as spoken. Return ONLY the transcribed text, nothing else. If you cannot hear anything clearly, return an empty string.",
            uploaded
        ])

        transcribed_text = response.text.strip()
        return jsonify({'text': transcribed_text})

    except Exception as e:
        print(f"Transcription error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            os.unlink(tmp.name)
        except:
            pass

@app.route('/api/finish-interview', methods=['POST'])
@login_required
def finish_interview():
    data = request.get_json()
    interview_id = data.get('interview_id')

    interview_data = get_interview(interview_id)
    if not interview_data or interview_data['user_id'] != session['user_id']:
        return jsonify({'error': 'Interview not found'}), 404

    questions = get_interview_questions(interview_id)
    questions_data = []
    for q in questions:
        questions_data.append({
            'question': q['question_text'],
            'category': q['category'],
            'difficulty': q['difficulty'],
            'user_answer': q['user_answer'],
            'score': q['score']
        })

    # Generate overall feedback
    overall = generate_overall_feedback(
        interview_data['job_role'],
        interview_data['company'],
        questions_data
    )

    # Update interview record
    update_interview_results(
        interview_id,
        overall.get('overall_score', 0),
        overall.get('rating', 'N/A'),
        json.dumps({
            'overall_feedback': overall.get('overall_feedback', ''),
            'technical_score': overall.get('technical_score', 0),
            'hr_score': overall.get('hr_score', 0),
            'communication_score': overall.get('communication_score', 0),
            'confidence_score': overall.get('confidence_score', 0),
            'skill_gaps': overall.get('skill_gaps', []),
            'learning_resources': overall.get('learning_resources', []),
            'improvement_roadmap': overall.get('improvement_roadmap', []),
            'weak_question_types': overall.get('weak_question_types', []),
            'strong_question_types': overall.get('strong_question_types', [])
        }),
        overall.get('top_strengths', []),
        overall.get('key_weaknesses', []),
        overall.get('action_items', [])
    )

    # Also save to performance_details table for structured storage
    save_performance_details(interview_id, overall)

    return jsonify({'redirect': url_for('results', interview_id=interview_id)})

@app.route('/results/<int:interview_id>')
@login_required
def results(interview_id):
    interview_data = get_interview(interview_id)
    if not interview_data or interview_data['user_id'] != session['user_id']:
        flash('Results not found.', 'error')
        return redirect(url_for('dashboard'))

    questions = get_interview_questions(interview_id)

    # Helper: safely parse JSON string → Python object
    def parse_json(val, default):
        if not val:
            return default
        if isinstance(val, (list, dict)):
            return val
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default

    # Parse top-level fields from interview_data (sqlite3.Row — use bracket notation)
    strengths   = parse_json(interview_data['strengths'], [])
    weaknesses  = parse_json(interview_data['weaknesses'], [])
    suggestions = parse_json(interview_data['suggestions'], [])

    # Parse detailed feedback — try structured table first, then JSON fallback
    perf = get_performance_details(interview_id)
    if perf:
        # Get overall feedback text from the feedback JSON column
        overall_feedback_text = ''
        try:
            fb_data = json.loads(interview_data['feedback']) if interview_data['feedback'] else {}
            if isinstance(fb_data, dict):
                overall_feedback_text = fb_data.get('overall_feedback', '') or interview_data['feedback'] or ''
            else:
                overall_feedback_text = interview_data['feedback'] or ''
        except (json.JSONDecodeError, TypeError):
            overall_feedback_text = interview_data['feedback'] or ''

        # perf is also a sqlite3.Row — use bracket notation and parse JSON fields
        technical_score      = perf['technical_score'] or 0
        hr_score             = perf['hr_score'] or 0
        communication_score  = perf['communication_score'] or 0
        confidence_score     = perf['confidence_score'] or 0
        skill_gaps           = parse_json(perf['skill_gaps'], [])
        learning_resources   = parse_json(perf['learning_resources'], [])
        improvement_roadmap  = parse_json(perf['improvement_roadmap'], [])
        weak_question_types  = parse_json(perf['weak_question_types'], [])
        strong_question_types = parse_json(perf['strong_question_types'], [])

    else:
        # Fallback: parse from JSON stored in the feedback column
        detailed = parse_json(interview_data['feedback'], {})
        if not isinstance(detailed, dict):
            detailed = {'overall_feedback': interview_data['feedback'] or ''}

        overall_feedback_text = detailed.get('overall_feedback', '') or interview_data['feedback'] or ''
        technical_score      = detailed.get('technical_score', 0)
        hr_score             = detailed.get('hr_score', 0)
        communication_score  = detailed.get('communication_score', 0)
        confidence_score     = detailed.get('confidence_score', 0)
        skill_gaps           = parse_json(detailed.get('skill_gaps', []), [])
        learning_resources   = parse_json(detailed.get('learning_resources', []), [])
        improvement_roadmap  = parse_json(detailed.get('improvement_roadmap', []), [])
        weak_question_types  = parse_json(detailed.get('weak_question_types', []), [])
        strong_question_types = parse_json(detailed.get('strong_question_types', []), [])

    return render_template('results.html',
        interview=interview_data,
        questions=questions,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions,
        overall_feedback=overall_feedback_text,
        technical_score=technical_score,
        hr_score=hr_score,
        communication_score=communication_score,
        confidence_score=confidence_score,
        skill_gaps=skill_gaps,
        learning_resources=learning_resources,
        improvement_roadmap=improvement_roadmap,
        weak_question_types=weak_question_types,
        strong_question_types=strong_question_types
    )

@app.route('/history')
@login_required
def history():
    interviews = get_user_interviews(session['user_id'])
    return render_template('history.html', interviews=interviews)

@app.route('/tracking')
def tracking():
    return render_template('tracking.html')

@app.route('/api/topics')
def get_topics():
    topics_path = os.path.join(os.path.dirname(__file__), 'datasets', 'topics.json')
    try:
        with open(topics_path, 'r', encoding='utf-8') as f:
            topics = json.load(f)
        return jsonify(topics)
    except FileNotFoundError:
        return jsonify([])
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format in datasets/topics.json'}), 500

@app.route('/dataset/<topic_id>')
@login_required
def view_dataset(topic_id):
    dataset_path = os.path.join(os.path.dirname(__file__), 'datasets', f"{topic_id.lower()}.json")
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
    except FileNotFoundError:
        flash(f"Dataset for '{topic_id}' not found.", 'error')
        return redirect(url_for('setup'))
    except json.JSONDecodeError:
        flash(f"Invalid dataset format for '{topic_id}'.", 'error')
        return redirect(url_for('setup'))
        
    return render_template('dataset.html', topic_id=topic_id.title().replace('_', ' '), questions=questions)

@app.route('/compiler')
@login_required
def compiler():
    import random
    
    # Check if user specifically clicked a single question from dataset side
    specific_q = request.args.get('q')
    specific_diff = request.args.get('diff', 'Technical')
    
    if specific_q:
        selected = [{'question': specific_q, 'difficulty': specific_diff}]
        return render_template('compiler.html', questions=selected)
        
    questions = []
    datasets_dir = os.path.join(os.path.dirname(__file__), 'datasets')
    topics = ['arrays', 'strings', 'dp', 'trees', 'graphs', 'sorting']
    for t in topics:
        try:
            with open(os.path.join(datasets_dir, f"{t}.json"), 'r', encoding='utf-8') as f:
                qs = json.load(f)
                questions.extend(qs)
        except Exception:
            continue
    random.shuffle(questions)
    selected = questions[:5] if questions else [{'question': 'Write a program to print Hello World', 'difficulty': 'Easy'}]
    return render_template('compiler.html', questions=selected)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=8000)
