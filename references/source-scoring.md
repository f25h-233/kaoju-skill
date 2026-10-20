# 来源打分

## 两个分数，别混

| 分数 | 谁给 | 存在哪 |
|---|---|---|
| `credibility` 1–5 | **你**判断，填进 `sources.csv` | 账本 |
| 权威分 0–10 | 脚本按域名自动算 | `_check/evaluation.json` |

**脚本的权威分只认域名，不认内容。** `nature.com` 上一篇勘误和一篇论文得分一样。所以它只能当参考，`credibility` 才是你的判断。

---

## `credibility` 怎么定

| 分 | 什么算 |
|---|---|
| 5 | 一手源：原始公告、财报、监管文件、论文原文、当事人自己的公开表述 |
| 4 | 权威机构报告：行业协会年报、政府统计、头部咨询的公开报告 |
| 3 | 行业媒体：有编辑把关的垂直媒体 |
| 2 | 大众媒体、个人博客 |
| 1 | 论坛、匿名、AI 生成内容 |

**一手源的判定标准**：它是**这个事实的原始发生地**吗？还是别人转述的？
- 财报是「营收 120 亿」的一手源；报道财报的新闻是二手。
- 标准原文是一手源；解读标准的文章是二手。
- 创始人自己写的博文是一手源；采访他的报道是二手（引语部分仍可作一手用，但要标注）。

---

## 权威分档表（脚本实际用的）

脚本 `source_evaluator.py` 里有一张域名表。**油气行业那几行是本仓库增补的**——原表对油气零覆盖，不补的话中石油、GIIGNL、EIA 这些会被当成未知域名丢掉。

**9.5 分**：nature.com、science.org、ieee.org、who.int、nih.gov、cnki.net、wanfangdata.com.cn、cas.cn、nsfc.gov.cn、**cnpc.com.cn、sinopec.com、cnooc.com.cn、pipechina.com.cn、giignl.org、iea.org、eia.gov、opec.org、spe.org、onepetro.org、asme.org、api.org、iso.org**

**8.5 分**：任何 `.gov` / `.edu` / `.gov.cn` / `.edu.cn` / `.ac.cn` 结尾的域名（自动加分，包括 `nea.gov.cn` 国家能源局、`ndrc.gov.cn` 发改委）

**7.5 分**：reuters.com、bbc.com、economist.com、hbr.org、mckinsey.com、xinhuanet.com、people.com.cn、36kr.com、jiqizhixin.com、**sasac.gov.cn、oilgas.com.cn、in-en.com、bjx.com.cn、longzhong.com、sci99.com、jlc.com.cn、cngold.org、argusmedia.com、spglobal.com、platts.com、naturalgasintel.com、worldoil.com、oilprice.com**

**5.5 分**：medium.com、substack.com、zhihu.com、csdn.net、juejin.cn、toutiao.com、sspai.com、**chem99.com、oilnews.com.cn、hcbbs.com**

**3.0 分**：不在表里的域名。**低于默认门槛 5.0，会被直接丢弃。**

> 遇到好源被丢，是域名表的问题不是源的问题。往 `source_evaluator.py` 的 `TIER_*` 表里补一条即可（域名写**可注册域**形式，如 `cnpc.com.cn` 而不是 `news.cnpc.com.cn`）。

---

## `caveat` 的四个值

严格枚举，写不出就填 `-`：

| 值 | 什么时候 |
|---|---|
| `-` | 没有特殊利益关系 |
| `vendor` | 卖方自己出的材料：设备厂白皮书、软件商案例、供应商宣传 |
| `self-reported` | 自报数据：企业自称的产能、合格率、市占率 |
| `disputed:NN` | 有另一个源（编号 NN）公开质疑它 |

**不许写自由文本。** 「可能有偏向」「需谨慎看待」这类话脚本读不了、人也不想读。四选一。

---

## `root` 怎么填

- `own`：**这条源本身就是原始出处**（它是那件事第一次发生的地方）
- 短 id：它转述的上游，例如 `reuters-2025-03`、`study-smith-2024`
- `unclear`：查不出来

**独立性怎么算**：`own` 的出处身份是**它自己**——三个互相独立的一手源都写 `own`，那是 3 个独立出处。写同一个短 id 的三个源，是 **1 个**出处。`unclear` 保守算作同一个未知出处。

## `discovery_path` 怎么填

格式：`渠道|确切查询词|语言`，例如：

```
必应|LNG 接收站 投资回收期|zh
官网|中国石油 年度报告|zh
必应|LNG terminal investment outlook|en
```

**必须是你实际用的词，不许复制粘贴。** 这条列存在的意义就是拆穿「三个源其实是一次搜索捞出来的」。

---

## `access` 怎么填

`full` / `partial` / `abstract` / `closed`

- `partial` / `abstract` / `closed` 的源**不计入三角验证**——付费墙摘要页不算一个来源
- 如实填。填 `full` 但实际只有摘要，是在给假证据。
