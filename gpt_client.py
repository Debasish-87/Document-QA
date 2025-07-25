import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API Key
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

def get_gemini_response(question, context_chunks):
    try:
        # Combine context from top-k chunks
        context = "\n\n".join(context_chunks)
        prompt = (
            "You are an assistant answering questions based ONLY on the provided document context.\n"
            "If the answer is not found, reply: 'The document does not specify this.'\n\n"
            f"DOCUMENT:\n{context}\n\nQUESTION:\n{question}"
        )

        generation_config = {
            "temperature": 0.2,
            "top_p": 1.0,
            "top_k": 32,
            "max_output_tokens": 1024,
        }

        gemini_model = genai.GenerativeModel(
            model_name="models/gemini-1.5-flash",
            generation_config=generation_config,
        )

        response = gemini_model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"
