from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from functools import wraps
import json
import os
import random
from pathlib import Path
from gtts import gTTS
import io
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Google Gemini API 설정 (선택적)
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GEMINI_API_KEY)
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: google-generativeai not installed. AI features will be disabled.")

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # 보안을 위해 변경하세요
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # 30일간 로그인 유지

# 사용자 파일 경로
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

def load_users():
    """JSON 파일에서 사용자 목록 로드"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 기존 단순 구조를 새 구조로 변환
                if data and isinstance(list(data.values())[0], str):
                    # 기존: {'username': 'password'}
                    # 새로운: {'username': {'password': 'xxx', 'progress': {...}}}
                    new_data = {}
                    for username, password in data.items():
                        new_data[username] = {
                            'password': password,
                            'progress': {
                                'Words': {
                                    'category': '전체', 
                                    'completed_count': 0, 
                                    'current_group_index': 0,
                                    'review_mode': False,
                                    'review_start_group': 0,
                                    'last_study_date': None
                                },
                                'ed': {
                                    'category': '전체', 
                                    'completed_count': 0, 
                                    'current_group_index': 0,
                                    'review_mode': False,
                                    'review_start_group': 0,
                                    'last_study_date': None
                                },
                                'numbers': {
                                    'category': '전체', 
                                    'completed_count': 0, 
                                    'current_group_index': 0,
                                    'review_mode': False,
                                    'review_start_group': 0,
                                    'last_study_date': None
                                }
                            }
                        }
                    save_users(new_data)
                    return new_data
                return data
        except:
            pass
    # 기본 계정 생성
    default_users = {
        'admin': {
            'password': 'password123',
            'progress': {
                'Words': {
                    'category': '전체', 
                    'completed_count': 0, 
                    'current_group_index': 0,  # 현재 학습 중인 묶음 번호
                    'review_mode': False,
                    'review_start_group': 0,
                    'last_study_date': None
                },
                'ed': {
                    'category': '전체', 
                    'completed_count': 0, 
                    'current_group_index': 0,
                    'review_mode': False,
                    'review_start_group': 0,
                    'last_study_date': None
                },
                'numbers': {
                    'category': '전체', 
                    'completed_count': 0, 
                    'current_group_index': 0,
                    'review_mode': False,
                    'review_start_group': 0,
                    'last_study_date': None
                }
            }
        }
    }
    save_users(default_users)
    return default_users

def save_users(users):
    """사용자 목록을 JSON 파일에 저장"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_user_progress(username, mode='Words'):
    """사용자의 진행 상황 가져오기"""
    users = load_users()
    if username in users:
        return users[username].get('progress', {}).get(mode, {
            'category': '전체', 
            'completed_count': 0, 
            'current_group_index': 0,
            'review_mode': False,
            'review_start_group': 0,
            'last_study_date': None
        })
    return {
        'category': '전체', 
        'completed_count': 0, 
        'current_group_index': 0,
        'review_mode': False,
        'review_start_group': 0,
        'last_study_date': None
    }

def save_user_progress(username, mode, progress_data):
    """사용자의 진행 상황 저장"""
    from datetime import datetime
    users = load_users()
    if username in users:
        if 'progress' not in users[username]:
            users[username]['progress'] = {}
        if mode not in users[username]['progress']:
            users[username]['progress'][mode] = {}
        
        users[username]['progress'][mode].update(progress_data)
        users[username]['progress'][mode]['last_study_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_users(users)

# 앱 시작시 사용자 목록 로드
USERS = load_users()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 데이터 파일 경로
DATA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'data')
WORDS_FILE = os.path.join(DATA_DIR, 'english_words.json')
ED_WORDS_FILE = os.path.join(DATA_DIR, 'english_words_ed.json')
YB_WORDS_FILE = os.path.join(DATA_DIR, 'english_words_yb_con.json')
NUMBERS_DATES_FILE = os.path.join(DATA_DIR, 'numbers_dates.json')

# 세션 데이터 저장소 (실제로는 데이터베이스 사용 권장)
sessions = {}

def load_words():
    """JSON에서 단어 로드"""
    if os.path.exists(WORDS_FILE):
        try:
            with open(WORDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return [{"word": "Apple", "meaning": "사과", "example": "I ate an apple.", "category": "기초"}]

def create_word_groups(words, group_size=3):
    """단어를 group_size개씩 묶음으로 만들고 번호 부여"""
    # 단어를 랜덤하게 섞기 (시드 고정으로 항상 같은 순서)
    import random
    random.seed(42)  # 고정된 시드로 항상 같은 순서로 섞임
    shuffled_words = words.copy()
    random.shuffle(shuffled_words)
    
    groups = []
    for i in range(0, len(shuffled_words), group_size):
        group_number = (i // group_size) + 1
        group_words = shuffled_words[i:i + group_size]
        # 나머지 단어도 포함 (최소 1개 이상이면 묶음에 추가)
        if len(group_words) >= 1:
            groups.append({
                'group_number': group_number,
                'words': group_words
            })
    return groups

def load_ed_words():
    """JSON에서 ed (Past Tense) 단어 로드"""
    if os.path.exists(ED_WORDS_FILE):
        try:
            with open(ED_WORDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return []

def load_yb_words():
    """JSON에서 YB 영한사전 단어 로드"""
    if os.path.exists(YB_WORDS_FILE):
        try:
            with open(YB_WORDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"YB 단어 로드 오류: {e}")
            pass
    return []

def load_numbers_dates():
    """JSON에서 숫자/날짜 단어 로드"""
    numbers_file = os.path.join(DATA_DIR, 'numbers_dates.json')
    if os.path.exists(numbers_file):
        try:
            with open(numbers_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"숫자/날짜 단어 로드 오류: {e}")
            pass
    return []

def save_words(words):
    """단어 JSON에 저장"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(WORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """로그인 처리"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    remember = data.get('remember', False)  # 로그인 상태 유지 옵션
    
    # users.json 파일 다시 로드 (변경사항 반영)
    users = load_users()
    
    if username in users:
        user_data = users[username]
        # 새 구조와 기존 구조 모두 지원
        user_password = user_data.get('password', user_data) if isinstance(user_data, dict) else user_data
        
        if user_password == password:
            session.permanent = remember  # 로그인 상태 유지 설정
            session['logged_in'] = True
            session['username'] = username
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': '아이디 또는 비밀번호가 올바르지 않습니다.'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/init', methods=['GET'])
@login_required
def api_init():
    """초기화 및 사용자 진행 상황에서 단어 로드"""
    username = session.get('username')
    words = load_words()
    categories = sorted(list(set(w.get('category', '기타') for w in words)))
    
    # 세션 ID 생성
    session_id = request.args.get('session_id', str(random.randint(100000, 999999)))
    
    # 사용자 진행 상황 로드
    progress = get_user_progress(username, 'Words')
    
    # 단어를 10개씩 묶음으로 생성
    word_groups = create_word_groups(words, 10)
    
    # 현재 학습할 묶음 인덱스
    current_group_idx = progress.get('current_group_index', 0)
    
    # 복습 모드는 제거 (틀린 단어만 반복하는 방식으로 변경)
    review_mode = False
    
    # 일반 모드: 현재 묶음 1개(10개 단어) 로드
    if current_group_idx < len(word_groups):
        current_group = word_groups[current_group_idx]
        all_nine_words = current_group['words']
        message = f"📖 {current_group_idx+1}번 묶음 학습 중"
    else:
        # 모든 단어 완료
        all_nine_words = []
        message = "🎉 모든 단어 학습 완료!"
    
    sessions[session_id] = {
        'all_nine_words': all_nine_words,
        'word_groups': word_groups,
        'repeat_count': 0,
        'correct_count': 0,
        'total_attempts': 0,
        'current_mode': 'Words',
        'current_group_index': current_group_idx,
        'review_mode': review_mode,
        'username': username,
        'incorrect_words': []  # 틀린 단어 추적
    }
    
    # 전체 9개 단어를 current_set으로 전송
    current_set = all_nine_words
    
    return jsonify({
        'session_id': session_id,
        'categories': categories,
        'current_set': current_set,
        'repeat_count': 0,
        'max_repeats': 3,
        'user_progress': progress,
        'message': message,
        'review_mode': review_mode,
        'current_group_index': current_group_idx,
        'total_words_count': len(words),
        'total_groups': len(word_groups)
    })

@app.route('/api/load-words-sheet', methods=['POST'])
@login_required
def load_words_sheet():
    """Words 탭 로드"""
    session_id = request.json.get('session_id')
    username = session.get('username')
    words = load_words()
    progress = get_user_progress(username, 'Words')
    
    # 단어 묶음 생성 (10개씩)
    word_groups = create_word_groups(words, 10)
    current_group_idx = progress.get('current_group_index', 0)
    
    # 범위를 벗어났으면 처음으로 돌아가기
    if current_group_idx >= len(word_groups):
        current_group_idx = 0
        progress['current_group_index'] = 0
        save_user_progress(username, 'Words', progress)
    
    # 현재 묶음 1개(10개 단어) 로드
    if current_group_idx < len(word_groups):
        current_group = word_groups[current_group_idx]
        all_nine_words = current_group['words']
        message = f"📖 {current_group_idx+1}번 묶음"
    else:
        all_nine_words = []
        message = "🎉 모든 단어 학습 완료!"
    
    if session_id in sessions:
        sessions[session_id]['all_nine_words'] = all_nine_words
        sessions[session_id]['repeat_count'] = 0
        sessions[session_id]['current_mode'] = 'Words'
        sessions[session_id]['correct_count'] = 0
        sessions[session_id]['total_attempts'] = 0
        sessions[session_id]['username'] = username
        sessions[session_id]['review_mode'] = False
        sessions[session_id]['current_group_index'] = current_group_idx
        sessions[session_id]['incorrect_words'] = []
    
    # 전체 9개 단어를 current_set으로 전송
    current_set = all_nine_words
    
    return jsonify({
        'current_set': current_set,
        'repeat_count': 0,
        'correct_count': 0,
        'total_attempts': 0,
        'user_progress': progress,
        'message': message,
        'review_mode': review_mode,
        'total_words_count': len(words),
        'current_group_index': current_group_idx,
        'total_groups': len(word_groups)
    })

@app.route('/api/load-ed-sheet', methods=['POST'])
@login_required
def load_ed_sheet():
    """ed (Past Tense) 탭 로드"""
    session_id = request.json.get('session_id')
    username = session.get('username')
    ed_words = load_ed_words()
    
    if not ed_words:
        return jsonify({'error': 'No ed words available'}), 404
    
    progress = get_user_progress(username, 'ed')
    
    # 단어 묶음 생성 (10개씩)
    word_groups = create_word_groups(ed_words, 10)
    current_group_idx = progress.get('current_group_index', 0)
    
    # 범위를 벗어났으면 처음으로 돌아가기
    if current_group_idx >= len(word_groups):
        current_group_idx = 0
        progress['current_group_index'] = 0
        save_user_progress(username, 'ed', progress)
    
    # 현재 묶음 1개(10개 단어) 로드
    if current_group_idx < len(word_groups):
        current_group = word_groups[current_group_idx]
        all_nine_words = current_group['words']
        message = f"📖 {current_group_idx+1}번 묶음"
    else:
        all_nine_words = []
        message = "🎉 모든 단어 학습 완료!"
    
    if session_id in sessions:
        sessions[session_id]['all_nine_words'] = all_nine_words
        sessions[session_id]['repeat_count'] = 0
        sessions[session_id]['current_mode'] = 'ed'
        sessions[session_id]['correct_count'] = 0
        sessions[session_id]['total_attempts'] = 0
        sessions[session_id]['username'] = username
        sessions[session_id]['review_mode'] = False
        sessions[session_id]['current_group_index'] = current_group_idx
        sessions[session_id]['incorrect_words'] = []
    
    # 전체 9개 단어를 current_set으로 전송
    current_set = all_nine_words
    
    return jsonify({
        'current_set': current_set,
        'repeat_count': 0,
        'correct_count': 0,
        'total_attempts': 0,
        'mode': 'ed',
        'user_progress': progress,
        'message': message,
        'review_mode': review_mode,
        'total_words_count': len(ed_words),
        'current_group_index': current_group_idx,
        'total_groups': len(word_groups)
    })

@app.route('/api/load-yb-sheet', methods=['POST'])
@login_required
def load_yb_sheet():
    """YB 영한사전 탭 로드"""
    session_id = request.json.get('session_id')
    username = session.get('username')
    yb_words = load_yb_words()
    
    if not yb_words:
        return jsonify({'error': 'No YB words available'}), 404
    
    progress = get_user_progress(username, 'yb')
    
    # 단어 묶음 생성
    word_groups = create_word_groups(yb_words, 10)
    current_group_idx = progress.get('current_group_index', 0)
    
    # 범위를 벗어났으면 처음으로 돌아가기
    if current_group_idx >= len(word_groups):
        current_group_idx = 0
        progress['current_group_index'] = 0
        save_user_progress(username, 'yb', progress)
    
    # 현재 묶음 1개(10개 단어) 로드
    if current_group_idx < len(word_groups):
        current_group = word_groups[current_group_idx]
        all_nine_words = current_group['words']
        message = f"📖 {current_group_idx+1}번 묶음 (10개 단어)\n총 {len(word_groups)}개 묶음 중 {current_group_idx+1}번째 학습"
    else:
        all_nine_words = []
        message = "🎉 모든 단어 학습 완료!"
    
    if session_id in sessions:
        sessions[session_id]['all_nine_words'] = all_nine_words
        sessions[session_id]['repeat_count'] = 0
        sessions[session_id]['current_mode'] = 'yb'
        sessions[session_id]['correct_count'] = 0
        sessions[session_id]['total_attempts'] = 0
        sessions[session_id]['username'] = username
        sessions[session_id]['review_mode'] = False
        sessions[session_id]['current_group_index'] = current_group_idx
        sessions[session_id]['incorrect_words'] = []
    
    # 전체 9개 단어를 current_set으로 전송
    current_set = all_nine_words
    
    return jsonify({
        'current_set': current_set,
        'repeat_count': 0,
        'correct_count': 0,
        'total_attempts': 0,
        'mode': 'yb',
        'user_progress': progress,
        'message': message,
        'review_mode': review_mode,
        'total_words_count': len(yb_words),
        'current_group_index': current_group_idx,
        'total_groups': len(word_groups)
    })

@app.route('/api/load-numbers-sheet', methods=['POST'])
@login_required
def load_numbers_sheet():
    """숫자/날짜 탭 로드"""
    session_id = request.json.get('session_id')
    username = session.get('username')
    numbers_words = load_numbers_dates()
    
    if not numbers_words:
        return jsonify({'error': 'No numbers/dates data available'}), 404
    
    progress = get_user_progress(username, 'numbers')
    
    # 단어 묶음 생성 (10개씩)
    word_groups = create_word_groups(numbers_words, 10)
    current_group_idx = progress.get('current_group_index', 0)
    
    # 범위를 벗어났으면 처음으로 돌아가기
    if current_group_idx >= len(word_groups):
        current_group_idx = 0
        progress['current_group_index'] = 0
        save_user_progress(username, 'numbers', progress)
    
    # 현재 묶음 1개(10개 단어) 로드
    if current_group_idx < len(word_groups):
        current_group = word_groups[current_group_idx]
        all_nine_words = current_group['words']
        message = f"📖 {current_group_idx+1}번 묶음 (10개 단어)\n총 {len(word_groups)}개 묶음 중 {current_group_idx+1}번째 학습"
    else:
        all_nine_words = []
        message = "🎉 모든 단어 학습 완료!"
    
    if session_id in sessions:
        sessions[session_id]['all_nine_words'] = all_nine_words
        sessions[session_id]['repeat_count'] = 0
        sessions[session_id]['current_mode'] = 'numbers'
        sessions[session_id]['correct_count'] = 0
        sessions[session_id]['total_attempts'] = 0
        sessions[session_id]['username'] = username
        sessions[session_id]['review_mode'] = False
        sessions[session_id]['current_group_index'] = current_group_idx
        sessions[session_id]['incorrect_words'] = []
    
    # 전체 9개 단어를 current_set으로 전송
    current_set = all_nine_words
    
    return jsonify({
        'current_set': current_set,
        'repeat_count': 0,
        'correct_count': 0,
        'total_attempts': 0,
        'mode': 'numbers',
        'user_progress': progress,
        'message': message,
        'review_mode': review_mode,
        'total_words_count': len(numbers_words),
        'current_group_index': current_group_idx,
        'total_groups': len(word_groups)
    })

@app.route('/api/check-answer', methods=['POST'])
@login_required
def check_answer():
    """답 확인 및 진행 상황 저장"""
    data = request.json
    session_id = data.get('session_id')
    user_input = data.get('user_input', '').lower().strip()
    word_data = data.get('word_data')
    mode = data.get('mode', 'Words')
    
    user_session = sessions.get(session_id)
    if not user_session:
        return jsonify({'error': 'Session not found'}), 404
    
    is_correct = False
    
    if mode == 'Words':
        is_correct = user_input == word_data['word'].lower()
    elif mode == 'ed':
        parts = user_input.split('/')
        if len(parts) == 2:
            is_correct = (parts[0].strip() == word_data.get('word', '').lower() and 
                         parts[1].strip() == word_data.get('past_tense', '').lower())
    elif mode == 'yb':
        is_correct = user_input == word_data['word'].lower()
    elif mode == 'numbers':
        is_correct = user_input == word_data['word'].lower()
    
    if is_correct:
        user_session['correct_count'] += 1
    else:
        # 틀린 단어 기록 (중복 방지)
        if 'incorrect_words' not in user_session:
            user_session['incorrect_words'] = []
        # word_data가 이미 incorrect_words에 없으면 추가
        already_exists = any(w.get('word') == word_data.get('word') for w in user_session['incorrect_words'])
        if not already_exists:
            user_session['incorrect_words'].append(word_data)
    user_session['total_attempts'] += 1
    
    # 사용자 진행 상황 저장
    username = user_session.get('username')
    if username and is_correct:
        progress = get_user_progress(username, mode)
        progress['completed_count'] = progress.get('completed_count', 0) + 1
        save_user_progress(username, mode, progress)
    
    accuracy = (user_session['correct_count'] / user_session['total_attempts'] * 100) if user_session['total_attempts'] > 0 else 0
    
    return jsonify({
        'is_correct': is_correct,
        'correct_count': user_session['correct_count'],
        'total_attempts': user_session['total_attempts'],
        'accuracy': round(accuracy, 1)
    })

@app.route('/api/next-word', methods=['POST'])
@login_required
def next_word():
    """다음 단어 또는 세트로 이동"""
    data = request.json
    session_id = data.get('session_id')
    current_index = data.get('current_index', 0)
    
    user_session = sessions.get(session_id)
    if not user_session:
        return jsonify({'error': 'Session not found'}), 404
    
    # 전체 단어 수 확인
    all_nine_words = user_session.get('all_nine_words', [])
    total_words = len(all_nine_words)
    
    print(f"DEBUG: current_index={current_index}, total_words={total_words}, all_nine_words length={len(all_nine_words)}")
    
    if total_words == 0:
        return jsonify({'error': 'No words in session', 'action': 'error'}), 400
    
    # 마지막 단어가 아니면 다음 단어로
    if current_index < total_words - 1:
        return jsonify({'action': 'next_word', 'index': current_index + 1})
    else:
        # 모든 단어 완료 - 10개 묶음 완료
        username = user_session.get('username')
        current_mode = user_session.get('current_mode', 'Words')
        
        # 틀린 단어가 있는지 확인
        incorrect_words = user_session.get('incorrect_words', [])
        
        if incorrect_words:
            # 틀린 단어만 반복
            user_session['all_nine_words'] = incorrect_words
            user_session['incorrect_words'] = []  # 초기화
            user_session['correct_count'] = 0
            user_session['total_attempts'] = 0
            return jsonify({
                'action': 'repeat_incorrect',
                'current_set': incorrect_words,
                'message': f'틀린 {len(incorrect_words)}개 단어를 다시 학습합니다.'
            })
        else:
            # 틀린 단어가 없으면 다음 묶음으로
            progress = get_user_progress(username, current_mode)
            new_group_index = progress.get('current_group_index', 0) + 1
            progress['current_group_index'] = new_group_index
            save_user_progress(username, current_mode, progress)
            
            # 다음 묶음 데이터 로드
            if current_mode == 'ed':
                words = load_ed_words()
            elif current_mode == 'yb':
                words = load_yb_words()
            elif current_mode == 'numbers':
                words = load_numbers_dates()
            else:
                words = load_words()
            
            word_groups = create_word_groups(words, 10)
            
            # 모든 묶음을 완료했는지 확인
            if new_group_index >= len(word_groups):
                new_group_index = 0
                progress['current_group_index'] = 0
                save_user_progress(username, current_mode, progress)
            
            # 다음 묶음 로드
            if new_group_index < len(word_groups):
                current_group = word_groups[new_group_index]
                all_nine_words = current_group['words']
                
                user_session['all_nine_words'] = all_nine_words
                user_session['current_group_index'] = new_group_index
                user_session['correct_count'] = 0
                user_session['total_attempts'] = 0
                user_session['incorrect_words'] = []
                
                return jsonify({
                    'action': 'next_set',
                    'current_set': all_nine_words,
                    'current_group_index': new_group_index,
                    'total_groups': len(word_groups),
                    'message': f'{new_group_index + 1}번 묶음으로 이동합니다.'
                })
            else:
                return jsonify({'action': 'set_complete', 'repeat_count': 0})

@app.route('/api/next-nine-words', methods=['POST'])
@login_required
def next_nine_words():
    """새로운 9개 단어로 이동 (다음 묶음)"""
    data = request.json
    session_id = data.get('session_id')
    mode = data.get('mode', 'Words')  # 클라이언트에서 모드 받기
    
    user_session = sessions.get(session_id)
    if not user_session:
        return jsonify({'error': 'Session not found'}), 404
    
    username = user_session.get('username')
    # 세션의 모드 업데이트
    user_session['current_mode'] = mode
    progress = get_user_progress(username, mode)
    
    # 모드에 따라 다른 파일 로드
    if mode == 'ed':
        words = load_ed_words()
    elif mode == 'yb':
        words = load_yb_words()
    elif mode == 'numbers':
        words = load_numbers_dates()
    else:
        words = load_words()
    
    # 10개씩 묶음
    word_groups = create_word_groups(words, 10)
    current_group_idx = progress.get('current_group_index', 0)
    
    # 모든 단어를 학습했으면 처음으로 돌아가기
    if current_group_idx >= len(word_groups):
        current_group_idx = 0
        progress['current_group_index'] = 0
        save_user_progress(username, mode, progress)
    
    if current_group_idx < len(word_groups):
        current_group = word_groups[current_group_idx]
        all_nine_words = current_group['words']
        
        user_session['all_nine_words'] = all_nine_words
        user_session['repeat_count'] = 0
        user_session['correct_count'] = 0
        user_session['total_attempts'] = 0
        user_session['current_group_index'] = current_group_idx
        user_session['incorrect_words'] = []
        
        # 전체 10개 단어를 current_set으로 전송
        current_set = all_nine_words
        
        completion_message = ""
        if current_group_idx == 0 and progress.get('completed_count', 0) > 0:
            completion_message = " (🎉 모든 단어 완료! 처음부터 다시 시작합니다)"
        
        return jsonify({
            'current_set': current_set,
            'repeat_count': 0,
            'message': f"{current_group_idx+1}번 묶음{completion_message}",
            'current_group_index': current_group_idx,
            'total_groups': len(word_groups)
        })
    else:
        return jsonify({'error': '단어 로드 실패'}), 404

def start_review_mode(session_id, username, mode):
    """복습 모드 시작"""
    # 모드에 따라 다른 파일 로드
    if mode == 'ed':
        words = load_ed_words()
    elif mode == 'yb':
        words = load_yb_words()
    elif mode == 'numbers':
        words = load_numbers_dates()
    else:
        words = load_words()
    
    word_groups = create_word_groups(words, 3)
    progress = get_user_progress(username, mode)
    
    review_start = progress.get('review_start_group', 0)
    review_groups = word_groups[review_start:review_start + 9]
    all_review_words = []
    for grp in review_groups:
        all_review_words.extend(grp['words'])
    
    # 27개 중 랜덤으로 섞기
    random.shuffle(all_review_words)
    all_nine_words = all_review_words[:27] if len(all_review_words) >= 27 else all_review_words
    
    user_session = sessions[session_id]
    user_session['all_nine_words'] = all_nine_words
    user_session['repeat_count'] = 0
    user_session['correct_count'] = 0
    user_session['total_attempts'] = 0
    user_session['review_mode'] = True
    
    # 복습 모드에서는 전체 27개 단어를 한 번에 전송
    current_set = all_nine_words
    
    return jsonify({
        'current_set': current_set,
        'repeat_count': 0,
        'review_mode': True,
        'message': f"📚 복습 모드: {review_start+1}~{review_start+9}번 묶음 27문제"
    })

@app.route('/api/start_review', methods=['POST'])
@login_required
def api_start_review():
    """복습 모드 시작 API"""
    data = request.json
    session_id = data.get('session_id')
    mode = data.get('mode', 'Words')
    username = session.get('username')
    
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    return start_review_mode(session_id, username, mode)

@app.route('/api/skip_review', methods=['POST'])
@login_required
def api_skip_review():
    """복습 건너뛰고 다음 9개 묶음으로"""
    data = request.json
    session_id = data.get('session_id')
    mode = data.get('mode', 'Words')
    username = session.get('username')
    
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    # 현재 그룹 인덱스를 9 증가시켜 복습 영역을 건너뜀
    progress = get_user_progress(username, mode)
    current_group = progress.get('current_group_index', 0)
    new_group_index = current_group + 9
    
    # 진행상황 업데이트
    progress['current_group_index'] = new_group_index
    progress['review_mode'] = False
    save_user_progress(username, mode, progress)
    
    # 새로운 9개 묶음 로드
    if mode == 'ed':
        words = load_ed_words()
    elif mode == 'yb':
        words = load_yb_words()
    elif mode == 'numbers':
        words = load_numbers_dates()
    else:
        words = load_words()
    
    word_groups = create_word_groups(words, 3)
    
    if new_group_index >= len(word_groups):
        return jsonify({
            'action': 'all_complete',
            'message': '🎉 모든 단어를 완료했습니다!'
        })
    
    # 새로운 9개 묶음
    nine_groups = word_groups[new_group_index:new_group_index + 9]
    all_nine_words = []
    for grp in nine_groups:
        all_nine_words.extend(grp['words'])
    
    random.shuffle(all_nine_words)
    
    user_session = sessions[session_id]
    user_session['all_nine_words'] = all_nine_words
    user_session['repeat_count'] = 0
    user_session['correct_count'] = 0
    user_session['total_attempts'] = 0
    user_session['review_mode'] = False
    
    return jsonify({
        'current_set': all_nine_words,
        'repeat_count': 0,
        'review_mode': False,
        'message': f'새로운 단어로 이동했습니다! ({new_group_index+1}번째 묶음)'
    })

@app.route('/api/repeat-nine-words', methods=['POST'])
@login_required
def repeat_nine_words():
    """같은 10개 단어 반복"""
    data = request.json
    session_id = data.get('session_id')
    
    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    session['repeat_count'] = 0
    session['correct_count'] = 0
    session['total_attempts'] = 0
    session['incorrect_words'] = []
    
    # 전체 10개 단어 반환
    current_set = session['all_nine_words']
    
    return jsonify({
        'current_set': current_set,
        'repeat_count': 0,
        'correct_count': 0,
        'total_attempts': 0
    })

@app.route('/api/play-audio', methods=['GET'])
@login_required
def play_audio():
    """단어 발음 생성"""
    word = request.args.get('word', '')
    
    try:
        tts = gTTS(text=word, lang='en')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        return send_file(
            audio_fp,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'{word}.mp3'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-word', methods=['POST'])
@login_required
def add_word():
    """단어 추가"""
    data = request.json
    word = data.get('word', '').strip()
    meaning = data.get('meaning', '').strip()
    
    if not word or not meaning:
        return jsonify({'error': 'Word and meaning are required'}), 400
    
    words = load_words()
    words.append({
        'word': word,
        'meaning': meaning,
        'example': '',
        'category': '기타'
    })
    save_words(words)
    
    return jsonify({'success': True, 'message': '단어가 추가되었습니다.'})

@app.route('/api/delete-word', methods=['POST'])
@login_required
def delete_word():
    """단어 삭제"""
    data = request.json
    word = data.get('word', '').strip()
    
    words = load_words()
    words = [w for w in words if w['word'].lower() != word.lower()]
    save_words(words)
    
    return jsonify({'success': True, 'message': '단어가 삭제되었습니다.'})

@app.route('/api/get-words', methods=['GET'])
@login_required
def get_words():
    """모든 단어 조회"""
    words = load_words()
    return jsonify(words)

@app.route('/api/get-categories', methods=['GET'])
@login_required
def get_categories():
    """카테고리 조회"""
    words = load_words()
    categories = sorted(list(set(w.get('category', '기타') for w in words)))
    return jsonify(categories)

@app.route('/api/ai-generate-sentences', methods=['POST'])
@login_required
def ai_generate_sentences():
    """AI로 단어를 사용한 예문 생성"""
    if not AI_AVAILABLE:
        return jsonify({'success': False, 'error': 'AI 기능을 사용할 수 없습니다. google-generativeai 패키지를 설치해주세요.'}), 503
    
    data = request.json
    word = data.get('word', '')
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        prompt = f"""단어 '{word}'를 사용해서 쉬운 영어 문장 3개를 만들어주세요.
각 문장 아래에 한국어 번역도 함께 적어주세요.
형식:
1. [영어 문장]
   (한국어 번역)
2. [영어 문장]
   (한국어 번역)
3. [영어 문장]
   (한국어 번역)"""
        
        response = model.generate_content(prompt)
        return jsonify({'success': True, 'sentences': response.text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-check-sentence', methods=['POST'])
@login_required
def ai_check_sentence():
    """AI로 사용자가 만든 문장 평가"""
    if not AI_AVAILABLE:
        return jsonify({'success': False, 'error': 'AI 기능을 사용할 수 없습니다. google-generativeai 패키지를 설치해주세요.'}), 503
    
    data = request.json
    word = data.get('word', '')
    user_sentence = data.get('sentence', '')
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        prompt = f"""학생이 단어 '{word}'를 사용해서 다음 문장을 만들었습니다:
"{user_sentence}"

이 문장을 평가해주세요:
1. 문법적으로 올바른가요? (O/X)
2. 단어를 올바르게 사용했나요? (O/X)
3. 더 자연스러운 표현이 있다면 제안해주세요.
4. 좋은 점을 칭찬해주세요.

친절하고 격려하는 톤으로 답변해주세요."""
        
        response = model.generate_content(prompt)
        return jsonify({'success': True, 'feedback': response.text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
