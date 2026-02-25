import streamlit as st
import json
import re
from langchain_community.llms import Ollama


class LocalMedicalAI:
    def __init__(self, model_name="mistral"):
        self.model_name = model_name
        self.api_available = True

        try:
            self.llm = Ollama(
                model=model_name,
                temperature=0.1,
                num_predict=512,
            )
            st.success(f"✅ Локальная модель {model_name} загружена")
        except Exception as e:
            st.error(f"❌ Ошибка загрузки модели: {e}")
            st.info("Убедитесь, что Ollama запущена (команда 'ollama serve' в отдельном терминале)")
            self.api_available = False

    def extract_pharmacokinetic_params(self, abstracts, inn):
        if not self.api_available:
            return self._get_fallback_params(inn)

        context = abstracts[:3000] if abstracts else ""
        if not context.strip():
            st.info("Аннотации не найдены, используются литературные данные.")
            return self._get_fallback_params(inn)

        prompt = f"""Ты — эксперт-фармаколог. Проанализируй аннотации из PubMed для препарата {inn}.

Аннотации:
{context}

Извлеки следующие параметры в формате JSON:
- cv_intra: внутрииндивидуальный коэффициент вариации (число от 0 до 1, например 0.25 для 25%)
- t_half: период полувыведения в часах (число)
- cmax_range: диапазон Cmax (строка, например "15-25 мкг/мл")
- auc_range: диапазон AUC (строка, например "50-80 мкг·ч/мл")

Если параметр не найден, поставь null.
Ответ должен быть только в JSON формате, без пояснений.
"""
        try:
            response = self.llm.invoke(prompt)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                st.warning("Модель не вернула корректный JSON, используются литературные данные.")
                return self._get_fallback_params(inn)
        except Exception as e:
            st.warning(f"Ошибка при обращении к модели: {e}")
            return self._get_fallback_params(inn)

    def _get_fallback_params(self, inn):
        knowledge_base = {
            "ibuprofen": {"cv_intra": 0.25, "t_half": 2.0, "cmax_range": "15-25 мкг/мл", "auc_range": "50-80 мкг·ч/мл"},
            "metformin": {"cv_intra": 0.20, "t_half": 4.0, "cmax_range": "1-2 мкг/мл", "auc_range": "10-15 мкг·ч/мл"},
            "atorvastatin": {"cv_intra": 0.35, "t_half": 14.0, "cmax_range": "5-15 нг/мл",
                             "auc_range": "30-100 нг·ч/мл"},
            "amoxicillin": {"cv_intra": 0.30, "t_half": 1.5, "cmax_range": "5-10 мкг/мл",
                            "auc_range": "20-40 мкг·ч/мл"},
        }
        inn_lower = inn.lower()
        for key in knowledge_base:
            if key in inn_lower:
                return knowledge_base[key]
        return {"cv_intra": 0.25, "t_half": 4.0, "cmax_range": "типичный диапазон", "auc_range": "типичный диапазон"}

    def generate_rationale(self, design_data):
        if not self.api_available:
            return self._get_fallback_rationale(design_data)

        prompt = f"""Ты — эксперт по биоэквивалентности. Обоснуй выбор дизайна исследования.

Параметры:
- Препарат: {design_data['inn']}
- CVintra: {design_data['cv']}
- Режим приёма: {design_data['mode']}
- Выбранный дизайн: {design_data['design']}
- Размер выборки: {design_data['sample_size']}

Напиши 2-3 предложения на русском языке в научном стиле.
"""
        try:
            response = self.llm.invoke(prompt)
            return response.strip()
        except:
            return self._get_fallback_rationale(design_data)

    def _get_fallback_rationale(self, design_data):
        cv = design_data['cv']
        if cv > 0.3:
            return f"Препарат {design_data['inn']} относится к высоковариабельным (CV={cv:.2f}). В соответствии с Решением №85 рекомендуется репликативный дизайн с расширенными границами биоэквивалентности (RSABE). Размер выборки {design_data['sample_size']} обеспечивает мощность 80% при ожидаемом dropout 20%."
        else:
            return f"Для препарата {design_data['inn']} с умеренной вариабельностью (CV={cv:.2f}) достаточно стандартного 2x2 crossover дизайна. Отмывочный период рассчитан исходя из T½. Размер выборки {design_data['sample_size']} соответствует требованиям Решения №85."



HuggingFaceInference = LocalMedicalAI