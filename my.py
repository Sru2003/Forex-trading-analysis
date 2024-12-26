from langdetect import detect
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Load mT5 model
model_name = "google/mt5-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# Function to auto-detect language and translate to English
def auto_translate_to_english(text):
    # Detect language
    detected_language = detect(text)
    print(f"Detected Language: {detected_language}")
    
    # Prepare prompt for translation
    prompt = f"Translate from {detected_language} to English: {text}"
    inputs = tokenizer.encode(prompt, return_tensors="pt")
    
    # Generate translation
    outputs = model.generate(inputs)
    translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return translated_text

# Example input text
input_text = "Hola, ¿cómo estás?"
translated_text = auto_translate_to_english(input_text)
print("Translated Text:", translated_text)
