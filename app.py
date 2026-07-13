import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from config import Config
from models import db, User, Resume, Analysis
from analyzer import extract_text, analyze_resume_ats, analyze_with_gemini

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Create database tables automatically
with app.app_context():
    db.create_all()


# --- Routes ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
            
        if User.query.filter_by(username=username).first():
            flash('Username is already taken.', 'danger')
            return render_template('register.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'danger')
            return render_template('register.html')
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email_or_user = request.form.get('email_or_user', '').strip()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter((User.email == email_or_user.lower()) | (User.username == email_or_user)).first()
        
        if not user or not user.check_password(password):
            flash('Invalid username/email or password.', 'danger')
            return render_template('login.html')
            
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard'))
        
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    user_resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).all()
    total_resumes = len(user_resumes)
    
    # Calculate statistics
    all_analyses = Analysis.query.join(Resume).filter(Resume.user_id == current_user.id).order_by(Analysis.created_at.desc()).all()
    
    if all_analyses:
        avg_score = round(sum(a.overall_score for a in all_analyses) / len(all_analyses))
        highest_score = max(a.overall_score for a in all_analyses)
    else:
        avg_score = 0
        highest_score = 0
        
    recent_analyses = all_analyses[:5]
    
    # Aggregate common missing skills
    missing_skills_count = {}
    for a in all_analyses:
        for sk in a.missing_skills:
            missing_skills_count[sk] = missing_skills_count.get(sk, 0) + 1
            
    sorted_missing_skills = sorted(missing_skills_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # For Chart.js progression chart (oldest to newest)
    chart_data = [{'date': a.created_at.strftime('%Y-%m-%d'), 'score': a.overall_score} for a in reversed(all_analyses)]

    return render_template(
        'dashboard.html',
        total_resumes=total_resumes,
        avg_score=avg_score,
        highest_score=highest_score,
        recent_analyses=recent_analyses,
        top_missing_skills=sorted_missing_skills,
        chart_data=chart_data
    )


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        job_title = request.form.get('job_title', '').strip()
        job_description = request.form.get('job_description', '').strip()
        
        if 'resume_file' not in request.files:
            flash('No resume file selected.', 'danger')
            return redirect(request.url)
            
        file = request.files['resume_file']
        if file.filename == '':
            flash('No resume file selected.', 'danger')
            return redirect(request.url)
            
        if not job_title or not job_description:
            flash('Job Title and Job Description are required.', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            orig_filename = secure_filename(file.filename)
            ext = orig_filename.rsplit('.', 1)[1].lower() if '.' in orig_filename else 'txt'
            unique_filename = f"{uuid.uuid4().hex}_{orig_filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(save_path)
            
            # Extract text
            extracted_txt = extract_text(save_path)
            
            # Save Resume model
            new_resume = Resume(
                user_id=current_user.id,
                filename=unique_filename,
                original_filename=orig_filename,
                file_path=save_path,
                file_type=ext,
                extracted_text=extracted_txt
            )
            db.session.add(new_resume)
            db.session.commit()
            
            # Analyze Resume against Job Description
            analysis_data = analyze_resume_ats(extracted_txt, job_description, job_title)
            
            # Call Gemini AI analysis
            api_key = app.config['GEMINI_API_KEY']
            ai_data = analyze_with_gemini(api_key, extracted_txt, job_description, job_title)
            
            new_analysis = Analysis(
                resume_id=new_resume.id,
                job_title=job_title,
                job_description=job_description,
                overall_score=analysis_data['overall_score'],
                skills_score=analysis_data['skills_score'],
                ats_score=analysis_data['ats_score'],
                cover_letter=ai_data.get('cover_letter', ''),
                job_fit_analysis=ai_data.get('job_fit_analysis', '')
            )
            new_analysis.matched_skills = analysis_data['matched_skills']
            new_analysis.missing_skills = analysis_data['missing_skills']
            new_analysis.formatting_feedback = analysis_data['formatting_feedback']
            new_analysis.ai_suggestions = ai_data.get('ai_suggestions', [])
            
            db.session.add(new_analysis)
            db.session.commit()
            
            flash('Resume uploaded & analyzed successfully with Gemini AI insights!', 'success')
            return redirect(url_for('report', analysis_id=new_analysis.id))
        else:
            flash('Invalid file format. Allowed formats: PDF, DOCX, TXT.', 'danger')
            return redirect(request.url)
            
    return render_template('upload.html')


@app.route('/resumes')
@login_required
def resume_list():
    resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).all()
    return render_template('resume_list.html', resumes=resumes)


@app.route('/report/<int:analysis_id>')
@login_required
def report(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    # Check authorization
    if analysis.resume.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))
        
    return render_template('report.html', analysis=analysis)


@app.route('/delete/<int:resume_id>', methods=['POST'])
@login_required
def delete_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        flash('Unauthorized operation.', 'danger')
        return redirect(url_for('resume_list'))
        
    # Remove physical file if exists
    if os.path.exists(resume.file_path):
        try:
            os.remove(resume.file_path)
        except Exception as e:
            print(f"Error deleting file {resume.file_path}: {e}")
            
    db.session.delete(resume)
    db.session.commit()
    flash('Resume deleted successfully.', 'success')
    return redirect(url_for('resume_list'))


@app.route('/resume-builder', methods=['GET', 'POST'])
@login_required
def resume_builder():
    if request.method == 'POST':
        # Read form inputs
        resume_data = {
            'name': request.form.get('name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'linkedin': request.form.get('linkedin', '').strip(),
            'github': request.form.get('github', '').strip(),
            'website': request.form.get('website', '').strip(),
            'summary': request.form.get('summary', '').strip(),
            'skills': [s.strip() for s in request.form.get('skills', '').split(',') if s.strip()],
            'experience': [],
            'education': [],
            'projects': []
        }
        
        # Parse experiences
        job_titles = request.form.getlist('job_title[]')
        companies = request.form.getlist('company[]')
        exp_dates = request.form.getlist('exp_dates[]')
        exp_descs = request.form.getlist('exp_desc[]')
        for i in range(len(job_titles)):
            if job_titles[i].strip():
                resume_data['experience'].append({
                    'title': job_titles[i].strip(),
                    'company': companies[i].strip() if i < len(companies) else '',
                    'dates': exp_dates[i].strip() if i < len(exp_dates) else '',
                    'desc': exp_descs[i].strip() if i < len(exp_descs) else ''
                })
                
        # Parse education
        degrees = request.form.getlist('degree[]')
        schools = request.form.getlist('school[]')
        edu_dates = request.form.getlist('edu_dates[]')
        for i in range(len(degrees)):
            if degrees[i].strip():
                resume_data['education'].append({
                    'degree': degrees[i].strip(),
                    'school': schools[i].strip() if i < len(schools) else '',
                    'dates': edu_dates[i].strip() if i < len(edu_dates) else ''
                })
                
        # Parse projects
        proj_names = request.form.getlist('project_name[]')
        proj_techs = request.form.getlist('project_tech[]')
        proj_descs = request.form.getlist('project_desc[]')
        for i in range(len(proj_names)):
            if proj_names[i].strip():
                resume_data['projects'].append({
                    'name': proj_names[i].strip(),
                    'tech': proj_techs[i].strip() if i < len(proj_techs) else '',
                    'desc': proj_descs[i].strip() if i < len(proj_descs) else ''
                })
                
        return render_template('resume_preview.html', resume=resume_data)
        
    return render_template('resume_builder.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
