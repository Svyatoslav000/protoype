import streamlit as st
import tempfile
import os
from datetime import datetime

from config import HF_MODEL
from pubmed_search import get_abstracts_by_inn
from inference_api import HuggingFaceInference
from sample_size import calculate_sample_size
from synopsis_generator import SynopsisGenerator

st.set_page_config(page_title="BE AI Designer", layout="wide")
st.title("💊 AI-проектирование исследований биоэквивалентности")
st.markdown("---")

# Инициализация AI (локальная модель)
@st.cache_resource
def init_ai():
    return HuggingFaceInference(model_name=HF_MODEL)

ai_client = init_ai()


with st.sidebar:
    st.header("Параметры исследования")
    inn = st.text_input("INN (например, Ibuprofen)", "Ibuprofen")
    dosage_form = st.text_input("Лекарственная форма", "таблетки")
    dosage_strength = st.text_input("Дозировка", "200 мг")
    mode = st.selectbox("Режим приёма", ["натощак", "после еды", "оба"])
    design_pref = st.selectbox("Предпочтительный дизайн", ["авто", "2x2 crossover", "репликативный (RSABE)"])
    rsabe = st.checkbox("Использовать RSABE (если CV > 30%)")
    dropout = st.slider("Ожидаемый dropout, %", 0, 40, 20) / 100

    st.markdown("---")
    st.subheader("Шаблон синопсиса")
    template_file = st.file_uploader("Загрузите файл .docx", type=["docx"])
    if template_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(template_file.getvalue())
            template_path = tmp.name
        st.success("✅ Шаблон загружен")
    else:
        template_path = "Шаблон Синопсиса Протокола.docx"
        if not os.path.exists(template_path):
            st.error("❌ Файл шаблона не найден! Положите его в папку проекта или загрузите выше.")
            st.stop()

if st.sidebar.button("🚀 Запустить проектирование", type="primary"):
    with st.spinner("🔍 Поиск в PubMed..."):
        abstracts = get_abstracts_by_inn(inn)
        if abstracts:
            st.info(f"Найдено аннотаций: {len(abstracts)} символов")
            with st.expander("Показать фрагмент"):
                st.text(abstracts[:1000])
        else:
            st.warning("Аннотации не найдены. Будут использованы литературные данные.")

    # Извлечение параметров через локальную модель
    with st.spinner("🤖 AI анализирует литературу..."):
        params = ai_client.extract_pharmacokinetic_params(abstracts, inn)
        if params:
            cv = params.get('cv_intra')
            t_half = params.get('t_half')
            if cv is not None:
                st.success(f"✅ Извлечено: CVintra = {cv}")
            else:
                st.warning("⚠️ CVintra не найден, потребуется ручной ввод.")
            if t_half is not None:
                st.success(f"✅ T½ = {t_half} ч")
            else:
                st.warning("⚠️ T½ не найден, потребуется ручной ввод.")
        else:
            cv = None
            t_half = None
            st.warning("⚠️ Не удалось извлечь параметры, будет ручной ввод.")

    # Ручной ввод, если параметры не определены
    if cv is None:
        cv = st.number_input("CVintra (например, 0.25)", 0.05, 1.0, 0.25, key="cv_in")
    if t_half is None:
        t_half = st.number_input("Период полувыведения T½ (часы)", 0.5, 100.0, 4.0, key="t_half_in")

    # Расчёт выборки
    N, N_total = calculate_sample_size(cv, dropout=dropout)

    # Выбор дизайна
    if design_pref == "авто":
        design = "репликативный (RSABE)" if (rsabe and cv > 0.3) else "2x2 crossover"
    else:
        design = design_pref

    washout = int(t_half * 5 / 24) + 1  # отмывка в днях


    rationale = ai_client.generate_rationale({
        'inn': inn,
        'cv': cv,
        'mode': mode,
        'design': design,
        'sample_size': N_total
    }) or "Дизайн выбран согласно Решению №85."


    data = {
        "Название протокола": f"Исследование биоэквивалентности препаратов {inn}",
        "Идентификационный номер протокола": f"BE-{inn[:3].upper()}-{datetime.now():%Y%m}",
        "Спонсор исследования": "ООО \"ФармаКом\"",
        "Исследовательский центр": "ООО \"Центр клинических исследований\"",
        "Биоаналитическая лаборатория": "ООО \"Аналитика\"",
        "Название исследуемого препарата": f"Тест {inn} {dosage_form} {dosage_strength}",
        "Действующее вещество": inn,
        "Препарат Т": f"Тест {inn}",
        "Препарат R": f"{inn} оригинальный",
        "Режим приема": mode,
        "Аналит": inn,
        "Цель исследования": f"Оценка биоэквивалентности препаратов {inn} {mode}",
        "Дизайн исследования": design,
        "Методология исследования": f"Открытое рандомизированное двухпериодное перекрестное исследование с отмывочным периодом {washout} дней",
        "Количество добровольцев": f"Включено {N_total} добровольцев (с учётом {dropout*100:.0f}% выбывших)",
        "Исследуемый препарат (T)": f"{inn} {dosage_strength}",
        "Референтный препарат (R)": f"{inn} оригинальный",
        "Продолжительность исследования": f"до {washout*2+14} дней",
        "Изучаемые фармакокинетические параметры": "Cmax, AUC0-t, Tmax, T½",
        "Критерии биоэквивалентности": "90% ДИ для отношения геометрических средних Cmax и AUC0-t в пределах 80.00–125.00%",
        "Расчет размера выборки": f"На основе CVintra = {cv:.2f} получено N={N}, с учётом выбывания {dropout*100:.0f}% итого {N_total}.",
        "Обоснование дизайна": rationale,
        "Число добровольцев в группу": N_total // 2,
        "Страховая компания": "ООО \"СК \"Согласие\"",
        "Номер версии Протокола": f"Версия 1.0 от {datetime.now():%d.%m.%Y}",
    }

    # Генерация документа
    generator = SynopsisGenerator(template_path)
    filled_doc = generator.fill_template(data)

    # Сохранение
    docx_filename = f"synopsis_{inn}_{datetime.now():%Y%m%d_%H%M}.docx"
    generator.save_docx(filled_doc, docx_filename)

    st.success("✅ Синопсис успешно сгенерирован!")
    with open(docx_filename, "rb") as f:
        st.download_button("📥 Скачать DOCX", f, file_name=docx_filename)

    # Предпросмотр
    st.subheader("📄 Предварительный просмотр (первые 1000 символов)")
    preview = "\n".join([p.text for p in filled_doc.paragraphs if p.text][:5])
    st.text(preview[:1000])