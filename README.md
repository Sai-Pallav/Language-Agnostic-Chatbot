# NexusAI — Enhanced Chatbot

A full-featured AI chatbot with NLP analysis, built on Flask + Groq.

## ✨ New Features

### 🎤 Voice Input
- Click the microphone button to speak your message
- Uses the Web Speech API (Chrome/Edge recommended)
- Transcription auto-fills the input box and sends on silence
- Voice messages are tagged with a 🎤 badge in chat

### 🖼️ Image Uploads
- Click the 🖼️ button to upload an image (JPG, PNG, GIF, WEBP)
- Drag & drop images directly into the chat area
- Images are sent to Groq's vision model (llama-3.2-11b-vision-preview)
- The AI will describe and analyze the image

### 📎 File Attachments
- Click the 📎 button to attach a file
- Supported: `.txt`, `.md`, `.csv`, `.json`, `.py`, `.js`, `.ts`, `.html`, `.css`, `.xml`, `.yaml`, `.pdf`, `.docx`, `.xlsx`
- File content is extracted and sent as context to the AI
- Large files are automatically truncated at 15,000 characters

### 🔀 Combined Inputs
- Mix text + images + files in a single message
- Attachments preview bar shows before sending
- Click × on any attachment to remove it

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000 and set your free Groq API key (from console.groq.com).

## Models Used
- **Text**: `llama-3.3-70b-versatile` (fast, smart)
- **Vision**: `llama-3.2-11b-vision-preview` (auto-selected when images present)
