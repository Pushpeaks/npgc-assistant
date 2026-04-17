document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const voiceTrigger = document.getElementById('voice-trigger');
    const ttsToggle = document.getElementById('tts-toggle');
    const langSwitch = document.getElementById('lang-switch');
    const autocompleteList = document.getElementById('autocomplete-list');
    const clearChatBtn = document.getElementById('clear-chat');
    
    const API_URL = '/api/chat';

    // State
    let isRecording = false;
    let autoSpeak = false;
    let currentLang = 'en-US'; 
    let isManualLang = false; // User manually toggled
    let recognition = null;
    let recognitionTimeout = null;



    // --- Rotating Placeholder ---
    const placeholderQuestions = [
        "What courses are available?",
        "How to apply for admission?",
        "Tell me about the library...",
        "Is there a hostel at NPGC?",
        "What is the placement record?",
        "Who are the faculty members?",
        "Ask about BBA syllabus...",
        "NPGC ka contact number?",
        "What events happen at NPGC?",
        "Tell me about alumni...",
        "Admission deadline kya hai?",
    ];
    let placeholderIdx = 0;
    function rotatePlaceholder() {
        userInput.style.transition = 'opacity 0.4s ease';
        userInput.style.opacity = '0.4';
        setTimeout(() => {
            placeholderIdx = (placeholderIdx + 1) % placeholderQuestions.length;
            userInput.setAttribute('placeholder', placeholderQuestions[placeholderIdx]);
            userInput.style.opacity = '1';
        }, 400);
    }
    userInput.setAttribute('placeholder', placeholderQuestions[0]);
    setInterval(rotatePlaceholder, 3000);

    // --- Startup Sequence ---
    function initChat() {
        addMessage("Hello! I am your **NPGC Assistant**. How can I help you today?", 'bot', [
            "🏫 Admissions", "📚 Courses Offered", "🎓 Scholarships", "📞 Contact NPGC"
        ]);
    }

    // --- Helper: Stop Recording ---
    function stopRecording() {
        isRecording = false;
        voiceTrigger.classList.remove('recording');
        clearRecognitionTimeout();
        if (recognition) {
            try { recognition.stop(); } catch (e) { /* already stopped */ }
        }
    }

    function setRecognitionTimeout(ms) {
        recognitionTimeout = setTimeout(() => stopRecording(), ms);
    }

    function clearRecognitionTimeout() {
        if (recognitionTimeout) {
            clearTimeout(recognitionTimeout);
            recognitionTimeout = null;
        }
    }

    function handleVoiceError(error) {
        const messages = {
            'not-allowed': 'Microphone access denied.',
            'no-speech': 'No speech detected.',
            'network': 'Network error during voice recognition.',
        };
        addMessage(messages[error] || `Voice error: ${error}`, 'bot');
    }

    // --- Voice Initialization ---
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isRecording = true;
            voiceTrigger.classList.add('recording');
            setRecognitionTimeout(10000);
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            clearRecognitionTimeout();
            chatForm.dispatchEvent(new Event('submit'));
        };

        recognition.onerror = (event) => {
            console.error('Speech Recognition Error:', event.error);
            handleVoiceError(event.error);
            stopRecording();
        };

        recognition.onend = () => stopRecording();

    } else {
        voiceTrigger.style.display = 'none';
    }

    function speakText(text, lang) {
        if (!autoSpeak || !window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        
        const cleanText = text.replace(/[*_#]/g, '');
        const utterance = new SpeechSynthesisUtterance(cleanText);
        const targetLang = lang || 'en-US';
        utterance.lang = targetLang;

        // --- Voice Selection (Feminine Persona) ---
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {
            // Find a female voice for the target language
            const femaleVoice = voices.find(v => 
                v.lang.startsWith(targetLang.split('-')[0]) && 
                (v.name.toLowerCase().includes('female') || 
                 v.name.toLowerCase().includes('samantha') || 
                 v.name.toLowerCase().includes('zira') || 
                 v.name.toLowerCase().includes('google us english') ||
                 v.name.toLowerCase().includes('hindi female') ||
                 v.name.toLowerCase().includes('google hindi'))
            );
            if (femaleVoice) utterance.voice = femaleVoice;
        }

        window.speechSynthesis.speak(utterance);
    }

    // --- Message rendering ---
    function addMessage(content, type, suggestions = []) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', type);

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        if (type === 'bot') {
            avatar.innerHTML = `<img src="assets/clg_logo.png" alt="Bot">`;
        } else {
            avatar.innerHTML = `<i class="bi bi-person-circle"></i>`;
        }
        messageDiv.appendChild(avatar);

        const messageDetails = document.createElement('div');
        messageDetails.className = 'message-details';

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        
        // Simple markdown support for bolding
        let formattedContent = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        contentDiv.innerHTML = formattedContent.replace(/\n/g, '<br>');
        messageDetails.appendChild(contentDiv);

        if (type === 'bot') {
            // Add Suggestion Buttons
            if (suggestions && suggestions.length > 0) {
                const suggContainer = document.createElement('div');
                suggContainer.className = 'suggestions-container';
                suggestions.forEach(text => {
                    const btn = document.createElement('button');
                    btn.className = 'suggestion-btn';
                    btn.innerText = text;
                    btn.onclick = () => {
                        handleQuery(text);
                    };
                    suggContainer.appendChild(btn);
                });
                messageDetails.appendChild(suggContainer);
            }
        }

        const time = document.createElement('div');
        time.className = 'message-time';
        const now = new Date();
        time.innerText = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        messageDetails.appendChild(time);

        messageDiv.appendChild(messageDetails);

        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function scrollToBottom() {
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 50);
    }

    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'message bot';
        const thinkingText = currentLang.startsWith('hi') ? 'सोच रही हूँ...' : 'Thinking...';
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <img src="assets/clg_logo.png" alt="Bot">
            </div>
            <div class="message-details">
                <div class="message-content shimmer-effect">
                    <div class="thinking-wrapper">
                        <span class="thinking-text">${thinkingText}</span>
                        <div class="typing-dot-container">
                            <div class="dot"></div>
                            <div class="dot"></div>
                            <div class="dot"></div>
                        </div>
                    </div>
                </div>
            </div>`;
        chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }


    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    }

    // --- Gibberish Detector (Phonotactics-based) ---
    // Valid English consonant bigrams — any pair NOT in this set is illegal and signals gibberish
    const VALID_BIGRAMS = new Set([
        'bl','br','ch','cl','cr','dr','ds','dl','dm','dw','fl','fr','gh','gl','gr',
        'kh','kl','kn','kr','lk','lm','lp','ll','ln','lt','lf','ld','lv',
        'mb','mn','mp','nd','ng','nk','nt','nc','nf','ns','nw',
        'ph','pl','pr','ps','pt',
        'rb','rc','rd','rf','rg','rk','rl','rm','rn','rp','rr','rs','rt','rv','rw',
        'sc','sh','sk','sl','sm','sn','sp','ss','st','sw','ck',
        'th','tr','ts','tw','wh','wr','xp','xt'
    ]);

    function wordIsGibberish(word) {
        const w = word.toLowerCase().replace(/[^a-z]/g, '');
        if (w.length < 2) return false;
        // Split word into consonant clusters (segments between vowels)
        const clusters = w.split(/[aeiou]+/).filter(c => c.length >= 2);
        for (const cluster of clusters) {
            for (let i = 0; i < cluster.length - 1; i++) {
                if (!VALID_BIGRAMS.has(cluster[i] + cluster[i + 1])) return true;
            }
        }
        return false;
    }

    function isGibberish(text) {
        const t = text.trim().toLowerCase();
        if (t.length < 2) return true;

        // Repeated char bursts (e.g. "aaaaaaa")
        if (/(.)\1{4,}/.test(t)) return true;

        // Known keyboard mash patterns
        const mashPatterns = ['qwerty', 'asdfgh', 'zxcvbn', 'qweasd', 'qazwsx'];
        if (mashPatterns.some(p => t.includes(p))) return true;

        // Split into words, check each word for illegal consonant clusters
        const words = t.split(/\s+/).filter(w => /[a-z]{2,}/.test(w));
        if (words.length === 0) return true;

        // Allow known NPGC/Hindi keywords to pass even if short
        const knownWords = new Set([
            'admission', 'admissions', 'deadline', 'deadlines', 'apply', 'faculty', 'professor', 'contact',
            'course', 'courses', 'fee', 'fees', 'scholarship', 'eligibility', 'npgc',
            'bca','bba','bsc','mca','mba','ba','ma','hod','lab',
            'kab','kya','hai','se','ki','ka','ko','toh','kaise','kitni','btao','kahan'
        ]);

        // HIGH-SAFETY UPGRADE: If the query contains ANY of these core keywords, it's NEVER gibberish
        const coreKeywords = ['admission', 'course', 'faculty', 'fee', 'scholarship', 'eligibility', 'deadline', 'apply', 'contact'];
        if (coreKeywords.some(kw => t.includes(kw))) return false;

        const gibWords = words.filter(w => {
            const clean = w.replace(/[^a-z]/g, '');
            if (knownWords.has(clean)) return false; // whitelist passes
            return wordIsGibberish(w);
        });

        // If ALL words in the message are gibberish → flag it
        return gibWords.length > 0 && gibWords.length === words.length;
    }

    async function handleQuery(query) {
        if (!query) return;

        if (isGibberish(query)) {
            addMessage(query, 'user');
            userInput.value = '';
            stopRecording();
            addMessage("🤔 I didn't quite understand that. Could you please rephrase? Try asking about **Admissions**, **Courses**, or **Faculty**!", 'bot', [
                "What courses are available?",
                "How to apply?"
            ]);
            return;
        }

        addMessage(query, 'user');
        userInput.value = '';
        stopRecording();
        showTypingIndicator();

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    session_id: 'widget-session',
                    language: currentLang,
                    is_explicit: isManualLang
                })

            });


            hideTypingIndicator();
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            
            // Sync language if backend detected a change AND user hasn't locked a preference
            if (!isManualLang && data.language && data.language !== currentLang) {
                currentLang = data.language;
                updateLangUI();
            }


            addMessage(data.response, 'bot', data.suggestions);
            if (autoSpeak) speakText(data.response, data.language);


        } catch (error) {
            hideTypingIndicator();
            addMessage('❌ Connectivity issue. Please try again.', 'bot');
        }
    }

    // --- Event Listeners ---
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleQuery(userInput.value.trim());
    });

    voiceTrigger.addEventListener('click', () => {
        if (isRecording) {
            stopRecording();
        } else if (recognition) {
            recognition.lang = currentLang; // Dynamic language sensing
            recognition.start();
        }
    });

    langSwitch.addEventListener('click', () => {
        isManualLang = true;
        currentLang = currentLang === 'en-US' ? 'hi-IN' : 'en-US';
        updateLangUI();
    });


    function updateLangUI() {
        langSwitch.innerHTML = `<span class="icon">${currentLang === 'en-US' ? 'EN / हिंदी' : 'हिंदी / EN'}</span>`;
        if (currentLang === 'hi-IN') {
            langSwitch.classList.add('active');
            userInput.placeholder = "अपना सवाल यहाँ लिखें...";
        } else {
            langSwitch.classList.remove('active');
            userInput.placeholder = "Type your message...";
        }
    }


    ttsToggle.addEventListener('click', () => {
        autoSpeak = !autoSpeak;
        ttsToggle.innerHTML = autoSpeak ? '<span class="icon">🔊</span>' : '<span class="icon">🔇</span>';
        if (!autoSpeak) window.speechSynthesis.cancel();
    });

    clearChatBtn.addEventListener('click', () => {
        chatMessages.innerHTML = '';
        isManualLang = false;
        currentLang = 'en-US';
        updateLangUI();
        initChat();
    });


    // --- Autocomplete Logic ---
    let autocompleteTimeout = null;
    userInput.addEventListener('input', () => {
        const query = userInput.value.trim();
        clearTimeout(autocompleteTimeout);
        if (query.length < 2) {
            autocompleteList.style.display = 'none';
            return;
        }
        autocompleteTimeout = setTimeout(async () => {
            try {
                const res = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
                if (!res.ok) return;
                const suggestions = await res.json();
                if (suggestions.length > 0) {
                    renderAutocomplete(suggestions);
                } else {
                    autocompleteList.style.display = 'none';
                }
            } catch (err) { console.error(err); }
        }, 300);
    });

    function renderAutocomplete(suggestions) {
        autocompleteList.innerHTML = '';
        suggestions.forEach(text => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.innerText = text;
            item.onclick = () => {
                autocompleteList.style.display = 'none';
                handleQuery(text);
            };
            autocompleteList.appendChild(item);
        });
        autocompleteList.style.display = 'block';
    }

    document.addEventListener('click', (e) => {
        if (!autocompleteList.contains(e.target) && e.target !== userInput) {
            autocompleteList.style.display = 'none';
        }
    });

    // --- Run Initialization ---
    initChat();
});
