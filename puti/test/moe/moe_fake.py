"""
@Author: obstacles
@Time:  2025-05-08 11:14
@Description:  
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


# ------------------------------------------------------------
# 1. 定义一个简单的 MoE Layer
# ------------------------------------------------------------
class SimpleMoE(nn.Module):
    def __init__(self, hidden_dim, expert_dim, num_experts):
        super().__init__()
        self.num_experts = num_experts
        # 一个简单的路由器：linear -> softmax，输出每个 token 到每个 expert 的分数
        self.router = nn.Linear(hidden_dim, num_experts, bias=False)
        # experts：num_experts 个简单 FFN（这里都用一层 Linear 代替）
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, expert_dim),
                nn.ReLU(),
                nn.Linear(expert_dim, hidden_dim)
            )
            for _ in range(num_experts)
        ])

    def forward(self, x, top_k: int = 2):
        """
        x: [batch, seq_len, hidden_dim]
        top_k: 每个 token 路由时激活的专家数
        """
        b, t, d = x.shape
        # 1) 计算路由分数
        scores = self.router(x)  # [b, t, num_experts]
        # 2) 选出 top_k 个 expert
        topk_vals, topk_idx = scores.topk(top_k, dim=-1)  # both: [b, t, top_k]
        # 3) 对每个激活 expert 计算输出并加权
        out = torch.zeros_like(x)
        for i in range(top_k):
            idx = topk_idx[..., i]  # [b, t]
            weight = F.softmax(topk_vals[..., i], dim=-1).unsqueeze(-1)
            # gather 对应 expert 的参数并计算
            # 先把 x 展平至 [b*t, d]
            x_flat = x.reshape(-1, d)
            idx_flat = idx.reshape(-1)
            # 取第 idx_flat 个 expert，计算输出
            expert_out = []
            for bti, exp_id in enumerate(idx_flat):
                expert_out.append(self.experts[exp_id](x_flat[bti]))
            expert_out = torch.stack(expert_out, dim=0)  # [b*t, d]
            expert_out = expert_out.reshape(b, t, d)
            out += weight * expert_out
        return out


# ------------------------------------------------------------
# 2. 定义一个采样函数：支持 temperature / top_k / top_p
# ------------------------------------------------------------
def sample_next_token(logits: torch.Tensor,
                      temperature: float = 1.0,
                      top_k: int = None,
                      top_p: float = None) -> int:
    """
    logits: [vocab_size]
    返回：采样得到的下一个 token id（标量）
    """
    # 1) temperature 缩放
    logits = logits / temperature

    # 2) Top-K 截断
    if top_k is not None:
        v, _ = torch.topk(logits, top_k)
        min_allowed = v[-1]
        logits = torch.where(logits < min_allowed,
                             torch.full_like(logits, -1e10),
                             logits)

    # 3) Top-P 截断
    if top_p is not None:
        sorted_logits, sorted_idx = torch.sort(logits, descending=True)
        probs = F.softmax(sorted_logits, dim=-1)
        cumulative = torch.cumsum(probs, dim=-1)
        # 找到累积超过 top_p 的第一个位置
        mask = cumulative > top_p
        # 对应位置及之后都置为 -inf
        sorted_logits[mask] = -1e10
        # 还原回原始顺序
        logits = torch.empty_like(logits)
        logits[sorted_idx] = sorted_logits

    # 4) softmax -> multinomial 采样
    probs = F.softmax(logits, dim=-1)
    next_token = torch.multinomial(probs, num_samples=1).item()
    return next_token


# ------------------------------------------------------------
# 3. 串联示例：伪造一个“小语言模型” + MoE 层 + 采样
# ------------------------------------------------------------
if __name__ == "__main__":
    # 配置
    batch_size = 1
    seq_len = 4
    hidden_dim = 32
    expert_dim = 64
    num_experts = 8
    vocab_size = 1000
    generate_len = 10

    # ① 随机初始化 embedding + “语言模型头”（线性投词）
    embed = nn.Embedding(vocab_size, hidden_dim)
    lm_head = nn.Linear(hidden_dim, vocab_size, bias=False)

    # ② MoE 层
    moe = SimpleMoE(hidden_dim, expert_dim, num_experts)

    # ③ 随机初始输入（batch=1，seq_len=4）
    input_ids = torch.randint(0, vocab_size, (batch_size, seq_len))
    hidden = embed(input_ids)  # [1, 4, hidden_dim]

    # ④ 迭代生成
    generated = input_ids.tolist()[0]
    for step in range(generate_len):
        # MoE 前向（动态 top_k）
        hidden = moe(hidden, top_k=2)

        # LM 头 + 取最后一个位置的 logits
        logits = lm_head(hidden)[:, -1, :]  # [1, vocab_size] -> [vocab_size]
        logits = logits.squeeze(0)

        # 采样下一个 token（动态传入采样超参）
        next_id = sample_next_token(
            logits,
            temperature=1.0 + 0.2 * (step / generate_len),  # 简单示例：温度随步数变化
            top_k=50,
            top_p=0.9
        )
        generated.append(next_id)

        # 更新 hidden：把新 token 加到序列尾（最简单做法）
        # 注意：这只是示例，真实场景最好用缓存避免重复全量计算
        hidden = embed(torch.tensor([generated]))  # 重映射

    print("生成的 token 序列：", generated)
