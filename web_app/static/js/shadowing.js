let offset = 0;
const limit = 100;
const shadowingRecorders = {};
const shadowingAudioChunks = {};
const shadowingAudioBlobs = {};
let currentBook = null;
let currentChapter = null;
let currentSubtitle = null;


document.addEventListener('DOMContentLoaded', () => {
    // initTheme is handled by main.js
    loadBooks();
    
    const bookSelect = document.getElementById('book-select');
    const chapterSelect = document.getElementById('chapter-select');

    bookSelect.addEventListener('change', (e) => {
        currentBook = e.target.value;
        currentChapter = null;
        currentSubtitle = null;
        
        // Reset chapter select
        chapterSelect.innerHTML = '<option value="">Select Chapter...</option>';
        chapterSelect.disabled = true;
        
        // Clear content
        document.getElementById('sentences-list').innerHTML = '<div style="text-align: center; margin-top: 50px; color: var(--text-muted);">Select a book and chapter to start practicing.</div>';

        if (currentBook) {
            loadStructure(currentBook);
        }
    });

    chapterSelect.addEventListener('change', (e) => {
        const value = e.target.value;
        if (value) {
            // Value format: "Chapter Name|Subtitle" or just "Chapter Name"
            const parts = value.split('|');
            currentChapter = parts[0];
            currentSubtitle = parts.length > 1 ? parts[1] : null;
            
            loadContent(currentBook, currentChapter, currentSubtitle);
        } else {
            document.getElementById('sentences-list').innerHTML = '<div style="text-align: center; margin-top: 50px; color: var(--text-muted);">Select a chapter to start practicing.</div>';
        }
    });
});

async function loadBooks() {
    const select = document.getElementById('book-select');
    try {
        const response = await fetch('/api/shadowing/books');
        const books = await response.json();
        
        select.innerHTML = '<option value="">Select Book...</option>';
        books.forEach(book => {
            const option = document.createElement('option');
            option.value = book;
            option.textContent = book;
            select.appendChild(option);
        });
        
        // Auto-select first book if available
        if (books.length > 0) {
            select.value = books[0];
            // Trigger change event manually
            select.dispatchEvent(new Event('change'));
        }
    } catch (error) {
        console.error('Error loading books:', error);
        select.innerHTML = '<option value="">Error loading books</option>';
    }
}

async function loadStructure(book) {
    const chapterSelect = document.getElementById('chapter-select');
    chapterSelect.innerHTML = '<option value="">Loading chapters...</option>';
    chapterSelect.disabled = true;
    
    try {
        console.log(`Fetching structure for book: ${book}`);
        const response = await fetch(`/api/shadowing/structure?book=${encodeURIComponent(book)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const structure = await response.json();
        
        chapterSelect.innerHTML = '<option value="">Select Chapter...</option>';
        
        if (Object.keys(structure).length === 0) {
            chapterSelect.innerHTML = '<option value="">No chapters found</option>';
            return;
        }
        
        for (const [chapter, subtitles] of Object.entries(structure)) {
            if (subtitles && subtitles.length > 0) {
                // Add option group for chapter if it has subtitles
                const optgroup = document.createElement('optgroup');
                optgroup.label = chapter;
                
                // Option for the chapter itself (if needed, or just subtitles)
                // Usually if there are subtitles, we might want to select specific subtitle
                // But let's allow selecting the whole chapter too if that makes sense, 
                // or just list subtitles.
                // Based on previous logic: "Load chapter content if no subtitles or just to start"
                
                // Let's add the main chapter as an option
                const mainOption = document.createElement('option');
                mainOption.value = chapter;
                mainOption.textContent = `${chapter} (Full)`;
                optgroup.appendChild(mainOption);

                subtitles.forEach(sub => {
                    const option = document.createElement('option');
                    option.value = `${chapter}|${sub}`;
                    option.textContent = sub;
                    optgroup.appendChild(option);
                });
                chapterSelect.appendChild(optgroup);
            } else {
                // Just a chapter option
                const option = document.createElement('option');
                option.value = chapter;
                option.textContent = chapter;
                chapterSelect.appendChild(option);
            }
        }
        
        chapterSelect.disabled = false;
        
        // Auto-select first chapter? Maybe not, let user choose.
        
    } catch (error) {
        console.error('Error loading structure:', error);
        chapterSelect.innerHTML = '<option value="">Error loading chapters</option>';
    }
}

async function loadContent(book, chapter, subtitle) {
    offset = 0;
    
    const container = document.getElementById('sentences-list');
    container.innerHTML = '<div style="text-align:center; padding:20px;">Loading...</div>';
    
    try {
        let url = `/api/shadowing/content?limit=${limit}&offset=${offset}`;
        if (book) url += `&book=${encodeURIComponent(book)}`;
        if (chapter) url += `&chapter=${encodeURIComponent(chapter)}`;
        if (subtitle) url += `&subtitle=${encodeURIComponent(subtitle)}`;
        
        const response = await fetch(url);
        const paragraphs = await response.json();
        
        container.innerHTML = '';
        
        if (paragraphs.length === 0) {
            container.innerHTML = '<div style="text-align:center; padding:20px;">No content found.</div>';
            return;
        }

        // Header for the section
        const header = document.createElement('h2');
        header.style.marginBottom = '20px';
        header.textContent = subtitle ? `${chapter} - ${subtitle}` : chapter;
        container.appendChild(header);

        // Create a card for each paragraph (chunk)
        paragraphs.forEach(p => {
            const card = createCard(p);
            container.appendChild(card);
        });

    } catch (error) {
        console.error('Error loading content:', error);
        container.innerHTML = '<div style="color:red; text-align:center;">Error loading content</div>';
    }
}

function createCard(paragraph) {
    const div = document.createElement('div');
    div.className = 'sentence-card';
    const id = paragraph.id;
    
    let audioHtml = '';
    if (paragraph.audio_path) {
        const filename = paragraph.audio_path.split('/').pop();
        audioHtml = `
            <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee;">
                <label style="font-weight:bold; display:block; margin-bottom:5px;">Original Audio:</label>
                <audio controls src="/audios_book/${filename}" style="width: 100%;"></audio>
            </div>
        `;
    }

    // TTS Section
    let ttsHtml = '';
    const ttsPath = paragraph.tts_audio_path;
    
    if (ttsPath) {
        const ttsFilename = ttsPath.split('/').pop();
        ttsHtml = `
            <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee; background-color: #f0f8ff; padding: 10px; border-radius: 5px;">
                <label style="font-weight:bold; display:block; margin-bottom:5px; color: #333;">TTS Audio:</label>
                <audio controls src="/audios_book/${ttsFilename}" style="width: 100%;"></audio>
            </div>
        `;
    } else {
        // Show Generate Button if no TTS yet
        ttsHtml = `
            <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee;">
                <button id="btn-tts-${id}" class="btn btn-secondary" onclick="generateTTS(${id})">✨ Generate TTS Audio</button>
                <div id="tts-status-${id}" style="margin-top:5px; font-size:0.9em; color:#666;"></div>
            </div>
        `;
    }

    let userAudioContainerHtml = `<div id="user-audio-container-${id}"></div>`;
    let rateButtonClass = 'btn-icon hidden';
    let rateButtonAttr = '';

    if (paragraph.user_audio_path) {
        const filename = paragraph.user_audio_path.split('/').pop();
        userAudioContainerHtml = `
            <div id="user-audio-container-${id}">
                <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee; background-color: #e8f5e9; padding: 10px; border-radius: 5px;">
                    <label style="font-weight:bold; display:block; margin-bottom:5px; color: #333;">User Audio:</label>
                    <audio controls src="/audios_user/${filename}" style="width: 100%;"></audio>
                </div>
            </div>
        `;
        rateButtonClass = 'btn-icon';
        rateButtonAttr = `data-audio-path="${paragraph.user_audio_path}"`;
    }

    const textHtml = `<p class="sentence-text" style="margin-bottom: 15px;">${paragraph.content}</p>`;
    const allText = paragraph.content;

    const controlsHtml = `
        <div class="controls" style="margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">
            <button class="btn-icon btn-record" id="btn-record-${id}" onclick="toggleRecording(${id})">🎤 Record</button>
            <button class="btn-icon btn-play-user hidden" id="btn-play-${id}" onclick="playUserAudio(${id})">▶️ Play My Rec</button>
            <button class="${rateButtonClass}" id="btn-rate-${id}" onclick="rateRecording(${id})" ${rateButtonAttr}>⭐ Rate</button>
        </div>
        <div class="result-box" id="result-${id}"></div>
        <!-- Hidden element for reference text -->
        <div id="text-${id}" style="display:none;">${allText}</div>
    `;

    div.innerHTML = `
        ${audioHtml}
        ${ttsHtml}
        ${userAudioContainerHtml}
        ${textHtml}
        ${controlsHtml}
    `;
    return div;
}

async function generateTTS(id) {
    const btn = document.getElementById(`btn-tts-${id}`);
    const status = document.getElementById(`tts-status-${id}`);
    
    btn.disabled = true;
    btn.textContent = 'Generating...';
    status.textContent = 'Sending text to Azure AI...';
    
    try {
        const response = await fetch('/api/shadowing/generate_tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id })
        });
        
        const result = await response.json();
        
        if (result.success) {
            status.textContent = 'Done! Reloading...';
            // Reload content to show the new player
            loadContent(currentBook, currentChapter, currentSubtitle);
        } else {
            status.textContent = 'Error: ' + result.error;
            btn.disabled = false;
            btn.textContent = '✨ Generate TTS Audio';
        }
    } catch (error) {
        console.error('TTS Error:', error);
        status.textContent = 'Network error';
        btn.disabled = false;
        btn.textContent = '✨ Generate TTS Audio';
    }
}

async function toggleRecording(id) {
    const btn = document.getElementById(`btn-record-${id}`);
    
    if (shadowingRecorders[id] && shadowingRecorders[id].state === 'recording') {
        shadowingRecorders[id].stop();
        btn.textContent = '🎤 Record';
        btn.classList.remove('recording');
    } else {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            shadowingRecorders[id] = mediaRecorder;
            shadowingAudioChunks[id] = [];

            mediaRecorder.ondataavailable = (event) => {
                shadowingAudioChunks[id].push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(shadowingAudioChunks[id], { type: 'audio/webm' });
                shadowingAudioBlobs[id] = audioBlob;
                
                // Show controls
                // document.getElementById(`btn-play-${id}`).classList.remove('hidden'); // Replaced by audio player
                document.getElementById(`btn-rate-${id}`).classList.remove('hidden');
                
                // Auto upload to get ready for rating
                await uploadAudio(id, audioBlob);
            };

            mediaRecorder.start();
            btn.textContent = '⏹ Stop';
            btn.classList.add('recording');
        } catch (err) {
            console.error('Error accessing microphone:', err);
            alert('Could not access microphone');
        }
    }
}

function playUserAudio(id) {
    if (shadowingAudioBlobs[id]) {
        const audioUrl = URL.createObjectURL(shadowingAudioBlobs[id]);
        const audio = new Audio(audioUrl);
        audio.play();
    }
}

async function uploadAudio(id, blob) {
    const formData = new FormData();
    formData.append('audio', blob, `shadowing_${id}.webm`);
    formData.append('source', 'shadowing');
    formData.append('id', id);

    try {
        const response = await fetch('/api/upload_audio', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        console.log('Upload result:', result);
        
        if (result.success) {
            // Store the path for rating
            const audioPath = result.path;
            console.log('Storing audio path:', audioPath);
            document.getElementById(`btn-rate-${id}`).dataset.audioPath = audioPath;

            // Show the audio player
            const container = document.getElementById(`user-audio-container-${id}`);
            if (container) {
                const filename = audioPath;
                container.innerHTML = `
                    <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee; background-color: #e8f5e9; padding: 10px; border-radius: 5px;">
                        <label style="font-weight:bold; display:block; margin-bottom:5px; color: #333;">User Audio:</label>
                        <audio controls src="/audios_user/${filename}?t=${new Date().getTime()}" style="width: 100%;"></audio>
                    </div>
                `;
                console.log('Audio player updated for ID:', id);
            }
        } else {
            console.error('Upload failed:', result.error);
        }
    } catch (error) {
        console.error('Error uploading:', error);
    }
}

async function rateRecording(id) {
    const btn = document.getElementById(`btn-rate-${id}`);
    const audioPath = btn.dataset.audioPath;
    const referenceText = document.getElementById(`text-${id}`).textContent;
    const resultBox = document.getElementById(`result-${id}`);

    console.log('Attempting to rate recording:', { id, audioPath, referenceText });

    if (!audioPath) {
        console.error('No audio path found. Dataset:', btn.dataset);
        alert('Please record and wait for upload first.');
        return;
    }

    if (!referenceText || referenceText.trim() === '') {
        alert('No reference text available for rating.');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Rating...';
    resultBox.style.display = 'none';

    try {
        const response = await fetch('/api/rate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: 'shadowing',
                id: id,
                reference_text: referenceText,
                audio_path: audioPath
            })
        });
        
        const result = await response.json();
        console.log('Rating result:', result);
        
        if (result.success) {
            resultBox.style.display = 'block';
            
            // Format mispronunciations
            let misHtml = '';
            if (result.mispronunciations && result.mispronunciations.length > 0) {
                const misList = result.mispronunciations.map(m => 
                    `<span style="color: #d9534f;">${m.word} (${m.accuracy.toFixed(0)}%)</span>`
                ).join(', ');
                misHtml = `
                    <div style="margin-top: 10px; padding: 10px; background: #fff3cd; border-radius: 4px; color: #856404;">
                        <strong>Mispronounced:</strong> ${misList}
                    </div>
                `;
            } else {
                misHtml = `
                    <div style="margin-top: 10px; padding: 10px; background: #d4edda; border-radius: 4px; color: #155724;">
                        <strong>Great job! No mispronunciations detected.</strong>
                    </div>
                `;
            }

            resultBox.innerHTML = `
                <div style="margin-bottom: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px; font-style: italic; color: #555;">
                    <strong>Understood:</strong> ${result.recognized_text}
                </div>
                <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 10px;">
                    <span><strong>Total:</strong> ${result.total_score.toFixed(1)}</span>
                    <span><strong>Score:</strong> ${result.pronunciation_score.toFixed(1)}</span>
                    <span><strong>Accuracy:</strong> ${result.accuracy_score.toFixed(1)}</span>
                    <span><strong>Fluency:</strong> ${result.fluency_score.toFixed(1)}</span>
                    <span><strong>Prosody:</strong> ${result.prosody_score.toFixed(1)}</span>
                </div>
                ${misHtml}
            `;
        } else {
            console.error('Rating failed:', result.error);
            alert('Rating failed: ' + result.error);
        }
    } catch (error) {
        console.error('Error rating:', error);
        alert('Error rating recording: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '⭐ Rate';
    }
}
