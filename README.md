---
title: NPGC Assistant
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
---

# NPGC Assistant | Modular FastAPI Chatbot


A high-performance, modular chatbot application built with FastAPI, Redis, and a premium Vanilla JS frontend.

## Features
- **Modular Backend**: Separate services for AI, FAQ, Redis Caching, and Voice support.
- **Premium UI**: Modern, glassmorphism-inspired chat interface.
- **Voice Support**: Integrated speech-to-text and text-to-speech stubs.
- **FastAPI**: Asynchronous, high-performance API.
- **Redis**: Fast caching for chat history and FAQ lookups.

## Project Structure
```
chatbot/
├── backend/
│   ├── app.py           # Application Entry Point
│   ├── routes/          # API Route Definitions
│   ├── services/        # Business Logic / Services
│   ├── models/          # Data Models
│   └── utils/           # Helper Functions
├── frontend/            # Web Frontend
└── requirements.txt     # Python Dependencies
```

## Setup & Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Backend
```bash
cd backend
uvicorn app:app --reload
```

### 3. Open Frontend
Simply open `frontend/index.html` in your browser.
