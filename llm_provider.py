import os
import logging

logger = logging.getLogger(__name__)

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini")

if MODEL_PROVIDER == "openai":
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14")

def get_openai_client():
    return openai.OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

def get_gemini_model():
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    return genai.GenerativeModel('gemini-2.0-flash')

def generate_response(messages: list, system_prompt: str) -> str:
    if MODEL_PROVIDER == "gemini":
        model = get_gemini_model()
        prompt = system_prompt + "\n\nИстория диалога:\n"
        for msg in messages:
            role = "Пользователь" if msg["role"] == "user" else "Ассистент"
            prompt += f"{role}: {msg['content']}\n"
        logger.info(f"[LLM] Gemini: длина промпта: {len(prompt)} символов")
        logger.debug(f"[LLM] Gemini: полный промпт:\n{prompt}")
        response = model.generate_content(prompt)
        logger.info(f"[LLM] Gemini: длина ответа: {len(response.text) if response and response.text else 0} символов")
        return response.text
    elif MODEL_PROVIDER == "openai":
        openai_client = get_openai_client()
        openai_messages = [
            {"role": "system", "content": system_prompt}
        ] + [
            {"role": msg["role"], "content": msg["content"]} for msg in messages
        ]
        logger.info(f"[LLM] OpenAI: сообщений в контексте: {len(openai_messages)}")
        logger.debug(f"[LLM] OpenAI: system_prompt: {system_prompt}")
        response = openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14"),
            messages=openai_messages,
            temperature=0.7,
            max_tokens=20024,
        )
        answer = response.choices[0].message.content
        logger.info(f"[LLM] OpenAI: длина ответа: {len(answer) if answer else 0} символов")
        return answer
    else:
        raise ValueError("Неизвестный провайдер модели") 