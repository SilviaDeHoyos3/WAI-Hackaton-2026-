# Lan's AI conversation prototype: presentation scope and Q&A

## 最重要的一句话

AI 负责理解经理的话、提取输入和请求调用工具；预测来自 Silvia 的模型，
备餐数字来自 Ari 的函数；经理确认后才更新演示中的计划。

不要说 Gemini 预测了销量，也不要说它自动减少了真实食物浪费。

## 展示时可以说的英文

“I built the conversation integration using Gemini 3.5 Flash Lite. The model
understands the manager's message and requests the appropriate tool. Silvia's
forecasting model supplies the forecast, and Ari's decision functions calculate
the preparation quantities. The manager reviews a recommendation before applying
it in the demo. The numerical explanations use templates populated from actual
tool outputs, rather than asking the language model to calculate the numbers.”

## 能力与边界

| 可以做 | 不能据此声称 |
| --- | --- |
| 对应用选中的一道菜，读取本地真实 next-week forecast，处理经理的 ready stock | Gemini 自己训练或生成预测；随便切换菜品仍保持上下文正确 |
| 用自然语言输入库存，AI 请求调用 central tool | 能可靠理解任何表达；LLM 输入提取绝不出错 |
| 收集经理对订单的估计，再选择25%／50%／100%权重 | 自动知道活动会增加多少订单；自动挑选最优权重 |
| 对同一份 forecast 和 stock 调用经理调整工具 | 已为所有餐厅验证最佳策略或真实业务收益 |
| 展示待确认建议，再确认／撤销；保留工具调用记录 | 已向厨房下单、扣减真实库存或执行现实操作 |
| 对缺信息追问，0库存作为有效输入；失败时保留已确认计划 | 网络/API永远可用；具备生产环境可靠性 |
| 对浪费、缺货和碳排预测问题说明范围限制 | 准确预测下周浪费或缺货；保证零浪费和零缺单 |

本聊天页面没有导入可验证的最终模拟结果表，因此不报具体 waste reduction
百分比。请切到团队的 Impact 屏幕，区分模拟假设、四道 demo meal 和 all-meal
服务权衡。需求区间也不能称为经过验证的统计置信区间。

## 技术结构（被问到再讲）

Manager text -> Gemini function call -> validated application adapter ->
deterministic preparation function -> pending plan -> explicit human confirmation.

The application computes the forecast locally. The LLM does not receive the whole
CSV dataset. It receives conversation text, tool definitions, and tool results
including the necessary forecast context. API access is configured on the machine
running the demo. Keys are not in the ZIP, trace export, or source code.

The current prototype allows one tool call per message and a bounded conversation
history. It is a constrained tool-using workflow, not an open-ended autonomous
agent. Sessions are not durable user accounts; reloading/restarting can lose state.

## 常见问题与简短回答

**Is this really using AI, or is it a fixed chatbot?**

“It uses a live Gemini model to interpret the message and request a tool call.
The numerical calculations and confirmation steps are controlled by the
application. Some safety responses and numerical explanations are templated.”

**What does AI add beyond the existing controls?**

“It gives the manager a conversational way to provide stock and local knowledge.
The underlying tools stay the same, so the chat and manual controls can be checked
against each other.”

**Does the AI calculate 434 or 470?**

“No. The Python decision tools calculate those quantities using the same stored
forecast. Gemini extracts the manager's inputs and calls the tool.”

**Why do you still use adjustment buttons?**

“They make the manager's influence explicit. The manager chooses 25%, 50% or 100%;
the language model does not invent a weight.”

**What happens when a manager says there is an event?**

“If they have not estimated orders, we ask for an estimate. We do not infer event
demand from the word ‘event’.”

**Can it guarantee no waste and no missed orders?**

“No. Demand is uncertain. This is a planning recommendation, and the reported
waste/service comparisons belong to a separate simulation under stated storage
assumptions.”

**What if the API fails?**

“The confirmed plan stays unchanged. The manager can retry or use the existing
manual interface. We do not label the manual fallback as a live AI conversation.”

**Is this deployed for every restaurant or public visitor?**

“No. It is a local hackathon prototype. Public deployment, authentication, durable
storage, usage controls and operational validation are future work.”

**What did Lan build?**

“I built the Gemini connection, conversation controller, application-tool
dispatch, confirmation workflow, test screen, integration tests and handoff
documentation. Silvia built forecasting, and Ari built the decision tools.”

## Evidence: say only what has actually been checked

- User-executed live synthetic call: forecast 100, stock 20 -> prepare 80; Gemini
  called the real adapter and correctly explained the result.
- User screenshot of live real-data screen: forecast about 453.16, stock 20 ->
  pending 434 -> confirmed 434. This proves that first path, not every later case.
- Local controller + UI acceptance with a mocked provider: 434 -> 470, missing
  event estimate, confirmation states and dish-change invalidation passed.
- Unit tests cover 0/sufficient/missing stock, weight settings, API failure,
  blocked extra numerical arguments, scope limitations and discard behavior.
- Full live multi-turn acceptance was executed by Lan: all seven checks passed,
  including missing estimate, manager estimate 600, 25% adjustment, manual-tool
  agreement and confirmation state. The report is `docs/AGENT_LIVE_ACCEPTANCE.json`
  in the review ZIP. This is one tested conversation, not a general reliability claim.
- No teammate-machine test or merge into Ari's latest UI is implied by this ZIP.

## 最短演示路线

1. Load Centre 13, Meal 1198. Say: “I have 20 portions ready to use. How many more
   should I make?” Review the result, then confirm.
2. Say: “There's a local event. I think we'll get 600 orders.” Select Small change.
3. Point out that the old confirmed plan remains active while the new one is
   pending. Confirm to apply. Numbers must come from this runtime's tool calls;
   434 -> 470 is the recorded local example, not a hard-coded promise.
4. Open the trace to show the two numerical tool calls and their outputs.

Before a final rehearsal, reload the page and click Load forecast and start again
to ensure a fresh conversation with the latest controller code.
