from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from config import get_content_dir, get_data_dir
from data_loader import DataLoader
from engine import PaperEngine, PaperRequest
from models import Paper, Question
from pdf_exporter import PDFExportError, PDFExporter

PROJECT_DIR = Path(__file__).resolve().parent
QUESTION_TYPES = ("选择题", "填空题", "解答题")
DIFFICULTIES = ("基础题", "综合题", "拓展题")


st.set_page_config(
    page_title="考研数学《880》智能拼好卷",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#22211d; --paper:#f6f1e7; --red:#a53727; --muted:#756f65; --line:#d8d0c1; }
        [data-testid="stAppViewContainer"] { background:
          radial-gradient(circle at 20% 15%, rgba(165,55,39,.06), transparent 26rem),
          repeating-linear-gradient(0deg, rgba(80,70,55,.018) 0, rgba(80,70,55,.018) 1px, transparent 1px, transparent 5px), var(--paper); }
        [data-testid="stHeader"] { background:transparent; }
        [data-testid="stSidebar"] { background:#e9e1d3; border-right:1px solid #cbc0ae; }
        html, body, [class*="st-"] { font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei","PingFang SC","Microsoft YaHei",sans-serif; color:var(--ink); }
        .block-container { max-width:1180px; padding-top:2.1rem; padding-bottom:5rem; }
        .hero { position:relative; padding:2.4rem 2.7rem 2rem; border:1px solid var(--line); border-top:6px solid var(--red);
          background:rgba(255,253,247,.76); box-shadow:0 18px 60px rgba(70,51,30,.08); margin-bottom:1.5rem; overflow:hidden; }
        .hero:after { content:"880"; position:absolute; right:1.2rem; bottom:-2.7rem; font-size:9rem; font-weight:800; color:rgba(165,55,39,.055); }
        .eyebrow { color:var(--red); letter-spacing:.22em; font:700 .72rem sans-serif; text-transform:uppercase; }
        .hero h1 { margin:.45rem 0 .5rem; font-size:clamp(2rem,4vw,3.6rem); line-height:1.14; letter-spacing:-.04em; }
        .hero p { max-width:48rem; color:var(--muted); margin:0; }
        .metric-strip { display:flex; flex-wrap:wrap; gap:1px; background:var(--line); border:1px solid var(--line); margin-bottom:1.5rem; }
        .metric-cell { flex:1; min-width:145px; background:rgba(255,253,247,.9); padding:1rem 1.2rem; }
        .metric-cell b { display:block; font-size:1.45rem; color:var(--red); } .metric-cell span { color:var(--muted); font-size:.76rem; }
        .paper-title { border-bottom:2px solid var(--ink); padding-bottom:.85rem; margin:1.2rem 0 2rem; }
        .paper-title small { color:var(--red); letter-spacing:.16em; font-family:sans-serif; }
        .type-heading { display:flex; align-items:center; gap:.8rem; margin:2.2rem 0 1rem; }
        .type-heading span { display:grid; place-items:center; width:2rem; height:2rem; background:var(--red); color:white; border-radius:50%; font-weight:800; }
        .type-heading h2 { margin:0; font-size:1.45rem; }
        .question-card { background:rgba(255,253,247,.88); border:1px solid var(--line); border-left:4px solid var(--ink); padding:1.25rem 1.5rem; margin:.8rem 0; }
        .question-meta { color:var(--muted); font:.72rem sans-serif; letter-spacing:.05em; margin-bottom:.7rem; }
        .tag { display:inline-block; border:1px solid #c6bca9; padding:.16rem .48rem; margin:.15rem .22rem .15rem 0; border-radius:999px; font-size:.7rem; color:#615a4f; }
        .missing-stem { color:#9a5b51; border:1px dashed #c89c92; padding:.8rem; background:#fff8f4; }
        [data-testid="stExpander"] { border-color:var(--line); background:rgba(255,253,247,.6); }
        .stButton > button, .stDownloadButton > button { border-radius:0; border:1px solid var(--ink); font-weight:700; }
        .stButton > button[kind="primary"] { background:var(--red); border-color:var(--red); }
        div[data-testid="stAlert"] { border-radius:0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="正在编目题库……")
def load_bank(metadata_path: str, content_path: str):
    return DataLoader(metadata_path, [content_path]).load()


def chapter_number(question: Question) -> int:
    match = re.match(r"(\d+)-", question.id)
    return int(match.group(1)) if match else 999


def unique_chapters(questions: list[Question]) -> list[str]:
    order: dict[str, int] = {}
    for question in questions:
        order[question.chapter] = min(order.get(question.chapter, 999), chapter_number(question))
    return sorted(order, key=lambda chapter: (order[chapter], chapter))


def subject_chapters(chapters: list[str], questions: list[Question]) -> dict[str, list[str]]:
    number_by_chapter = {
        chapter: min((chapter_number(q) for q in questions if q.chapter == chapter), default=999)
        for chapter in chapters
    }
    return {
        "高等数学": [c for c in chapters if 1 <= number_by_chapter[c] <= 9],
        "线性代数": [c for c in chapters if 10 <= number_by_chapter[c] <= 15],
        "概率统计": [c for c in chapters if 16 <= number_by_chapter[c]],
    }


def render_question(question: Question, number: int) -> None:
    st.markdown('<div class="question-card">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="question-meta">NO. {number:02d}　·　{question.id}　·　{question.chapter}　·　{question.section}</div>',
        unsafe_allow_html=True,
    )
    if question.content_missing:
        st.markdown(f'<div class="missing-stem">{question.stem}</div>', unsafe_allow_html=True)
    else:
        st.markdown(question.stem)
    if question.options:
        columns = st.columns(2)
        for index, option in enumerate(question.options):
            with columns[index % 2]:
                st.markdown(option)
    tags = [*question.tags, *question.core_knowledge[:2]]
    if tags:
        st.markdown("".join(f'<span class="tag">{tag}</span>' for tag in tags), unsafe_allow_html=True)
    with st.expander("详细解析与踩坑点", expanded=False):
        if question.answer:
            st.markdown("**参考答案**")
            st.markdown(question.answer)
        st.markdown("**详细解析**")
        st.markdown(question.analysis or "暂无详细解析。")
        st.markdown("**踩坑点**")
        st.markdown(question.pitfall_analysis or "暂无踩坑提示。")
    st.markdown("</div>", unsafe_allow_html=True)


def prepare_pdf(paper: Paper, include_solutions: bool, state_key: str) -> None:
    try:
        with st.spinner("正在排版 A4 试卷……"):
            st.session_state[state_key] = PDFExporter(PROJECT_DIR).export(paper, include_solutions)
    except PDFExportError as exc:
        st.error(str(exc))


inject_styles()
st.markdown(
    """<section class="hero"><div class="eyebrow">Postgraduate Mathematics · Paper Atelier</div>
    <h1>考研数学《880》<br>智能拼好卷</h1>
    <p>让每一次组卷都有明确覆盖：按章节、题型与难度倾向抽取，优先分散核心考点，把错题风险留在考场之外。</p></section>""",
    unsafe_allow_html=True,
)

default_path = str(get_data_dir(PROJECT_DIR))
default_content_path = str(get_content_dir(PROJECT_DIR))
with st.sidebar:
    st.markdown("## 组卷编辑台")
    with st.expander("数据源", expanded=False):
        data_path = st.text_input("元数据目录", value=default_path)
        content_path = st.text_input("题目正文目录", value=default_content_path)
        if st.button("重新扫描题库", use_container_width=True):
            load_bank.clear()
            st.session_state.pop("paper", None)
            st.rerun()

report = load_bank(data_path, content_path)
questions = report.questions
chapters = unique_chapters(questions)
subjects = subject_chapters(chapters, questions)

st.markdown(
    f"""<div class="metric-strip">
    <div class="metric-cell"><b>{len(questions)}</b><span>题目元数据</span></div>
    <div class="metric-cell"><b>{report.matched_bodies}</b><span>已关联正文</span></div>
    <div class="metric-cell"><b>{len(chapters)}</b><span>可选章节</span></div>
    <div class="metric-cell"><b>{report.json_files} + {report.markdown_files}</b><span>JSON + Markdown</span></div>
    </div>""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 01 · 题量")
    choice_count = st.slider("选择题", 0, 15, 5)
    blank_count = st.slider("填空题", 0, 10, 3)
    solution_count = st.slider("解答题", 0, 8, 3)

    st.markdown("### 02 · 章节")
    if "selected_chapters" not in st.session_state:
        st.session_state.selected_chapters = chapters
    controls = st.columns(2)
    if controls[0].button("全选", use_container_width=True):
        st.session_state.selected_chapters = chapters
    if controls[1].button("清空", use_container_width=True):
        st.session_state.selected_chapters = []
    for subject, items in subjects.items():
        if st.button(f"+ {subject}", key=f"subject_{subject}", use_container_width=True):
            st.session_state.selected_chapters = list(dict.fromkeys([*st.session_state.selected_chapters, *items]))
    selected_chapters = st.multiselect("当前复习章节", chapters, key="selected_chapters")

    st.markdown("### 03 · 难度倾向")
    difficulty_weights = {
        "基础题": st.slider("基础题权重", 0, 5, 3),
        "综合题": st.slider("综合题权重", 0, 5, 3),
        "拓展题": st.slider("拓展题权重", 0, 5, 1),
    }
    available_tags = sorted({tag for question in questions for tag in question.tags})
    preferred = [tag for tag in ("高频真题变式", "易错概念", "压轴题型") if tag in available_tags]
    other = [tag for tag in available_tags if tag not in preferred]
    selected_tag = st.selectbox("专项标签", ["全部", *preferred, *other])

    st.markdown("### 04 · 试卷署名")
    paper_title = st.text_input("试卷标题", "【拼好卷01】全科考点交叉扫描")
    random_seed = st.number_input("随机种子（便于复现）", min_value=0, value=880, step=1)
    generate = st.button("✦ 开始智能组卷", type="primary", use_container_width=True)

if report.warnings:
    for warning in report.warnings:
        st.warning(warning)

if generate:
    if not questions:
        st.error("没有可用于组卷的题目，请先修复数据源。")
    elif not selected_chapters:
        st.error("请至少选择一个章节。")
    elif not any(difficulty_weights.values()):
        st.error("至少保留一种难度权重。")
    else:
        request = PaperRequest(
            title=paper_title,
            counts={"选择题": choice_count, "填空题": blank_count, "解答题": solution_count},
            chapters=set(selected_chapters),
            difficulty_weights=difficulty_weights,
            tag=selected_tag,
            seed=int(random_seed),
        )
        st.session_state.paper = PaperEngine(questions).generate(request)
        st.session_state.pop("pdf_clean", None)
        st.session_state.pop("pdf_solutions", None)

paper: Paper | None = st.session_state.get("paper")
if not paper:
    st.info("在左侧设定题量、章节与难度，然后点击“开始智能组卷”。")
else:
    for warning in paper.warnings:
        st.warning(warning)
    st.markdown(
        f'<div class="paper-title"><small>GENERATED PAPER · SEED {paper.seed}</small><h2>{paper.title}</h2>'
        f'<p>共 {len(paper.questions)} 题 · 覆盖 {len({k for q in paper.questions for k in q.core_knowledge})} 个核心考点</p></div>',
        unsafe_allow_html=True,
    )
    index = 0
    for section_no, question_type in enumerate(QUESTION_TYPES, 1):
        group = paper.by_type(question_type)
        if not group:
            continue
        st.markdown(
            f'<div class="type-heading"><span>{section_no}</span><h2>{question_type}</h2></div>',
            unsafe_allow_html=True,
        )
        for question in group:
            index += 1
            render_question(question, index)

    st.markdown("### 导出到 GoodNotes / 平板")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("排版纯享版 PDF", use_container_width=True):
            prepare_pdf(paper, False, "pdf_clean")
        if st.session_state.get("pdf_clean"):
            st.download_button(
                "下载【试卷纯享版.pdf】",
                st.session_state.pdf_clean,
                file_name=f"{paper.title}_试卷纯享版.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    with col2:
        if st.button("排版解析版 PDF", use_container_width=True):
            prepare_pdf(paper, True, "pdf_solutions")
        if st.session_state.get("pdf_solutions"):
            st.download_button(
                "下载【试卷+解析与踩坑提示版.pdf】",
                st.session_state.pdf_solutions,
                file_name=f"{paper.title}_试卷+解析与踩坑提示版.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
