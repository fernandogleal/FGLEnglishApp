let currentCard = null;
let mediaRecorder = null;
let audioChunks = [];
let currentRecordingType = null; // 'formal' or 'informal'
let currentAudioBlob = null;
let currentUser = null;

// User Management
function initUser() {
    currentUser = localStorage.getItem('fgl_username');
    if (!currentUser) {
        while (!currentUser) {
            currentUser = prompt("Please enter your username:");
        }
        localStorage.setItem('fgl_username', currentUser);
    }
    updateUserDisplay();
    
    document.getElementById('user-display').addEventListener('click', () => {
        const newUser = prompt("Switch user (enter username):", currentUser);
        if (newUser && newUser !== currentUser) {
            currentUser = newUser;
            localStorage.setItem('fgl_username', currentUser);
            updateUserDisplay();
            loadCard(); // Reload for new user
        }
    });
}

function updateUserDisplay() {
    const display = document.getElementById('user-display');
    if (display) {
        display.textContent = `👤 ${currentUser}`;
    }
}

// Theme Management
function initTheme() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;

    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });
}

function updateThemeIcon(theme) {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initUser();
    
    const levelSelect = document.getElementById('level-select');
    if (levelSelect) {
        loadLevels();
        loadCard();
        levelSelect.addEventListener('change', loadCard);
        // document.getElementById('btn-repeat').addEventListener('click', loadCard);
        document.getElementById('btn-known').addEventListener('click', markKnown);
    }
});

async function loadLevels() {
    try {
        const response = await fetch('/api/levels');
        const levels = await response.json();
        const select = document.getElementById('level-select');
        
        levels.forEach(level => {
            const option = document.createElement('option');
            option.value = level;
            option.textContent = level.toUpperCase();
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading levels:', error);
    }
}

async function loadCard() {
    const level = document.getElementById('level-select').value;
    resetUI();

    try {
        const response = await fetch(`/api/card?level=${level}&username=${encodeURIComponent(currentUser)}`);
        if (!response.ok) throw new Error('No cards found');
        
        currentCard = await response.json();
        renderCard(currentCard);
    } catch (error) {
        console.error('Error loading card:', error);
        document.getElementById('card-word').textContent = "No cards available";
    }
}

function highlightWord(text, word) {
    if (!text || !word) return text;
    // Case-insensitive replace with word boundary check
    const regex = new RegExp(`\\b(${word})\\b`, 'gi');
    return text.replace(regex, '<span class="highlight">$1</span>');
}

function formatProsody(text) {
    if (!text) return '';
    // Escape HTML to prevent XSS, then apply formatting
    let formatted = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    // Bold: **WORD** -> <strong>WORD</strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic: *word* -> <em>word</em>
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Pauses: | -> <span class="pause">|</span>
    formatted = formatted.replace(/\|/g, '<span class="pause">|</span>');

    // Arrows: ↑ ↓ -> <span class="arrow">...</span>
    formatted = formatted.replace(/([↑↓])/g, '<span class="arrow">$1</span>');

    return formatted;
}

function renderCard(card) {
    document.getElementById('card-word').textContent = card.word;
    document.getElementById('card-level').textContent = card.level;
    document.getElementById('card-pos').textContent = card.pos;
    
    // Highlight word in sentences
    const formalHTML = highlightWord(card.sentence_formal, card.word) || 'No sentence available';
    const informalHTML = highlightWord(card.sentence_informal, card.word) || 'No sentence available';
    
    document.getElementById('sentence-formal').innerHTML = formalHTML;
    document.getElementById('sentence-informal').innerHTML = informalHTML;

    // Display prosody guides from dedicated columns (with fallback to stored user guides)
    document.getElementById('prosody-formal').innerHTML =
        formatProsody(card.sentence_formal_prosody || card.user_transcription_formal || '');
    document.getElementById('prosody-informal').innerHTML =
        formatProsody(card.sentence_informal_prosody || card.user_transcription_informal || '');
    // Clear recognized transcription display until rated
    document.getElementById('transcription-formal').textContent = '';
    document.getElementById('transcription-informal').textContent = '';

    // Check user audio for formal
    if (card.user_audio_formal_path) {
        document.getElementById('play-user-formal').classList.remove('hidden');
        document.getElementById('btn-rate-formal').classList.remove('hidden');
    } else {
        document.getElementById('play-user-formal').classList.add('hidden');
        document.getElementById('btn-rate-formal').classList.add('hidden');
    }

    // Check user audio for informal
    if (card.user_audio_informal_path) {
        document.getElementById('play-user-informal').classList.remove('hidden');
        document.getElementById('btn-rate-informal').classList.remove('hidden');
    } else {
        document.getElementById('play-user-informal').classList.add('hidden');
        document.getElementById('btn-rate-informal').classList.add('hidden');
    }
}

function resetUI() {
    currentCard = null;
    currentAudioBlob = null;
    currentRecordingType = null;
    
    document.getElementById('play-user-formal').classList.add('hidden');
    document.getElementById('play-user-informal').classList.add('hidden');
    document.getElementById('btn-rate-formal').classList.add('hidden');
    document.getElementById('btn-rate-informal').classList.add('hidden');
    
    document.getElementById('review-formal').classList.add('hidden');
    document.getElementById('review-informal').classList.add('hidden');
    
    document.getElementById('btn-record-formal').classList.remove('hidden');
    document.getElementById('btn-record-informal').classList.remove('hidden');
    document.getElementById('btn-record-formal').textContent = '🎤 Record';
    document.getElementById('btn-record-informal').textContent = '🎤 Record';

    document.getElementById('recording-status').textContent = '';
    document.getElementById('card-word').textContent = 'Loading...';
    document.getElementById('transcription-formal').textContent = '';
    document.getElementById('transcription-informal').textContent = '';
    document.getElementById('rating-formal').textContent = '';
    document.getElementById('rating-informal').textContent = '';
    document.getElementById('mis-formal').textContent = '';
    document.getElementById('mis-informal').textContent = '';
    document.getElementById('prosody-formal').textContent = '';
    document.getElementById('prosody-informal').textContent = '';
}

function playAudio(type) {
    if (!currentCard) return;
    
    const path = type === 'formal' ? currentCard.audio_formal_path : currentCard.audio_informal_path;
    if (!path) {
        alert('No audio available');
        return;
    }
    
    // Path is the full relative path from DB (e.g. audios/audios_tts_sentences/...)
    const audio = new Audio(`/${path}`);
    audio.play();
}

function playUserAudio(type) {
    if (!currentCard) return;
    
    const path = type === 'formal' ? currentCard.user_audio_formal_path : currentCard.user_audio_informal_path;
    if (!path) {
        console.warn('No user audio path found for type:', type);
        return;
    }
    
    console.log('Playing user audio:', path);
    const audio = new Audio(`/audios_user/${path}`);
    audio.onerror = (e) => {
        console.error('Error playing user audio:', e);
        alert('Error playing audio. File might be missing or format unsupported.');
    };
    audio.play().catch(e => {
        console.error('Error starting playback:', e);
        alert('Error starting playback: ' + e.message);
    });
}

async function markKnown() {
    if (!currentCard) return;

    try {
        await fetch('/api/mark_known', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word: currentCard.word,
                pos: currentCard.pos,
                level: currentCard.level,
                username: currentUser
            })
        });
        loadCard();
    } catch (error) {
        console.error('Error marking known:', error);
    }
}

// Recording Logic
async function toggleRecording(type) {
    const btn = document.getElementById(`btn-record-${type}`);
    
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        // Stop recording
        if (currentRecordingType === type) {
            mediaRecorder.stop();
            // UI updates happen in onstop
        } else {
            alert('Already recording another section!');
        }
    } else {
        // Start recording - clear any previous blob
        currentAudioBlob = null;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            currentRecordingType = type;

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                    console.log('Audio chunk received:', event.data.size);
                }
            };

            mediaRecorder.onstop = () => {
                const mimeType = mediaRecorder.mimeType || 'audio/webm';
                currentAudioBlob = new Blob(audioChunks, { type: mimeType });
                console.log('Recording stopped. Blob size:', currentAudioBlob.size, 'Type:', currentAudioBlob.type);
                // Stop all tracks to release microphone
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                
                // Show Review UI - Auto Save
                btn.classList.add('hidden'); 
                btn.classList.remove('recording');
                document.getElementById(`review-${type}`).classList.remove('hidden');
                
                // Trigger Auto Save
                saveRecording(type);
            };

            mediaRecorder.start(200);
            btn.textContent = '⏹ Stop';
            btn.classList.add('recording');
            document.getElementById('recording-status').textContent = `Recording ${type}...`;
            
        } catch (error) {
            console.error('Error accessing microphone:', error);
            alert('Could not access microphone');
        }
    }
}

function playPreview(type) {
    if (!currentAudioBlob) {
        console.error('No audio blob to play');
        return;
    }
    console.log('Playing preview. Blob size:', currentAudioBlob.size, 'Type:', currentAudioBlob.type);
    const audioUrl = URL.createObjectURL(currentAudioBlob);
    const audio = new Audio(audioUrl);
    audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
    };
    audio.play().catch(e => {
        console.error('Error playing preview:', e);
        alert('Error playing preview: ' + e.message);
    });
}

function discardRecording(type) {
    // If recording is still active, stop it first
    if (mediaRecorder && mediaRecorder.state === 'recording' && currentRecordingType === type) {
        mediaRecorder.stop();
        // Stop all tracks to release microphone
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    currentAudioBlob = null;
    currentRecordingType = null;
    audioChunks = [];
    
    // Reset UI
    document.getElementById(`review-${type}`).classList.add('hidden');
    const btn = document.getElementById(`btn-record-${type}`);
    btn.classList.remove('hidden');
    btn.classList.remove('recording');
    btn.textContent = '🎤 Record';
    document.getElementById('recording-status').textContent = 'Recording discarded.';
}

async function saveRecording(type) {
    if (!currentAudioBlob) return;

    const formData = new FormData();
    formData.append('audio', currentAudioBlob, 'recording.webm');
    formData.append('word', currentCard.word);
    formData.append('pos', currentCard.pos);
    formData.append('level', currentCard.level);
    formData.append('type', type);
    formData.append('username', currentUser);

    document.getElementById('recording-status').textContent = 'Auto-saving...';

    try {
        const response = await fetch('/api/upload_audio', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.success) {
            // Update local card data
            if (type === 'formal') {
                currentCard.user_audio_formal_path = result.path;
                document.getElementById('play-user-formal').classList.remove('hidden');
                document.getElementById('btn-rate-formal').classList.remove('hidden');
                // Clear old rating when new audio is saved
                document.getElementById('rating-formal').textContent = '';
                document.getElementById('mis-formal').textContent = '';
                document.getElementById('transcription-formal').textContent = '';
            } else {
                currentCard.user_audio_informal_path = result.path;
                document.getElementById('play-user-informal').classList.remove('hidden');
                document.getElementById('btn-rate-informal').classList.remove('hidden');
                // Clear old rating when new audio is saved
                document.getElementById('rating-informal').textContent = '';
                document.getElementById('mis-informal').textContent = '';
                document.getElementById('transcription-informal').textContent = '';
            }
            
            document.getElementById(`review-${type}`).classList.add('hidden');
            const btn = document.getElementById(`btn-record-${type}`);
            btn.classList.remove('hidden');
            btn.textContent = '🎤 Record';
            
            document.getElementById('recording-status').textContent = 'Saved!';
            
            // Auto Rate after save? Not requested, but maybe useful.
            // But we already showed the "My Rec" button.
        } else {
            document.getElementById('recording-status').textContent = 'Error saving.';
        }
    } catch (error) {
        console.error('Error uploading:', error);
        document.getElementById('recording-status').textContent = 'Error uploading.';
    }
    
    currentRecordingType = null;
    mediaRecorder = null;
    currentAudioBlob = null;
    audioChunks = [];
}

function rateRecording(type) {
    if (!currentCard) return;

    const hasRec = type === 'formal' ? currentCard.user_audio_formal_path : currentCard.user_audio_informal_path;
    if (!hasRec) {
        alert('Save a recording first.');
        return;
    }

    const ratingEl = document.getElementById(`rating-${type}`);
    const misEl = document.getElementById(`mis-${type}`);
    ratingEl.textContent = 'Rating...';
    misEl.textContent = '';

    fetch('/api/rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            word: currentCard.word,
            pos: currentCard.pos,
            level: currentCard.level,
            type: type,
            username: currentUser
        })
    }).then(resp => resp.json())
      .then(data => {
          if (!data.success) {
              ratingEl.textContent = '';
              alert(data.error || 'Rating failed');
              return;
          }
          const { pronunciation_score, accuracy_score, fluency_score, prosody_score, total_score, recognized_text, mispronunciations } = data;
          
          ratingEl.textContent = `Total: ${total_score?.toFixed(1)} | Pronunciation: ${pronunciation_score?.toFixed(1)} | Acc: ${accuracy_score?.toFixed(1)} | Flu: ${fluency_score?.toFixed(1)} | Prosody: ${prosody_score?.toFixed(1)}`;
          
          // Conditional Formatting
          ratingEl.className = 'rating-text'; // Reset
          if (total_score >= 90) ratingEl.classList.add('score-excellent');
          else if (total_score >= 80) ratingEl.classList.add('score-good');
          else if (total_score >= 60) ratingEl.classList.add('score-average');
          else ratingEl.classList.add('score-poor');
          
          const transcriptionEl = document.getElementById(`transcription-${type}`);
          transcriptionEl.textContent = recognized_text ? `"${recognized_text}"` : '';
          const misList = (mispronunciations || []).map(w => `${w.word} (${w.accuracy?.toFixed(1)})`).join(', ');
          misEl.textContent = misList ? `Mispronounced: ${misList}` : 'Mispronounced: none';
      })
      .catch(err => {
          console.error('Rating error', err);
          ratingEl.textContent = '';
          alert('Error rating audio');
      });
}

async function requestTranscription(type) {
    if (!currentCard) return;
    
    const btn = document.getElementById(`btn-transcribe-${type}`);
    const originalText = btn.textContent;
    btn.textContent = '⏳...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word: currentCard.word,
                pos: currentCard.pos,
                level: currentCard.level,
                type: type,
                username: currentUser
            })
        });
        
        const result = await response.json();
        if (result.success) {
            const transcriptionEl = document.getElementById(`transcription-${type}`);
            transcriptionEl.textContent = `"${result.transcription}"`;
            
            // Update local state
            if (type === 'formal') {
                currentCard.user_transcription_formal = result.transcription;
            } else {
                currentCard.user_transcription_informal = result.transcription;
            }
        } else {
            alert('Transcription failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error requesting transcription:', error);
        alert('Error requesting transcription');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
