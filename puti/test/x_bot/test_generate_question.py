"""
@Author: obstacles
@Time:  2025-04-18 15:36
@Description:  
"""
import pandas as pd
import asyncio

from utils.path import root_dir
from llm.nodes import OpenAINode, OllamaNode
from conf.llm_config import LLMConfig, LlamaConfig
import random
from tqdm import tqdm


async def test_generate_question():
    filter_json_path = str(root_dir() / 'data' / 'cz_filtered.json')
    df = pd.read_json(filter_json_path)
    node = OllamaNode(llm_name='llama', conf=LlamaConfig())
    for index, row in tqdm(df.iterrows(), total=len(df), mininterval=0.5, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]'):
        text = row['text']
        theme = await analyze_topic(text, node)
        
        # 单条生成prompt指令
        prompt_response = await node.chat(
            msg=[
                {"role": "system", "content": "生成3种风格的推文指令，用###分隔。格式：指令1###指令2###指令3"},
                {"role": "user", "content": theme}
            ],
            # temperature=0.7
        )
        
        # 解析单条结果
        prompt_response = extract_think_content(prompt_response)
        prompts = prompt_response.split('###')
        df.at[index, 'prompts'] = random.choice(prompts)

        template = random.choice(PROMPT_TEMPLATES)
        q = random.choice(random.choice(theme.split('\n')).split('/'))
        df.at[index, 'question'] = template.format(theme=q)
    filter_json_path2 = str(root_dir() / 'data' / 'cz_filtered_question_fix.json')
    df.to_json(filter_json_path2, orient='records', lines=True)
    print(f'测试完成，生成{len(df)}条问题')


async def analyze_topic(text: str, node: OllamaNode) -> str:
    """使用LLM分析文本提取核心主题"""
    response = await node.chat(
        msg=[
            {"role": "system", "content": "你是一个专业的内容分析师，请分析以下文本并提取2-5个核心主题。对于每个主题，请提供中文和英文版本，多个之间换行区分，格式：中文主题/英文主题, 不需要其他多余的内容。特别注意处理中英文混合内容，确保双语主题的准确性和一致性。"},
            {"role": "user", "content": text}
        ],
        # temperature=0.5
    )
    return extract_think_content(response)

def extract_think_content(text):
    import re
    # 使用正则表达式匹配并去除 <think> 和 </think> 标签
    think_content = re.sub(r'<think>(.*?)</think>', r'', text, flags=re.DOTALL)
    # 去除'中文主题/英文主题'前缀和空行
    think_content = re.sub(r'^中文主题/英文主题\s*', '', think_content)
    think_content = re.sub(r'\n\s*\n', '\n', think_content)
    return think_content.strip()

async def generate_prompts(theme: str, node: OllamaNode) -> list:
    """LLM生成3种不同风格的推文指令"""
    import re
    response = await node.chat(
        messages=[
            {"role": "system", "content": "请根据以下主题生成3条风格完全不同的推文指令。要求：1条提问式，1条感叹式，1条双语混合式。每条指令必须包含主题关键词，且风格差异明显。返回格式：指令1###指令2###指令3"},
            {"role": "user", "content": f"主题：{theme}"}
        ],
        # temperature=0.7
    )
    return extract_think_content(response)

PROMPT_TEMPLATES = [
    "请创作一条关于{theme}的社交媒体推文",
    "根据{theme}主题构思一条吸引眼球的推文",
    "为{theme}相关内容撰写一条互动性强的推文",
    "用轻松幽默的语气写一条关于{theme}的推文",
    "用中英双语写条关于{theme}的推文，要求包含核心关键词",
    "Create a bilingual tweet about {theme} with key terms",
    "Mix Chinese/English in post about {theme} #热门话题"
]


async def test_check_and_fix_questions():
    """
    检查cz_filtered_question_fix2.json中每条text对应的question是否合理，不合理则调用LLM重新生成，合理则不变，最后保存。
    """
    import json
    filter_json_path = str(root_dir() / 'data' / 'cz_filtered_question_fix2.json')
    with open(filter_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    node = OllamaNode(llm_name='llama', conf=LlamaConfig())
    changed = False
    for item in tqdm(data, desc='检查与修正question', mininterval=0.5):
        text = item.get('text', '')
        question = item.get('question', '')
        # 判断question是否合理
        is_reasonable = await is_question_reasonable(text, question, node)
        if not is_reasonable:
            # 重新生成question
            theme = await analyze_topic(text, node)
            template = random.choice(PROMPT_TEMPLATES)
            q = random.choice(random.choice(theme.split('\n')).split('/'))
            new_question = template.format(theme=q)
            item['question'] = new_question
            changed = True
    if changed:
        with open(filter_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'已修正并保存到{filter_json_path}')
    else:
        print('所有question均合理，无需修改')

async def is_question_reasonable(text: str, question: str, node: OllamaNode) -> bool:
    """
    利用LLM判断question是否与text内容匹配且符合推文生成要求。
    """
    check_prompt = [
        {"role": "system", "content": "你是一个推文内容审核专家，请判断给定的推文正文（text）和对应的问题（question）是否匹配且合理。要求：1. question需与text主题相关，2. question应为推文生成指令或与推文内容高度相关。只需回答'合理'或'不合理'。"},
        {"role": "user", "content": f"text: {text}\nquestion: {question}"}
    ]
    resp = await node.chat(msg=check_prompt)
    resp = extract_think_content(resp)
    return '合理' in resp

