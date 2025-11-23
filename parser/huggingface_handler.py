import logging
from typing import Optional
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Импортируем Config из родительской директории
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

# Инициализируем логирование из Config
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(Config.LOG_FORMAT, Config.LOG_DATE_FORMAT))
    logger.addHandler(handler)
logger.setLevel(Config.LOG_LEVEL)

class HuggingFaceHandler:
    def __init__(self, model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        """
        Инициализирует обработчик для работы с моделями Hugging Face.
        
        Args:
            model_name (str): TinyLlama/TinyLlama-1.1B-Chat-v1.0
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        
    def load_model(self) -> None:
        """Загружает модель и токенизатор."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                dtype=torch.float16,  # Используем float16 для оптимизации памяти
                device_map="auto",  # Автоматическое определение устройства (CPU/GPU)
                trust_remote_code=True  # Разрешаем использование удаленного кода для модели
            )
            print(f"Модель {self.model_name} успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {str(e)}")
            raise
    
    def generate_response(self, prompt: str, max_length: int = 5000, temperature: float = 0.7) -> Optional[str]:
        """
        Генерирует ответ на основе входного текста.
        
        Args:
            prompt (str): Входной текст
            max_length (int): Максимальная длина генерируемого текста
            temperature (float): Температура генерации (влияет на креативность)
            
        Returns:
            str: Сгенерированный текст или None в случае ошибки
        """
        if not self.model or not self.tokenizer:
            logger.warning("Модель не загружена. Вызовите метод load_model() сначала.")
            return None
            
        try:
            # Форматируем промпт для чат-модели
            formatted_prompt = f"<human>: {prompt}\n<assistant>:"
            
            # Подготавливаем входной текст
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.model.device)
            
            # Генерируем ответ
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,  # Используем nucleus sampling
                    top_k=50,   # Ограничиваем выбор топ-50 токенов
                    repetition_penalty=1.2,  # Штраф за повторения
                    pad_token_id=self.tokenizer.eos_token_id,
                    num_return_sequences=1,
                    no_repeat_ngram_size=3  # Избегаем повторения 3-грамм
                )
            
            # Декодируем результат
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Извлекаем только ответ ассистента
            response = response.split("<assistant>:")[-1].strip()
            
            return response
            
        except Exception as e:
            print(f"Ошибка при генерации ответа: {str(e)}")
            return None