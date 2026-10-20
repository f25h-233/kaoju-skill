# 抓取通道（本机 Windows 11 中国区）

## 唯一通道

```bash
python C:/Users/qwe13/.claude/toolkit/fetch.py <url>
```

常用参数：`--html`（保留 HTML 结构）、`--json`（JSON API）、`--links`（只取链接）、`-o <文件>`（落盘）。

JS 渲染站 / 反爬站：

```bash
python C:/Users/qwe13/.claude/toolkit/fetch_js.py <url> --channel msedge
```

---

## 硬规则

**一、绝不改用 WebFetch / WebSearch。**
本机这两个被网络策略拦截，用了就是白费一轮。抓不到就抓不到，报给用户，不要换工具硬试。

**二、同一个 URL 失败两次就换路径。**
换子页、换域名、换移动版、换镜像、换搜索引擎的结果页。不要对同一个地址重试第三次。

**三、内容大时先落盘再筛。**
```bash
python .../fetch.py <url> -o /tmp/page.txt
grep -n "关键词" /tmp/page.txt
```
不要把整页灌进上下文——一次抓取就能吃掉几万 token。

---

## 抓不通时怎么办

| 情况 | 做法 |
|---|---|
| 超时 / 连接失败 | 换镜像站或缓存版；两次不行就放弃这个源 |
| 付费墙 / 登录墙 | `access` 如实填 `partial` 或 `closed`，**它就不算一个有效来源** |
| 只有摘要页 | 同上。摘要页不算来源 |
| 反爬（PerimeterX / Cloudflare） | 用 `fetch_js.py`；仍失败就换同内容的其它站点 |
| 整站不可达 | 记下来，在报告的「本次缩减了什么」里写明 |

---

## 抓不到时的降级

**不降级。** 抓取是硬依赖，不是可选的加速器。

- `fetch.py` 存在但抓不通 → 报给用户，并说明哪些源没拿到
- 完全没有抓取能力 → 本 skill 只能处理用户**已经提供**的材料（本地文件、粘贴的文本），并在报告里写「未联网」
- 任何情况下都不许用记忆或常识**编造**一个来源

---

## 依赖

- `fetch.py` 需要 `httpx` + `bs4`
- `fetch_js.py` 需要 `playwright`

两者都已装。若换机器，先验：
```bash
python -c "import httpx, bs4; print('fetch.py 可用')"
python -c "import playwright; print('fetch_js.py 可用')"
```
