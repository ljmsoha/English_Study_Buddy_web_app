// 전역 변수
let sessionId = '';
let currentIndex = 0;
let currentSet = [];
let currentMode = 'Words';
let allWords = [];
let totalWordsCount = 0;
let currentGroupIndex = 0;

// 초기화
document.addEventListener('DOMContentLoaded', async () => {
    await initApp();
    document.getElementById('answerInput').focus();
    document.addEventListener('keydown', (e) => {
        if (e.key === '`') {
            e.preventDefault();
            playAudio();
        }
    });
});

async function initApp() {
    try {
        const response = await fetch('/api/init');
        const data = await response.json();
        
        sessionId = data.session_id;
        currentSet = data.current_set;
        allWords = data.categories;
        totalWordsCount = data.total_words_count || 0;
        currentGroupIndex = data.current_group_index || 0;
        document.getElementById('totalWords').textContent = `총: ${totalWordsCount}개`;
        
        // 카테고리 채우기
        const categorySelect = document.getElementById('categorySelect');
        data.categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat;
            categorySelect.appendChild(option);
        });
        
        // 사용자 진행 상황 표시
        if (data.user_progress) {
            showUserProgress(data.user_progress, data.message, data.review_mode);
        }
        
        displayWord();
        updateStats();
    } catch (error) {
        console.error('초기화 실패:', error);
        alert('앱 초기화에 실패했습니다.');
    }
}

function showUserProgress(progress, message, reviewMode) {
    let displayMsg = message || '';
    
    if (progress && progress.completed_count > 0) {
        displayMsg += `\n\n현재까지 ${progress.completed_count}개의 단어를 학습하셨습니다.`;
    }
    
    if (reviewMode) {
        displayMsg += '\n\n📚 복습 모드입니다!';
    }
    
    if (displayMsg) {
        console.log(displayMsg);
        // 필요하면 alert로 변경 가능: alert(displayMsg);
    }
}

function displayWord() {
    if (!currentSet || currentSet.length === 0) {
        console.error('currentSet이 비어있습니다.');
        return;
    }
    
    if (currentIndex >= currentSet.length) {
        console.error(`currentIndex(${currentIndex})가 범위를 벗어났습니다. currentSet.length=${currentSet.length}`);
        return;
    }
    
    const word = currentSet[currentIndex];
    console.log('displayWord:', {currentMode, currentIndex, word});
    
    const meaningDisplay = document.getElementById('meaningDisplay');
    
    let displayText = word.meaning;
    
    // YB 모드는 의미를 40자로 제한
    if (currentMode === 'yb' && displayText && displayText.length > 40) {
        displayText = displayText.substring(0, 37) + '...';
    }
    
    meaningDisplay.textContent = displayText;
    
    document.getElementById('answerInput').value = '';
    document.getElementById('answerInput').focus();
    document.getElementById('resultMessage').textContent = '';
    document.getElementById('resultMessage').className = 'result-message';
    
    updateStats();
}

function updateStats() {
    const totalWords = currentSet.length;
    const currentSetNum = Math.floor(currentIndex / 10) + 1;
    const totalSets = Math.ceil(totalWords / 10);
    
    // 절대 위치 계산: (현재 묶음 시작 위치) + (현재 인덱스) + 1
    const absolutePosition = currentGroupIndex + currentIndex + 1;
    
    document.getElementById('wordStats').textContent = `단어: ${currentIndex + 1}/${totalWords}`;
    document.getElementById('setStats').textContent = `묶음: ${currentSetNum}/${totalSets}`;
}

async function checkAnswer() {
    const input = document.getElementById('answerInput').value.trim();
    if (!input) return;
    
    const word = currentSet[currentIndex];
    
    try {
        const response = await fetch('/api/check-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                user_input: input,
                word_data: word,
                mode: currentMode
            })
        });
        
        const data = await response.json();
        const resultDiv = document.getElementById('resultMessage');
        
        // 정확도 업데이트
        if (data.accuracy !== undefined) {
            document.getElementById('accuracyStats').textContent = `정확도: ${data.accuracy}%`;
        }
        
        if (data.is_correct) {
            if (currentMode === 'ed') {
                resultDiv.innerHTML = `✅ 정답: ${word.word} → ${word.past_tense}<br><br><span style="color: #666; font-size: 13px;">👉 Enter를 눌러 다음 단어로 이동</span>`;
            } else if (currentMode === 'yb') {
                resultDiv.innerHTML = `✅ 정답: <strong>${word.word}</strong><br><br><span style="color: #666; font-size: 13px;">👉 Enter를 눌러 다음 단어로 이동</span>`;
            } else {
                // 단어를 두껍게 표시
                const exampleWithBold = word.example ? word.example.replace(new RegExp(`\\b${word.word}\\b`, 'gi'), `<strong>$&</strong>`) : '';
                const meaningWithBold = word.meaning ? word.meaning.replace(new RegExp(`\\b${word.word}\\b`, 'gi'), `<strong>$&</strong>`) : word.meaning;
                
                // 예문 한글 번역 추가 (example_kr 필드가 있으면 사용)
                const exampleKorean = word.example_kr ? `<br><span style="color: #666; font-size: 14px; margin-left: 20px;">→ ${word.example_kr}</span>` : '';
                
                resultDiv.innerHTML = `✅ 정답: <strong>${word.word}</strong><br><br>
                    📝 예문: ${exampleWithBold}${exampleKorean}<br>
                    💡 뜻: ${meaningWithBold}<br><br>
                    <span style="color: #666; font-size: 13px;">👉 Enter를 눌러 다음 단어로 이동</span>`;
            }
            resultDiv.className = 'result-message correct';
            playAudio();
            
            // Enter 키로 다음 단어로 이동하도록 설정
            document.getElementById('answerInput').value = '';
            document.getElementById('answerInput').dataset.correctAnswer = 'true';
        } else {
            if (currentMode === 'ed') {
                resultDiv.textContent = `❌ 오답! 정답: ${word.word} → ${word.past_tense}`;
            } else if (currentMode === 'yb') {
                resultDiv.textContent = `❌ 오답! 정답: ${word.word}`;
            } else {
                resultDiv.textContent = `❌ 오답! 정답: ${word.word}`;
            }
            resultDiv.className = 'result-message incorrect';
            playAudio();
        }
        
        updateStats();
    } catch (error) {
        console.error('답 확인 실패:', error);
    }
}

async function nextWord() {
    try {
        const response = await fetch('/api/next-word', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                current_index: currentIndex
            })
        });
        
        const data = await response.json();
        
        if (data.action === 'next_word') {
            currentIndex = data.index;
            displayWord();
        } else if (data.action === 'next_set') {
            currentSet = data.current_set;
            currentIndex = 0;
            displayWord();
        } else if (data.action === 'repeat_incorrect') {
            // 틀린 단어만 반복
            alert(data.message);
            currentSet = data.current_set;
            currentIndex = 0;
            displayWord();
            updateStats();
        } else if (data.action === 'set_complete') {
            alert('10개 단어를 모두 성공적으로 완료했습니다! 다음 묶음으로 이동합니다.');
            location.reload(); // 다음 묶음 로드
        } else if (data.action === 'enter_review') {
            // 복습 모드 진입
            const enterReview = confirm(data.message + '\n\n확인: 복습 시작\n취소: 다음 단어로');
            if (enterReview) {
                // 복습 시작 API 호출
                const reviewResponse = await fetch('/api/start_review', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId, mode: currentMode })
                });
                const reviewData = await reviewResponse.json();
                currentSet = reviewData.current_set;
                currentIndex = 0;
                displayWord();
                updateStats();
            } else {
                // 다음 10개 단어로 스킵
                const skipResponse = await fetch('/api/skip_review', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId, mode: currentMode })
                });
                const skipData = await skipResponse.json();
                currentSet = skipData.current_set;
                currentIndex = 0;
                displayWord();
                updateStats();
            }
        } else if (data.action === 'review_complete') {
            alert(data.message);
            location.reload(); // 페이지 새로고쳨으로 다음 묶음 로드
        }
    } catch (error) {
        console.error('다음 단어 실패:', error);
    }
}

function prevWord() {
    if (currentIndex > 0) {
        currentIndex--;
        displayWord();
    }
}

async function playAudio() {
    const word = currentSet[currentIndex];
    if (!word || !word.word) {
        console.error('단어 데이터가 없습니다.');
        return;
    }
    try {
        const audio = new Audio(`/api/play-audio?word=${encodeURIComponent(word.word)}`);
        audio.play();
    } catch (error) {
        console.error('음성 재생 실패:', error);
        alert(`발음: ${word.word}`);
    }
}

function googleTranslate() {
    const word = currentSet[currentIndex];
    if (!word || !word.word) {
        console.error('단어 데이터가 없습니다.');
        return;
    }
    const translateUrl = `https://translate.google.com/?sl=en&tl=ko&text=${encodeURIComponent(word.word)}`;
    window.open(translateUrl, '_blank');
}

function showHint() {
    const word = currentSet[currentIndex];
    const hintText = `[예문]\n${word.example || '없음'}\n\n[첫 글자]\n${word.word[0]}...`;
    document.getElementById('hintText').textContent = hintText;
    document.getElementById('hintModal').style.display = 'block';
}

function closeHintModal() {
    document.getElementById('hintModal').style.display = 'none';
}

function showSetCompleteDialog() {
    const result = confirm(
        '총 10개 단어를 완료했습니다.\n\n' +
        '확인: 같은 10개 단어를 다시 반복\n' +
        '취소: 새로운 10개 단어로 이동'
    );
    
    if (result) {
        repeatNineWords();
    } else {
        nextNineWords();
    }
}

async function loadWordsSheet() {
    try {
        const response = await fetch('/api/load-words-sheet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        currentSet = data.current_set;
        currentIndex = 0;
        currentMode = 'Words';
        
        // 총 단어 수 업데이트
        if (data.total_words_count !== undefined) {
            totalWordsCount = data.total_words_count;
            document.getElementById('totalWords').textContent = `총: ${totalWordsCount}개`;
        }
        
        // 현재 묶음 인덱스 업데이트
        if (data.current_group_index !== undefined) {
            currentGroupIndex = data.current_group_index;
        }
        
        // 활성 탭 표시
        setActiveTab('wordsTabBtn');
        
        // AI 섹션 숨김, 일반 섹션 표시
        document.getElementById('aiSection').style.display = 'none';
        document.getElementById('normalInputSection').style.display = 'flex';
        document.querySelector('.button-section').style.display = 'flex';
        document.querySelector('.result-message').style.display = 'block';
        
        displayWord();
        updateStats();
        
        let message = '📘 Words 탭을 로드했습니다.\n원형을 입력해주세요.';
        if (data.message) {
            message += '\n\n' + data.message;
        }
        if (data.user_progress && data.user_progress.completed_count > 0) {
            message += `\n현재까지 ${data.user_progress.completed_count}개 학습 완료!`;
        }
        if (data.review_mode) {
            message += '\n\n📚 복습 모드입니다!';
        }
        alert(message);
    } catch (error) {
        console.error('Words 탭 로드 실패:', error);
    }
}

async function loadEdSheet() {
    try {
        const response = await fetch('/api/load-ed-sheet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        console.log('loadEdSheet response:', data);
        
        currentSet = data.current_set;
        currentIndex = 0;
        currentMode = 'ed';
        
        console.log('After setting:', {currentSet, currentIndex, currentMode});
        
        // 총 단어 수 업데이트
        if (data.total_words_count !== undefined) {
            totalWordsCount = data.total_words_count;
            document.getElementById('totalWords').textContent = `총: ${totalWordsCount}개`;
        }
        
        // 현재 묶음 인덱스 업데이트
        if (data.current_group_index !== undefined) {
            currentGroupIndex = data.current_group_index;
        }
        
        // 활성 탭 표시
        setActiveTab('edTabBtn');
        
        // AI 섹션 숨김, 일반 섹션 표시
        document.getElementById('aiSection').style.display = 'none';
        document.getElementById('normalInputSection').style.display = 'flex';
        document.querySelector('.button-section').style.display = 'flex';
        document.querySelector('.result-message').style.display = 'block';
        
        displayWord();
        updateStats();
        
        let message = '⏰ Past Tense 탭을 로드했습니다.\n원형과 과거형을 / 로 구분해서 입력해주세요.\n예: arrive/arrived';
        if (data.message) {
            message += '\n\n' + data.message;
        }
        if (data.user_progress && data.user_progress.completed_count > 0) {
            message += `\n현재까지 ${data.user_progress.completed_count}개 학습 완료!`;
        }
        if (data.review_mode) {
            message += '\n\n📚 복습 모드입니다!';
        }
        alert(message);
    } catch (error) {
        console.error('ed 탭 로드 실패:', error);
    }
}

async function loadYbSheet() {
    try {
        const response = await fetch('/api/load-yb-sheet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        currentSet = data.current_set;
        currentIndex = 0;
        currentMode = 'yb';
        
        // 총 단어 수 업데이트
        if (data.total_words_count !== undefined) {
            totalWordsCount = data.total_words_count;
            document.getElementById('totalWords').textContent = `총: ${totalWordsCount}개`;
        }
        
        // 현재 묶음 인덱스 업데이트
        if (data.current_group_index !== undefined) {
            currentGroupIndex = data.current_group_index;
        }
        
        // 활성 탭 표시
        setActiveTab('ybTabBtn');
        
        // AI 섹션 숨김, 일반 섹션 표시
        document.getElementById('aiSection').style.display = 'none';
        document.getElementById('normalInputSection').style.display = 'flex';
        document.querySelector('.button-section').style.display = 'flex';
        document.querySelector('.result-message').style.display = 'block';
        
        displayWord();
        updateStats();
        
        let message = '📚 YB 영한사전 탭을 로드했습니다.\n2,046개의 단어가 포함되어 있습니다.\n영어 단어를 입력해주세요.';
        if (data.message) {
            message += '\n\n' + data.message;
        }
        if (data.user_progress && data.user_progress.completed_count > 0) {
            message += `\n현재까지 ${data.user_progress.completed_count}개 학습 완료!`;
        }
        if (data.review_mode) {
            message += '\n\n📚 복습 모드입니다!';
        }
        alert(message);
    } catch (error) {
        console.error('yb 탭 로드 실패:', error);
    }
}

async function loadNumbersSheet() {
    try {
        const response = await fetch('/api/load-numbers-sheet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        currentSet = data.current_set;
        currentIndex = 0;
        currentMode = 'numbers';
        
        // 총 단어 수 업데이트
        if (data.total_words_count !== undefined) {
            totalWordsCount = data.total_words_count;
            document.getElementById('totalWords').textContent = `총: ${totalWordsCount}개`;
        }
        
        // 현재 묶음 인덱스 업데이트
        if (data.current_group_index !== undefined) {
            currentGroupIndex = data.current_group_index;
        }
        
        // 활성 탭 표시
        setActiveTab('numbersTabBtn');
        
        // AI 섹션 숨김, 일반 섹션 표시
        document.getElementById('aiSection').style.display = 'none';
        document.getElementById('normalInputSection').style.display = 'flex';
        document.querySelector('.button-section').style.display = 'flex';
        document.querySelector('.result-message').style.display = 'block';
        
        displayWord();
        updateStats();
        
        let message = '🔢 숫자/날짜 탭을 로드했습니다.\n계절, 월, 날짜, 숫자를 학습합니다.\n영어 단어를 입력해주세요.';
        if (data.message) {
            message += '\n\n' + data.message;
        }
        if (data.user_progress && data.user_progress.completed_count > 0) {
            message += `\n현재까지 ${data.user_progress.completed_count}개 학습 완료!`;
        }
        if (data.review_mode) {
            message += '\n\n📚 복습 모드입니다!';
        }
        alert(message);
    } catch (error) {
        console.error('숫자 탭 로드 실패:', error);
    }
}

async function nextNineWords() {
    try {
        const category = document.getElementById('categorySelect').value;
        const response = await fetch('/api/next-nine-words', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                category: category,
                mode: currentMode  // 현재 모드 전달
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        currentSet = data.current_set;
        currentIndex = 0;
        
        // currentGroupIndex 업데이트
        if (data.current_group_index !== undefined) {
            currentGroupIndex = data.current_group_index;
            console.log(`nextNineWords: currentGroupIndex updated to ${currentGroupIndex}`);
        } else {
            console.warn('nextNineWords: current_group_index not in response!');
        }
        
        console.log(`Before display - currentGroupIndex: ${currentGroupIndex}, currentIndex: ${currentIndex}`);
        
        displayWord();
        updateStats();
        
        // 메시지 표시
        if (data.message) {
            console.log(data.message);
        }
        if (data.review_mode) {
            alert('📚 복습 모드를 시작합니다!\n' + (data.message || ''));
        }
    } catch (error) {
        console.error('새로운 9개 단어 로드 실패:', error);
        alert('다음 단어 로드에 실패했습니다: ' + error.message);
    }
}

async function repeatNineWords() {
    try {
        const response = await fetch('/api/repeat-nine-words', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        currentSet = data.current_set;
        currentIndex = 0;
        displayWord();
    } catch (error) {
        console.error('10개 단어 반복 실패:', error);
    }
}

function addWordDialog() {
    const word = prompt('영어 단어를 입력하세요:');
    if (!word) return;
    
    const meaning = prompt('뜻을 입력하세요:');
    if (!meaning) return;
    
    addWord(word, meaning);
}

async function addWord(word, meaning) {
    try {
        const response = await fetch('/api/add-word', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word: word,
                meaning: meaning
            })
        });
        
        const data = await response.json();
        alert(data.message || '단어가 추가되었습니다.');
    } catch (error) {
        console.error('단어 추가 실패:', error);
        alert('단어 추가에 실패했습니다.');
    }
}

function deleteWordDialog() {
    const word = currentSet[currentIndex];
    const confirmed = confirm(`'${word.word}'를 삭제할까요?`);
    
    if (confirmed) {
        deleteWord(word.word);
    }
}

async function deleteWord(word) {
    try {
        const response = await fetch('/api/delete-word', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word: word })
        });
        
        const data = await response.json();
        alert(data.message || '단어가 삭제되었습니다.');
        nextWord();
    } catch (error) {
        console.error('단어 삭제 실패:', error);
        alert('단어 삭제에 실패했습니다.');
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        const input = document.getElementById('answerInput');
        
        // 정답을 맞춘 상태에서 Enter를 누르면 다음 단어로
        if (input.dataset.correctAnswer === 'true') {
            input.dataset.correctAnswer = 'false';
            nextWord();
        } else {
            // 일반 상태에서는 답안 체크
            checkAnswer();
        }
    }
}

// 활성 탭 설정
function setActiveTab(activeTabId) {
    // 모든 탭 버튼에서 active-tab 클래스 제거
    document.getElementById('wordsTabBtn').classList.remove('active-tab');
    document.getElementById('edTabBtn').classList.remove('active-tab');
    document.getElementById('ybTabBtn').classList.remove('active-tab');
    document.getElementById('numbersTabBtn').classList.remove('active-tab');
    document.getElementById('aiTabBtn').classList.remove('active-tab');
    
    // 선택된 탭에 active-tab 클래스 추가
    document.getElementById(activeTabId).classList.add('active-tab');
}

// AI 탭 로드
async function loadAiTab() {
    try {
        // AI 탭 활성화
        setActiveTab('aiTabBtn');
        
        // AI 섹션 표시, 일반 섹션 숨김
        document.getElementById('aiSection').style.display = 'block';
        document.getElementById('normalInputSection').style.display = 'none';
        document.querySelector('.button-section').style.display = 'none';
        document.querySelector('.result-message').style.display = 'none';
        
        // Words 단어 로드
        const response = await fetch('/api/init');
        const data = await response.json();
        currentSet = data.current_set;
        currentIndex = 0;
        currentMode = 'ai';
        
        // 첫 단어 표시
        displayAiWord();
        
        alert('🤖 AI 탭을 로드했습니다.\n단어를 사용해서 문장을 만들고 AI의 평가를 받아보세요!');
    } catch (error) {
        console.error('AI 탭 로드 실패:', error);
    }
}

function displayAiWord() {
    if (!currentSet || currentSet.length === 0) return;
    
    const word = currentSet[currentIndex];
    document.getElementById('aiWord').textContent = `${word.word} (${word.meaning})`;
    document.getElementById('aiSentences').textContent = '';
    document.getElementById('aiFeedback').textContent = '';
    document.getElementById('userSentence').value = '';
}

async function generateAiSentences() {
    const word = currentSet[currentIndex];
    const sentencesDiv = document.getElementById('aiSentences');
    sentencesDiv.textContent = '🤖 AI가 예문을 생성하고 있습니다...';
    
    try {
        const response = await fetch('/api/ai-generate-sentences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word: word.word })
        });
        
        const data = await response.json();
        if (data.success) {
            sentencesDiv.textContent = data.sentences;
        } else {
            sentencesDiv.textContent = '❌ 오류: ' + data.error;
        }
    } catch (error) {
        console.error('AI 예문 생성 실패:', error);
        sentencesDiv.textContent = '❌ AI 예문 생성에 실패했습니다.';
    }
}

async function checkUserSentence() {
    const word = currentSet[currentIndex];
    const userSentence = document.getElementById('userSentence').value.trim();
    const feedbackDiv = document.getElementById('aiFeedback');
    
    if (!userSentence) {
        alert('문장을 입력해주세요!');
        return;
    }
    
    feedbackDiv.textContent = '🤖 AI가 평가하고 있습니다...';
    
    try {
        const response = await fetch('/api/ai-check-sentence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                word: word.word,
                sentence: userSentence 
            })
        });
        
        const data = await response.json();
        if (data.success) {
            feedbackDiv.textContent = data.feedback;
        } else {
            feedbackDiv.textContent = '❌ 오류: ' + data.error;
        }
    } catch (error) {
        console.error('AI 평가 실패:', error);
        feedbackDiv.textContent = '❌ AI 평가에 실패했습니다.';
    }
}

// AI 탭에서 다음 단어로 이동
function nextAiWord() {
    console.log('nextAiWord 호출됨. currentIndex:', currentIndex, 'currentSet.length:', currentSet.length);
    
    if (!currentSet || currentSet.length === 0) {
        alert('단어 목록이 없습니다. AI 탭을 다시 로드해주세요.');
        return;
    }
    
    // 현재 인덱스 증가
    currentIndex = (currentIndex + 1) % currentSet.length;
    console.log('새로운 currentIndex:', currentIndex);
    
    // 새 단어 표시
    displayAiWord();
    
    // 입력창과 피드백 초기화
    document.getElementById('userSentence').value = '';
    document.getElementById('aiSentences').textContent = '';
    document.getElementById('aiFeedback').textContent = '';
}

// 모달 외부 클릭 시 닫기
window.onclick = function(event) {
    const modal = document.getElementById('hintModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

