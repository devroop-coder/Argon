import os
import subprocess
import speech_recognition as sr
import whisper
import warnings
import re
import datetime
import random
import threading
import time


warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

model = whisper.load_model("base")
conversation_history = []
conversation_active = False
is_speaking = False
interrupt_requested = False

# Argon personality responses
WAKE_RESPONSES = [
    "Hello.",
    "Ready.",
    "Yes?",
    "I'm here."
]

THINKING_RESPONSES = [
    "Thinking...",
    "Processing...",
    "One moment..."
]

CONVERSATION_STARTERS = [
    "How can I help?",
    "What do you need?",
    "Ask me anything."
]

def listen():
    global conversation_active
    r = sr.Recognizer()
    
    
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8
    
    with sr.Microphone() as source:
        print("\nListening...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            audio = r.listen(source, timeout=8, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            return ""

    
    with open("temp.wav", "wb") as f:
        f.write(audio.get_wav_data())

    try:
       
        result = model.transcribe("temp.wav", language="en")
        text = result["text"].strip()
        
        
        if len(text) < 2:
            return ""
        
       
        if is_whisper_hallucination(text):
            return ""
        
       
        if len(text) > 200:
            return ""
        
        print(f"You: {text}")
        return text
        
    except Exception as e:
        return ""

def is_whisper_hallucination(text):
    """Detect common Whisper hallucinations"""
    text_lower = text.lower()
    
    
    hallucinations = [
        "thank you for watching",
        "subscribe",
        "english translation",
        "transcribed by",
        "translation by",
        "subtitles by"
    ]
    
    for phrase in hallucinations:
        if phrase in text_lower:
            return True
    
    
    words = text.split()
    if len(words) > 5:
        
        first_half = " ".join(words[:len(words)//2])
        second_half = " ".join(words[len(words)//2:])
        if first_half == second_half:
            return True
    
    return False

def ask_gemma(prompt: str) -> str:
    global conversation_history, conversation_active
    
    
    conversation_active = True
    
  
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
    
   
    system_prompt = f"""You are Argon, a helpful AI assistant having a conversation.
Be direct, helpful, and conversational. Keep responses reasonably short.
Avoid excessive emojis or overly enthusiastic language.

Current time: {current_time}
Current date: {current_date}

Give natural, helpful responses without being too chatty.

"""
    
    
    if conversation_history:
        context = "\n".join([f"You: {h}" if i % 2 == 0 else f"Argon: {h}" 
                           for i, h in enumerate(conversation_history[-4:])])  # Only last 2 exchanges
        full_prompt = f"{system_prompt}Recent conversation:\n{context}\n\nYou: {prompt}\nArgon:"
    else:
        full_prompt = f"{system_prompt}You: {prompt}\nArgon:"
    
    try:
        timeout = 45
        
        print(random.choice(THINKING_RESPONSES))
        result = subprocess.run(
            ["ollama", "run", "gemma3:4b"],
            input=full_prompt,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            response = result.stdout.strip()
            
            conversation_history.append(prompt)
            conversation_history.append(response)
            
            
            if len(conversation_history) > 8: 
                conversation_history = conversation_history[-8:]
                
            return response
        else:
            return "Sorry, I'm having trouble processing that."
    except subprocess.TimeoutExpired:
        return "That's taking too long to process. Can you rephrase?"
    except Exception as e:
        return "I encountered an error. Please try again."

def speak(text):
    global is_speaking, interrupt_requested
    print(f"Argon: {text}")
    
    # Remove emojis 
    clean_text = re.sub(r'[^\w\s.,!?\-]', '', text)
    
    is_speaking = True
    interrupt_requested = False
    
    
    os.system(f'say "{clean_text}"')
    
    is_speaking = False

def handle_wake_word(text):
    """Check for wake words"""
    global conversation_active
    wake_words = ['argon', 'hey argon', 'hello argon']
    
    if any(wake in text.lower() for wake in wake_words):
        conversation_active = True
        response = random.choice(WAKE_RESPONSES)
        speak(response)
        return True
    return False

def handle_casual_commands(text):
    """Handle casual conversation starters and commands"""
    global conversation_active
    text_lower = text.lower()
    
    if any(phrase in text_lower for phrase in ['what time', 'time']):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"It's {current_time} right now.")
        conversation_active = True
        return True
    
    elif any(phrase in text_lower for phrase in ['what date', 'today']):
        current_date = datetime.datetime.now().strftime("%A, %B %d")
        speak(f"Today is {current_date}.")
        conversation_active = True
        return True
    
    elif any(phrase in text_lower for phrase in ['how are you', 'how\'s it going', 'what\'s up']):
        responses = [
            "I'm good. How about you?",
            "Fine. What's going on?",
            "All good. What do you need?",
            "I'm well. How are you?"
        ]
        speak(random.choice(responses))
        conversation_active = True
        return True
    
    elif any(phrase in text_lower for phrase in ['let\'s chat', 'talk to me', 'conversation']):
        starter = random.choice(CONVERSATION_STARTERS)
        speak(starter)
        conversation_active = True
        return True
    
    elif any(phrase in text_lower for phrase in ['goodbye', 'bye', 'see you', 'talk later', 'go offline']):
        speak("Going offline. Goodbye.")
        return "EXIT"
    
    return False

def main():
    global conversation_active
    print("=" * 40)
    print("ARGON - AI Assistant")
    print("=" * 40)
    print("Say 'Hey Argon' to start")
    print("Say 'go offline' to exit")
    print("=" * 40)
    
    speak("Hello, I'm Argon.")
    
    while True:
        user_text = listen()
        if not user_text or len(user_text.strip()) == 0:
            continue
        
        
        if handle_wake_word(user_text):
            continue
        
        # Handle casual commands
        result = handle_casual_commands(user_text)
        if result == "EXIT":
            break
        elif result:
            continue
        
        
        if not conversation_active and len(user_text.split()) > 1:
            conversation_active = True
        
       
        if conversation_active:
            reply = ask_gemma(user_text)
            if reply:
                speak(reply)

if __name__ == "__main__":
    main()
