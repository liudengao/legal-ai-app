import streamlit as st
from openai import OpenAI
import json, re

st.set_page_config(page_title="社区矫正普法需求AI分析", page_icon="⚖️")
st.title("社区矫正普法需求 AI 智能分析系统")
st.write("基于《普法需求标签体系》与《调查问卷》，自动生成需求画像卡。")

# 替换为你自己的 API Key
client = OpenAI(api_key=st.secrets["DEEPSEEK_KEY"], base_url="https://api.deepseek.com")

# ================= 1. 数据映射字典 =================
# Q4 大领域映射 (+1)
q4_mapping = {
    "A. 社区矫正相关规定": ["T27", "T29"],
    "B. 找工作、上班、工资和社保": ["T19", "T20", "T21"],
    "C. 婚姻家庭、抚养赡养": ["T12", "T13"],
    "D. 邻里关系、房屋、宅基地": ["T03", "T04", "T07", "T09"],
    "E. 借钱欠债、合同、消费": ["T06", "T07", "T08"],
    "F. 交通事故、酒驾": ["T22", "T23"],
    "G. 治安处罚": ["T24", "T25"],
    "H. 防诈骗、网络赌博、网贷": ["T31", "T32"],
    "I. 帮人转账/借卡风险": ["T30"],
    "J. 继承、遗嘱": ["T14"],
    "K. 被侵权怎么维权": ["T15", "T10", "T11", "T18", "T34"],
    "L. 未成年人教育": ["T33"]
}

# Q5 具体话题映射 (+3)
q5_mapping = {
    "外出请假怎么报": ["T27"], "定期报告等要求": ["T27"], "考核奖惩": ["T27"],
    "撤销缓刑/收监": ["T27", "T29"],
    "劳动合同怎么签": ["T19"], "被拖欠工资怎么办": ["T19"], "工伤怎么认定": ["T20"],
    "社保没交的影响": ["T20"], "打零工被坑怎么维权": ["T21"], "有前科找工作被拒": ["T21"],
    "离婚怎么办、财产怎么分": ["T12"], "彩礼要不要退": ["T12"], "孩子抚养费": ["T13"],
    "老人赡养": ["T13"], "遇到家庭暴力": ["T13"],
    "邻居噪音/采光纠纷": ["T03"], "宅基地边界": ["T03"], "租房押金、提前退租": ["T07"],
    "买房过户、一房二卖": ["T04"], "物业费纠纷": ["T09"],
    "借条怎么写才有效": ["T06"], "利息多少算高利贷": ["T06"], "被催债怎么办": ["T06"],
    "定金订金、网购问题": ["T08"], "遇到霸王条款": ["T08"],
    "酒驾醉驾的后果": ["T22"], "出事故现场怎么处理": ["T23"], "对责任认定不服": ["T23"],
    "保险理赔怎么走": ["T23"],
    "打架斗殴的后果": ["T24"], "赌博、吸毒后果": ["T24"], "噪音扰民": ["T24"],
    "被处罚了不服": ["T25"],
    "常见骗术识别": ["T31"], "网络赌博": ["T32"], "套路贷、高息网贷": ["T32"],
    "被骗后怎么追回": ["T31"],
    "出借银行卡、电话卡": ["T30"], "帮人取钱、代收款": ["T30"], "跑分是什么": ["T30"],
    "法定继承顺序": ["T14"], "遗嘱怎么写": ["T14"], "遗产怎么分": ["T14"],
    "人身损害怎么赔偿": ["T15"], "名誉、隐私被侵犯": ["T10", "T11"], "网络暴力": ["T18"],
    "去哪申请法律援助": ["T34"],
    "监护人承担什么责任": ["T33"], "怎么管教孩子不违法": ["T33"], "孩子在学校遇到问题": ["T33"]
}

# 情景题 (Q6-Q10) 映射，选B/C/D命中标签 (+2)
scenario_tags = {
    "Q6": {"B": ["T27"], "C": ["T27"], "D": ["T27"]},
    "Q7": {"B": ["T19"], "C": ["T19"], "D": ["T19"]},
    "Q8": {"B": ["T31"], "C": ["T31"], "D": ["T31"]},
    "Q9": {"B": ["T30"], "C": ["T30"], "D": ["T30"]},
    "Q10": {"B": ["T03"], "C": ["T03"], "D": ["T03", "T34"]}
}

# ================= 2. 问卷 UI 表单 =================
with st.form("survey_form"):
    st.header("第一部分：基本情况")
    q1 = st.radio("Q1. 您的年龄段是？", ["A. 18-25", "B. 26-35", "C. 36-45", "D. 46-55", "E. 56及以上", "F. 不便回答"],
                  horizontal=True)
    q2 = st.radio("Q2. 您的最高学历是？",
                  ["A. 小学及以下", "B. 初中", "C. 高中/中专", "D. 大专", "E. 本科及以上", "F. 不便回答"],
                  horizontal=True)

    # === 补齐的 Q3 ===
    q3 = st.radio(
        "Q3. 您目前最主要的生活状态是？",
        ["A. 已稳定工作", "B. 打零工/灵活就业", "C. 正在找工作", "D. 上学或参加技能培训", "E. 暂时在家/其他",
         "F. 不便回答"],
        horizontal=True
    )

    st.divider()
    st.header("第二部分：兴趣话题")
    q4 = st.multiselect("Q4. 下面这些方面，您目前最想了解哪些？（最多选3项）", list(q4_mapping.keys()), max_selections=3)

    st.write("⬇️ 基于上述选择，请勾选具体想了解的话题（最多选3项）：")
    q5 = st.multiselect("Q5. 在您关心的方面里，具体想了解哪些？", list(q5_mapping.keys()), max_selections=3)

    st.divider()
    st.header("第三部分：情景小判断（素养测评）")
    q6 = st.radio("Q6. 矫正期间急事需离开本市，正确做法是？",
                  ["A.先请假获批再走", "B.先走，回来补招呼", "C.很快回来，不告诉别人", "D.不清楚"])
    q7 = st.radio("Q7. 入职要签劳动合同，哪种做法最稳妥？",
                  ["A.看清内容再签，自己留一份", "B.让签就签，不细看", "C.口头说好就行", "D.不清楚"])
    q8 = st.radio("Q8. 收到“低投入高回报”信息，您会？",
                  ["A.不信，直接删除", "B.有点心动，问问别人", "C.金额小，可以试试", "D.拿不准"])
    q9 = st.radio("Q9. 朋友借您银行卡转来路不明的钱并给好处费？",
                  ["A.坚决拒绝，可能违法", "B.碍于情面可能帮忙", "C.给好处费就可以帮", "D.不清楚是否违法"])
    q10 = st.radio("Q10. 邻居装修导致您家渗水沟通无果？",
                   ["A.先找社区调解，不成再诉讼", "B.直接找人上门理论", "C.只能自己忍着", "D.不知道怎么办"])

    st.divider()
    st.header("第四部分：宣讲形式与时间")
    q11 = st.radio("Q11. 您更容易接受哪种普法方式？",
                   ["A.真实案例故事讲解", "B.短视频、情景剧", "C.互动问答", "D.情景模拟演练", "E.一对一交流",
                    "F.图文宣传册"], horizontal=True)
    q12 = st.radio("Q12. 一次普法活动，多长时间最合适？",
                   ["A.20分钟以内", "B.30分钟左右", "C.45分钟左右", "D.1小时也可以"], horizontal=True)

    # === 补齐的 Q13 ===
    q13 = st.radio("Q13. 如果安排普法活动，您哪个时间比较方便？",
                   ["A. 工作日上午", "B. 工作日下午", "C. 周末", "D. 晚上", "E. 都可以"], horizontal=True)

    st.divider()
    st.header("第五部分：意见建议与个性化")
    q14 = st.text_area("Q14. 如果下次普法只讲一个主题，您最希望讲什么？",
                       placeholder="例如：我想知道老板拖欠工资我该怎么去要...")
    q15 = st.text_area("Q15. 对我们今后的普法活动，您还有什么建议？")

    submitted = st.form_submit_button("提交问卷并生成智能画像", type="primary")

# ================= 3. 数据处理与 AI 分析 =================
if submitted:
    st.info("AI 正在结合《标签体系》进行深度分析，请稍候...")

    # 1. 计算素养得分与层级
    score = 0
    answers = [q6, q7, q8, q9, q10]
    for ans in answers:
        if ans.startswith("A"):
            score += 2
        elif ans.startswith("B"):
            score += 1

    if score <= 3:
        level = "基础层（大白话+案例，强调底线意识）"
    elif score <= 7:
        level = "中间层（案例+互动，讲怎么做+基本权利）"
    else:
        level = "提升层（权利救济、维权程序，情景演练）"

    # 2. 权重字典初始化
    weights = {}


    def add_weights(tags, weight):
        for t in tags:
            weights[t] = weights.get(t, 0) + weight


    # 计算 Q4 (权重 1)
    for selected_q4 in q4:
        add_weights(q4_mapping[selected_q4], 1)

    # 计算 Q5 (权重 3)
    for selected_q5 in q5:
        add_weights(q5_mapping[selected_q5], 3)

    # 计算 Q6-Q10 薄弱点 (权重 2)
    for i, ans in enumerate(answers):
        q_key = f"Q{i + 6}"
        if ans.startswith("B") or ans.startswith("C") or ans.startswith("D"):
            if ans.startswith("B"):
                tag_letter = "B"
            elif ans.startswith("C"):
                tag_letter = "C"
            else:
                tag_letter = "D"

            if q_key in scenario_tags and tag_letter in scenario_tags[q_key]:
                add_weights(scenario_tags[q_key][tag_letter], 2)

    # 3. 大模型兜底 Q14 开放题 (权重 2)
    if q14.strip():
        prompt = f"""你是一个法学专家。请阅读以下用户的诉求，并从【T01-T34】标签库中提取最匹配的标签编号。
        标签库：T01监护, T03相邻关系, T06借贷, T08合同, T12离婚财产, T13抚养赡养, T15人身损害, T19劳动工资, T20工伤社保, T22交通酒驾, T24治安处罚, T27社区矫正, T28刑事量刑, T30帮信罪, T31反诈, T32网贷赌博, T33未成年人, T34法律援助。
        用户诉求：{q14}
        请直接输出标签编号列表，如 ["T19", "T34"]。不要输出废话。"""
        try:
            res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            ai_text = res.choices[0].message.content
            matched_tags = re.findall(r'T\d{2}', ai_text)
            add_weights(list(set(matched_tags)), 2)
        except:
            pass

    # 4. 排序取 Top 3
    top_3 = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]

    # ================= 4. 结果展示 =================
    st.success("✅ 分析完成！以下是为您生成的【需求画像卡】：")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="素养得分", value=f"{score} / 10")
    with col2:
        st.metric(label="宣讲深度", value=level.split("（")[0])
    with col3:
        st.metric(label="偏好时间", value=q13.split(".")[0])  # 顺带展示Q13

    st.write(f"**🎯 偏好形式：** {q11}")
    st.write(f"**⏱️ 建议时长：** {q12}")

    st.subheader("🔥 核心普法需求 (Top 3)")
    if not top_3:
        st.write("暂无高频需求，建议进行常规基础宣讲。")
    else:
        for idx, (tag, w) in enumerate(top_3):
            st.info(f"**第 {idx + 1} 需求：{tag}** (匹配权重：{w})")
            st.write(f"📚 已匹配资源：请调用 `资源库/{tag}_资料包` 进行备课。")

    st.caption("注：上述素养得分依据 Q6-Q10 选项自动生成，需求标签依据权重规则计算得出。")