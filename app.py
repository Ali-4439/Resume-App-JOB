import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from fpdf import FPDF
import io

# إعداد واجهة التطبيق
st.set_page_config(page_title="مُحسّن السيرة الذاتية الذكي", page_icon="🚀", layout="centered")

# --- الإعدادات ومفتاح API ---
st.sidebar.header("⚙️ الإعدادات")
api_key = st.sidebar.text_input("أدخل مفتاح Gemini API الخاص بك", type="password")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- دوال مساعدة ---
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def create_pdf(text, filename="document.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    # ملاحظة: لدعم اللغة العربية في PDF ستحتاج لتحميل خط Arial.ttf ووضعه في نفس المجلد
    # pdf.add_font("Arial", "", "Arial.ttf", uni=True) 
    # pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", size=12) # استخدم هذا للغة الإنجليزية حالياً
    
    # معالجة النص ليتناسب مع PDF
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'))
    
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return pdf_bytes

# --- الذاكرة المؤقتة للتطبيق ---
if 'base_cv' not in st.session_state:
    st.session_state.base_cv = None

# --- الواجهة الرئيسية ---
st.title("🚀 النظام الذكي لمطابقة السير الذاتية")

# 1. رفع السيرة الذاتية (لمرة واحدة)
if st.session_state.base_cv is None:
    st.info("لم يتم رفع سيرة ذاتية بعد. يرجى رفع نسختك الأساسية.")
    uploaded_file = st.file_uploader("ارفع السيرة الذاتية (PDF)", type="pdf")
    if uploaded_file is not None:
        st.session_state.base_cv = extract_text_from_pdf(uploaded_file)
        st.success("✅ تم حفظ السيرة الذاتية بنجاح! يمكنك الآن التقديم على الوظائف.")
else:
    st.success("✅ توجد سيرة ذاتية محفوظة مسبقاً في النظام.")
    if st.button("🗑️ حذف السيرة المحفوظة لرفع واحدة جديدة"):
        st.session_state.base_cv = None
        st.experimental_rerun()

st.markdown("---")

# 2. تفاصيل الوظيفة الجديدة
st.subheader("📋 تفاصيل الوظيفة والتقديم")
job_title = st.text_input("اسم الوظيفة المقدم عليها")
company_name = st.text_input("اسم الشركة (اختياري، يفيد في خطاب التغطية)")
job_description = st.text_area("الصق مهام ومتطلبات الوظيفة هنا", height=150)
custom_edits = st.text_input("أي تعديلات أو إضافات خاصة تريد مني كتابتها في السيرة؟ (اختياري)")

# 3. الخيارات
col1, col2 = st.columns(2)
with col1:
    translate_arabic = st.checkbox("ترجمة السيرة إلى العربية")
with col2:
    create_cover_letter = st.checkbox("كتابة Cover Letter")
    cover_letter_lang = st.selectbox("لغة خطاب التغطية", ["English", "العربية"])

# 4. المعالجة
if st.button("معالجة واستخراج الملفات ⚙️"):
    if not api_key:
        st.error("❌ يرجى إدخال مفتاح API في القائمة الجانبية أولاً.")
    elif not st.session_state.base_cv:
        st.error("❌ يرجى رفع السيرة الذاتية الأساسية أولاً.")
    elif not job_title or not job_description:
        st.error("❌ يرجى إدخال اسم الوظيفة ومتطلباتها كحد أدنى.")
    else:
        with st.spinner("جاري تحليل متطلبات الوظيفة وإعادة صياغة السيرة..."):
            try:
                # هندسة الأوامر (Prompt Engineering) للسيرة الذاتية
                lang_instruction = "Translate the entire CV to professional Arabic." if translate_arabic else "Keep it in English."
                cv_prompt = f"""
                You are an expert ATS CV writer. 
                Here is my base CV: {st.session_state.base_cv}
                Here is the Job Title: {job_title}
                Here is the Job Description: {job_description}
                User custom edits: {custom_edits}
                
                Task: Rewrite and tailor my CV to perfectly match the job description. Emphasize matching skills.
                Keep it under 2 pages. Organize with clear headings (Summary, Experience, Education, Skills).
                {lang_instruction}
                Only output the final CV text.
                """
                
                response_cv = model.generate_content(cv_prompt)
                tailored_cv = response_cv.text
                
                st.success("✅ تمت معالجة السيرة الذاتية بنجاح!")
                st.text_area("معاينة السيرة المعدلة:", tailored_cv, height=300)
                
                # إنشاء ملف PDF للسيرة
                cv_pdf_bytes = create_pdf(tailored_cv)
                st.download_button(
                    label="📄 تحميل السيرة الذاتية (PDF)",
                    data=cv_pdf_bytes,
                    file_name="Tailored_CV.pdf",
                    mime="application/pdf"
                )

                # هندسة الأوامر لخطاب التغطية
                if create_cover_letter:
                    st.markdown("---")
                    with st.spinner("جاري كتابة خطاب التغطية..."):
                        cl_prompt = f"""
                        Write a professional Cover Letter for the position of {job_title} at {company_name}.
                        Base it on this job description: {job_description}
                        And my tailored CV summary: {tailored_cv[:1000]}
                        Write it in {cover_letter_lang}.
                        Only output the cover letter text.
                        """
                        response_cl = model.generate_content(cl_prompt)
                        cl_text = response_cl.text
                        
                        st.success("✅ تم إنشاء خطاب التغطية!")
                        st.text_area("معاينة خطاب التغطية:", cl_text, height=200)
                        
                        cl_pdf_bytes = create_pdf(cl_text)
                        st.download_button(
                            label="📄 تحميل خطاب التغطية (PDF)",
                            data=cl_pdf_bytes,
                            file_name="Cover_Letter.pdf",
                            mime="application/pdf"
                        )
                        
            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
