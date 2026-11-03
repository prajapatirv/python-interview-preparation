---
id: genai-fundamentals-40-concepts
title: GenAI fundamentals: 40 concepts every developer is asked about, from tokens to context failures
stack: java
skill: genai
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`). It covers the 40 concepts of
a widely shared "Gen AI Fundamentals" guide, grouped into 12 answers you can actually say aloud. No machine-learning
background is assumed. The sampling and cost numbers ran in `examples/21_coding_interview/09_vector_search_and_llm_sampling_from_scratch.java`.

| # | Concept | Answer | # | Concept | Answer |
|---|---|---|---|---|---|
| 1 | Tokens | Q1 | 21 | Prompt caching | Q8 |
| 2 | Tokenization | Q1 | 22 | Latency | Q8 |
| 3 | Token inflation | Q1 | 23 | Model routing | Q8 |
| 4 | Embeddings | Q1 | 24 | Local models | Q8 |
| 5 | Transformer | Q2 | 25 | Prompt engineering | Q10 |
| 6 | Attention | Q2 | 26 | Few-shot prompting | Q10 |
| 7 | Mixture-of-experts | Q2 | 27 | Prompts as code | Q10 |
| 8 | Pretraining | Q2 | 28 | Context engineering | Q6 |
| 9 | Reasoning models | Q4 | 29 | Context: write | Q6 |
| 10 | Hallucination | Q4 | 30 | Context: select | Q6 |
| 11 | Temperature | Q3 | 31 | Compression | Q6 |
| 12 | Top-p | Q3 | 32 | Token budgets | Q6 |
| 13 | Top-k | Q3 | 33 | Context ordering | Q6 |
| 14 | Benchmark literacy | Q5 | 34 | Memory | Q11 |
| 15 | Model landscape | Q5 | 35 | Semantic memory | Q11 |
| 16 | Calling models properly | Q7 | 36 | Episodic memory | Q11 |
| 17 | Structured output | Q9 | 37 | Procedural memory | Q11 |
| 18 | Schema-constrained decoding | Q9 | 38 | Context rot | Q12 |
| 19 | Tool calling | Q9 | 39 | Context distraction | Q12 |
| 20 | Cost engineering | Q8 | 40 | Context clash | Q12 |

Note that the "Top-k" here (13) is about choosing the next **token**. In RAG, top-k means how many **chunks** to retrieve
(bank 67). Same name, different thing, and a good one to clarify if asked.

### Q1 [fresher] What are tokens, tokenization and embeddings? Why does the same sentence cost more in some languages?
tags: tokens, tokenization, token-inflation, embeddings, context-window, multilingual, genai-fundamentals, reported-genai

**Start here: the concepts**
- A **token** is a chunk of text a model reads and writes: a word, part of a word, or punctuation. Each maps to an integer ID.
- **Tokenization** is the step that splits text into tokens before the model sees it.
- An **embedding** is a list of numbers representing meaning, so similar things sit close together.

**The live scenario (functional requirement)**
*FR: "A support bot serves English, Hindi and Tamil users."* The budget was estimated from English test data. The same sentence can take more tokens in Hindi or Tamil, so costs come in higher and long documents hit limits sooner.

**What the interviewer is really checking**
That you treat tokens as an engineering unit for cost and limits, rather than as an abstract idea.

**How I answer it** (120-second answer, point by point)
1. **Text to tokens:** "Generative AI" might become `Gener`, `ative`, `AI`, each with an ID such as 4920, 345, 8001. The exact split depends on the tokenizer, so these numbers are illustrative.
2. **Rule of thumb:** in English, about 4 characters or three quarters of a word per token. Count with the provider's tokenizer before relying on it.
3. **Why it matters:** you pay per token, and the context window is measured in tokens. A model has a maximum for input plus output.
4. **Token inflation:** tokenizers are often more efficient for scripts common in their training data. The guide's example gives 6, 9 and 10 tokens for the same sentence in English, Hindi and Tamil. It varies by tokenizer and text, so measure on your own data.
5. **Tokens vs embeddings:** token IDs are arbitrary labels: 4920 isn't "near" 4921 in meaning. Embeddings are what capture meaning, and that's why `car` and `vehicle` end up close and `banana` far away.
6. **Practical check:** an embedding model and a chat model tokenize separately, and each has its own limit.

**Trade-offs and what can go wrong**
- Models see tokens rather than letters, which is why counting characters in a word has historically been unreliable for them.
- Estimating budgets from English data alone underestimates multilingual cost.
- Long pasted JSON or base64 can use far more tokens than you'd expect.

**Follow-ups to expect**
- *How do you count tokens in Java?* -> JTokkit for OpenAI-style encodings, or a provider's token-count API, and read `usage` on every response.
- *Why does output usually cost more than input?* -> Output tokens need sequential generation, and pricing generally reflects that.

**60-second answer**
"A token is the unit a model reads and writes: a word, a piece of a word or punctuation, each with an ID. Tokenization is the split that happens before the model sees the text, and it matters because you pay per token and the context window is measured in tokens. The same sentence can take more tokens in Hindi or Tamil than in English, so I measure on real data rather than English samples. Token IDs carry no meaning. Embeddings do: they're vectors where similar meanings are close, and that's the basis of semantic search."

### Q2 [mid] What happens inside an LLM? Explain transformers, attention, mixture-of-experts and pretraining to a backend developer.
tags: transformer, attention, multi-head, mixture-of-experts, pretraining, next-token, genai-fundamentals, reported-genai

**Start here: the concepts**
- **Pretraining:** the model learns by predicting the next token over huge amounts of text.
- **Transformer:** the architecture most modern LLMs use, built around attention.
- **Attention:** lets each token weigh information from other tokens in order to work out its meaning in context.

**The live scenario (functional requirement)**
A manager asks why the model handled "The bank approved the loan" and "We sat on the river bank" differently, and why it isn't just looking things up. The word `bank` means something different in each sentence, and attention is how the model works that out.

**What the interviewer is really checking**
A correct mental model at a developer's level, without pretending to be a researcher.

**How I answer it** (120-second answer, point by point)
1. **Training:** given "The cat sat on the", predict "mat". Repeating this billions of times shapes weights that capture grammar, facts and patterns. It stores patterns rather than a database of documents, which explains why it can recall things wrongly.
2. **A transformer block:** multi-head attention, then a feed-forward network, with layer normalisation. It's repeated N times. Each layer refines each token's representation.
3. **Attention:** for each token, the model scores how relevant every other token is, then mixes in information accordingly. **Multi-head** means several of these run in parallel, capturing different relationships.
4. **Generation:** it isn't retrieving an answer. It produces a probability for every possible next token, picks one, appends it, and repeats (Q3).
5. **Mixture-of-experts:** instead of running the whole network per token, a router activates only a few expert sub-networks. That reduces compute for a given capability. Experts are learned, so the tidy "code expert, math expert" labels in diagrams are only an illustration.
6. **Why a developer should care:** attention over the whole context explains the context-window limit, why cost grows with input, and why position and clutter affect quality.

**Trade-offs and what can go wrong**
- "It understands" is shorthand. Don't overclaim in an interview.
- Pretraining has a cut-off date, so a model can't know recent facts unless you supply them (RAG or tools).

**Follow-ups to expect**
- *Why are GPUs needed?* -> Attention and feed-forward steps are large matrix multiplications that run well in parallel.
- *What about fine-tuning?* -> Adjusting weights on your own examples: bank 77 Q2 covers when.

**60-second answer**
"During pretraining, the model learns by predicting the next token across huge amounts of text, which encodes language patterns into its weights. It's a transformer: stacked layers where attention lets each token weigh every other token, so 'bank' gets a different meaning next to 'river' than next to 'loan'. When generating, it produces a probability for each possible next token, picks one, and repeats. Mixture-of-experts saves compute by activating only a few sub-networks per token. As a developer, the takeaway is that it predicts rather than looks up, which explains both hallucinations and context limits."

### Q3 [mid] How does an LLM choose its next token? Explain temperature, top-p and top-k.
tags: temperature, top-p, top-k, nucleus-sampling, softmax, determinism, genai-fundamentals, reported-genai

**Start here: the concepts**
- The model outputs a score (a logit) per possible token, and these become probabilities.
- **Temperature** reshapes those probabilities. **Top-k** keeps only the k most likely tokens. **Top-p** keeps the smallest set whose cumulative probability reaches p.

**The live scenario (functional requirement)**
*FR: "An invoice extractor must be consistent, while a marketing copy tool should vary."* Using the same settings for both gives either flaky extraction or dull copy.

**What the interviewer is really checking**
Whether you understand the mechanism well enough to choose settings and explain why temperature 0 is not a guarantee.

**How I answer it** (120-second answer, point by point)
I ran this with five tokens, with logits 3.0, 2.0, 1.0, 0.5, 0.1:

| Temperature | Top token probability | Tokens kept by top-p 0.9 |
|---|---|---|
| 0.2 | above 0.99 | 1 |
| 1.0 | 0.61 | 3 |
| 2.0 | 0.40 | 4 |

1. **Temperature** divides the logits before converting them to probabilities. Low values sharpen the distribution, and high values flatten it.
2. **Top-k** is a fixed cut: with k=3, only three tokens can ever be picked, however the probability is spread.
3. **Top-p adapts**, as the table shows: a confident distribution keeps one token, and an uncertain one keeps several. That's why it's often preferred to top-k.
4. **Choosing:** low temperature for extraction, classification and code. Higher for brainstorming. Adjust temperature **or** top-p rather than both, as provider docs usually advise.
5. **Not all models accept all of these.** Some newer or reasoning models restrict sampling parameters, so check the model's docs.

**Trade-offs and what can go wrong**
- **Temperature 0 isn't fully deterministic.** Batching, hardware and model updates can still change results, and a seed is best-effort. So tests must not assert exact strings (bank 78 Q11).
- Low temperature doesn't make an answer **true**. It just makes it more repeatable.
- For structure, use schema-constrained output (Q9), instead of relying on low temperature.

**Follow-ups to expect**
- *Which is applied first?* -> Generally temperature, then the top-k and top-p filters, then sampling. It varies by implementation.

**60-second answer**
"The model gives a probability for each possible next token, and these settings control the pick. Temperature reshapes the distribution: in my test the top token went from over 99% at 0.2, to 61% at 1, to 40% at 2. Top-k keeps a fixed number of tokens. Top-p keeps the smallest set reaching a cumulative probability, so it adapts: one token if the model is confident, several if not. I use low temperature for extraction and higher for creative work, and I tune one, not both. Even temperature 0 isn't perfectly deterministic, and low temperature doesn't make the answer correct."

### Q4 [mid] What are reasoning models, and why do models hallucinate? How do you reduce it?
tags: reasoning-models, hallucination, chain-of-thought, grounding, abstain, genai-fundamentals, reported-genai

**Start here: the concepts**
- A **reasoning model** spends extra computation thinking step by step before answering.
- A **hallucination** is a confident, plausible answer that's wrong or unsupported.

**The live scenario (functional requirement)**
*FR: "An HR assistant answers leave-policy questions."* It states a 30-day carry-forward rule that doesn't exist. It sounds right, and nothing in the response signals doubt.

**What the interviewer is really checking**
That you know why it happens, and that you know the system design controls rather than "tell it not to lie".

**How I answer it** (120-second answer, point by point)
1. **Why it happens:** the model predicts plausible next tokens, and it has no built-in database lookup or truth check. A smooth continuation can be false. The guide's example is a fabricated winner of a "Nobel Prize in Computer Science", which doesn't exist.
2. **Reduction, by layer:**

| Layer | Technique |
|---|---|
| Ground it | RAG or a tool call for facts (bank 67) |
| Allow "I don't know" | Say so in the prompt, and test that it happens |
| Require evidence | Citations that your code validates |
| Check the output | Decompose into claims, and verify each (bank 66 Q12) |
| Structure it | Schemas, plus business validation |
| Measure it | Faithfulness evaluation on a golden set (bank 77 Q8) |
| Keep a human in | Approval for high-stakes actions |

3. **Reasoning models** help with multi-step logic, like `25 x 17 = 425`, or planning. They cost more and take longer, and they don't invent missing facts into truth, so they aren't a cure for hallucination.
4. **Model choice:** route hard problems to a reasoning model, and leave simple ones to a fast model (Q8).

**Trade-offs and what can go wrong**
- Showing the reasoning doesn't prove the answer, since a stated chain of thought may not reflect how the model got there.
- Citations can be fabricated, so check that a cited source exists and supports the claim.
- A high retrieval score isn't proof of correctness.

**Follow-ups to expect**
- *Can you eliminate hallucination?* -> No. You reduce and detect it, and design for the remainder.
- *More detail?* -> Bank 77 Q7.

**60-second answer**
"A hallucination is a confident, plausible but wrong answer. It happens because the model predicts likely text and has no built-in truth check. I can't eliminate it, so I design around it: ground answers with RAG or tools, allow 'I don't know', require citations that code validates, split outputs into claims and verify them, and measure faithfulness on a golden set. Reasoning models think step by step first, which helps with multi-step logic, but they cost more and can't supply missing facts. High-stakes actions still get human approval."

### Q5 [mid] How do you choose the right model? How do you read benchmarks?
tags: model-selection, benchmarks, mmlu, humaneval, model-landscape, evaluation, genai-fundamentals, reported-genai

**Start here: the concepts**
- **Model landscape:** fast and cheap, balanced, or most powerful. Most products need more than one.
- **Benchmark:** a standard test. **MMLU** tests broad knowledge, and **HumanEval** tests coding.

**The live scenario (functional requirement)**
*FR: "Pick a model for Java code review comments."* Model B tops the general leaderboard with an MMLU of 88.1, and model C has a lower MMLU of 82.5 but scores 82.3 on HumanEval. For code, C may be better. Your own test decides.

**What the interviewer is really checking**
That you don't choose from a leaderboard, and that you have an evaluation method.

**How I answer it** (120-second answer, point by point)
1. **Start from requirements:** latency budget, cost per request, quality bar, data residency, context size, and needed features such as tools, vision, structured output.
2. **Use tiers:**

| Tier | Good for | Trade-off |
|---|---|---|
| Fast and cheap | Classification, extraction, routing, high volume | Weaker reasoning |
| Balanced | Most features, chat, RAG answers | The default |
| Most powerful | Hard reasoning, agents, complex code | Higher cost and latency |
| Self-hosted open-weight | Private data, on-prem | You operate it |

3. **Read benchmarks critically:** different ones test different skills. Check the version and date, data contamination, and whether the score is vendor-reported. A small score gap often isn't meaningful for your task.
4. **Run your own evaluation:** 50 to 100 real cases with expected outcomes, scored for quality, p95 latency, and cost per request. That table makes the decision.
5. **Keep it swappable:** behind `ChatClient` or `AiServices`, and re-run the evaluation when models change.

**Trade-offs and what can go wrong**
- Vendors replace and retire models, so pin versions, and test before upgrading.
- The cheapest token price can be more expensive overall if the model needs more retries or longer prompts.

**Follow-ups to expect**
- *Self-host or API?* -> Bank 77 Q11.

**60-second answer**
"I start from requirements: latency, cost, quality, data rules and features. Then I think in tiers: a fast cheap model for classification and routing, a balanced one as the default, and the most powerful only for hard reasoning. Benchmarks are a starting filter, not a decision, since MMLU and HumanEval measure different skills and small gaps often mean nothing. So I run my own evaluation on 50 to 100 real cases, measuring quality, p95 latency and cost per request. And I keep the model behind an abstraction so I can re-test and switch."

### Q6 [senior] What is context engineering? How do you manage what the model sees?
tags: context-engineering, write, select, compress, token-budget, context-ordering, genai-fundamentals, reported-genai

**Start here: the concepts**
- **Prompt engineering** is what you say. **Context engineering** controls **everything** the model sees: instructions, retrieved data, tool definitions, history.
- Four moves: **write** (save outside the model), **select** (pull in only what's needed), **compress** (summarise), and **budget** (limit each part).

**The live scenario (functional requirement)**
*FR: "A travel-planning assistant works over long sessions."* Sending all history and all documents on every call makes it slow and expensive, and quality gets worse, not better.

**What the interviewer is really checking**
That you treat context as a limited resource to be designed, and can give numbers.

**How I answer it** (120-second answer, point by point)
1. **Write:** store facts outside the context window. "I prefer budget hotels under 3000 rupees" goes in a database, a file or a vector store for later.
2. **Select:** use search to fetch only what this request needs: relevant docs, key notes, a short summary. Sending less improves accuracy and saves tokens.
3. **Compress:** replace a 5,000-token history with a 300-token summary that keeps key facts, decisions and open tasks. Trim tool outputs to the top rows and key fields.
4. **Budget:** give each part a limit. Example for a 128,000-token window (I verified it adds up):

| Part | Share | Tokens |
|---|---|---|
| System instructions | 10% | 12,800 |
| Retrieved context | 40% | 51,200 |
| User input | 30% | 38,400 |
| Reserved for output | 20% | 25,600 |

5. **Order:** put stable system instructions first, and the current question last, with the context in between. Models tend to weight the start and end more, and stable prefixes also improve prompt caching (Q8). Treat "attention by position" as a heuristic, and test it.
6. **Reserve output:** a full context leaves no room to answer, and the reply gets cut off.

**Trade-offs and what can go wrong**
- Over-compression loses a decision that matters, so keep decisions and constraints verbatim.
- Exceeding the limit may drop old content silently or return an error, depending on the provider.
- Remove sensitive data before it goes into context.

**How I'd monitor it**
Tokens per part per request, truncation count, the cache hit rate, and quality against context size.

**Follow-ups to expect**
- *How does this differ from RAG?* -> RAG is one technique inside "select".
- *When context goes wrong?* -> Q12.

**60-second answer**
"Context engineering means controlling everything the model sees, not just the prompt. I think of four moves. Write: save facts outside the model. Select: retrieve only what this request needs. Compress: summarise old history, like 5,000 tokens down to 300, keeping decisions. Budget: fix a share per part, such as 10% instructions, 40% retrieved context, 30% input and 20% reserved for output. I keep stable instructions first and the question last, which also helps prompt caching. The goal is the smallest context that lets the model do this step well."

### Q7 [mid] What does calling a model properly look like in production?
tags: llm-client, retries, backoff, timeouts, rate-limits, fallback, circuit-breaker, genai-fundamentals, reported-genai

**Start here: the concepts**
- An LLM API is a **slow, expensive, unreliable remote dependency**. All the usual resilience rules apply, with a few more.

**The live scenario (functional requirement)**
*FR: "Summarise each support ticket on creation."* A provider has a 429 spike for 10 minutes. A naive retry loop multiplies the traffic, makes things worse and doubles the bill.

**What the interviewer is really checking**
That you apply your backend experience here, rather than treating AI as magic.

**How I answer it** (120-second answer, point by point)

| Concern | What I do |
|---|---|
| Timeout | Connect short, and read per use case: streaming has a time-to-first-token limit and an idle limit |
| Retry | Only transient errors (429, 5xx, timeouts) with exponential backoff and jitter |
| Don't retry | 400, 401, and a request that's too long; these are bugs |
| Rate limits | Respect `Retry-After`; client-side throttling; a queue for batch work |
| Circuit breaker | Fail fast when the provider is down, then fall back |
| Fallback | A secondary model or provider, a cached answer, or a clear "try later" |
| Idempotency | A retried generation costs money, and can repeat tool side effects |
| Token limit | Set `max_tokens`; handle the "output truncated" stop reason |
| Error messages | Useful to the user; details go in the logs |
| Logging | Model, tokens, latency, finish reason, request id; not raw sensitive prompts |

In Spring AI, `spring.ai.retry.*` configures retries for model calls. Wrap the rest with Resilience4j.

**Trade-offs and what can go wrong**
- Retrying inside a tool loop can duplicate a side effect such as a payment. Tools must be idempotent.
- A fallback model behaves differently, so evaluate it, and record which model served each answer.
- Retry budgets must fit inside the user's overall timeout.

**How I'd monitor it**
Error rate by code, p95 and time-to-first-token, retries, breaker state, tokens and cost per feature.

**Follow-ups to expect**
- *Async or sync?* -> Queue any non-interactive work, so that you control the rate.
- *More detail?* -> Bank 78 Q8 on observability.

**60-second answer**
"I treat it as a slow, costly and unreliable remote dependency. I set timeouts, including time-to-first-token for streaming. I retry only on transient errors, 429s, 5xx and timeouts, with backoff and jitter, respecting Retry-After, and I never retry a 400. There's a circuit breaker with a fallback to a second model or a clear message. I set max tokens and handle truncated output. Non-interactive work goes through a queue to control the rate. I log model, tokens and latency, and make tools idempotent, since retries can repeat side effects."

### Q8 [senior] How do you reduce the cost and latency of an AI feature? Explain prompt caching, streaming, routing and local models.
tags: cost-engineering, prompt-caching, streaming, model-routing, local-models, ollama, vllm, latency, genai-fundamentals, reported-genai

**Start here: the concepts**
- **Cost** is input tokens x input rate + output tokens x output rate, per request, then multiplied by volume.
- **Prompt caching** lets a provider reuse a processed **prefix** of your prompt.
- **Streaming** shows tokens as they're generated.
- **Routing** sends each request to the right model.

**The live scenario (functional requirement)**
*FR: "A customer assistant at 1 million requests a month, under a budget."* At 1,000 input and 500 output tokens, at example rates of $3 and $12 per million, one request costs $0.009, which is $9,000 a month. (I checked this arithmetic. The rates are illustrative, so use current pricing.)

**What the interviewer is really checking**
That you start by measuring, know each lever, and don't confuse perceived and real latency.

**How I answer it** (120-second answer, point by point)
1. **Measure first:** tokens and cost per feature, from `usage` in each response. Find what dominates.
2. **Levers, cheapest to adopt first:**

| Lever | Effect | Caveat |
|---|---|---|
| `max_tokens`, concise output | Output is usually the pricier side | Don't cut useful answers |
| Trim context | Less input | Keep what's needed (Q6) |
| Prompt caching | Lower input cost and latency on repeated prefixes | Needs a **stable start**: a timestamp at the top breaks every hit |
| Semantic cache | Skips the model on similar questions | Risk of a wrong match (bank 66 Q7) |
| Model routing | Simple tasks go to a small model | Needs evaluation and fallback |
| Batch APIs | Often cheaper for offline work | Results aren't immediate |
| Local models | No per-call fee | You pay for GPUs and operations |

3. **Routing:** simple rules first, such as length or intent, and a small classifier if needed. Start small, and escalate on low confidence.
4. **Latency:** streaming doesn't make generation faster, but the user sees text sooner, so measure **time to first token** as well as the total. Real reductions come from smaller models, shorter context, closer regions and caching.
5. **Local models** with Ollama, LM Studio or vLLM suit development, sensitive data and steady high volume. Compare the true cost, including GPU, idle capacity and staff.

**Trade-offs and what can go wrong**
- Prompt caching only helps with an exact prefix, and caches can have a minimum size, a write cost and a short lifetime. Check your provider.
- Don't let cost cuts silently reduce quality: gate each change on your evaluation set.
- Cheap models needing retries can cost more.

**How I'd monitor it**
Cost per feature and per user, cache hit rate, time to first token, p95 total latency, and routing distribution.

**Follow-ups to expect**
- *Prompt cache vs semantic cache?* -> The prompt cache reuses computation and the model still answers. A semantic cache returns a stored answer without calling the model.
- *More detail?* -> Bank 77 Q12.

**60-second answer**
"I first measure tokens and cost per feature. For example, 1,000 input and 500 output tokens at $3 and $12 per million is under a cent, but that's $9,000 at a million requests. Then I cut output with max tokens, trim context, and use prompt caching, which needs a stable prefix, so no timestamps at the top. Routing sends simple tasks to a small model. A semantic cache can skip the call altogether, but risks wrong matches. For latency, streaming improves what the user feels, so I track time to first token separately. Every change is checked against my evaluation set."

### Q9 [mid] Structured output, schema-constrained decoding and tool calling: what's the difference?
tags: structured-output, json-schema, constrained-decoding, tool-calling, function-calling, validation, genai-fundamentals, reported-genai

**Start here: the concepts**
- **Structured output:** asking for machine-readable data, such as JSON, rather than prose.
- **Schema-constrained decoding:** the provider **forces** generation to follow a schema, by restricting which tokens are allowed.
- **Tool calling:** the model asks **your code** to run a function, then uses the result.

**The live scenario (functional requirement)**
*FR: "Read a CV into a typed record, then check the candidate's city against the live office list."* Extraction is structured output. Looking up offices is a tool call.

**What the interviewer is really checking**
The key limit: valid format doesn't mean a correct answer. And who actually executes tools.

**How I answer it** (120-second answer, point by point)
1. **Levels of reliability:**

| Approach | Guarantee |
|---|---|
| "Reply with JSON" in the prompt | None; may wrap it in prose |
| JSON mode | Valid JSON, any shape |
| Schema-constrained | Matches your schema, where supported |

2. **A valid shape isn't the truth.** `"age": 280` passes a schema. You still need business validation.
3. **Tool calling flow:** user asks; the model returns a tool name and arguments as JSON; **your code** runs it; the result goes back into the conversation; and the model writes the answer. **The model never runs anything itself.** Your code controls permissions.
4. **In Spring AI:** `chatClient.prompt()...call().entity(Candidate.class)` for typed output, and `@Tool`-annotated methods for tools.
5. **Handling failure:** validate, and on failure re-ask once with the error included (bank 66 Q5).

**Trade-offs and what can go wrong**
- Strict schemas may restrict some JSON Schema features, and can be slower on first use.
- A refusal or a truncated reply may still not parse, so handle both.
- Tool arguments are model output, and must be validated as untrusted input.

**Follow-ups to expect**
- *Tool design?* -> Bank 68 Q5.
- *More detail?* -> Bank 77 Q9 and bank 78 Q1.

**60-second answer**
"Structured output means asking for machine-readable data. Schema-constrained decoding goes further: the provider restricts generation so the output must match the schema. But valid format doesn't mean correct, as age 280 still passes, so I add business validation. Tool calling is different: the model returns a tool name and arguments, my code runs it and returns the result, and the model writes the answer. The model never executes anything itself, so permissions stay in my code, and I treat tool arguments as untrusted input."

### Q10 [mid] What makes a good prompt? Explain few-shot prompting, and prompts as code.
tags: prompt-engineering, few-shot, system-prompt, prompts-as-code, versioning, evaluation, genai-fundamentals, reported-genai

**Start here: the concepts**
- **Prompt engineering:** writing instructions a model follows reliably.
- **Few-shot:** showing examples so that the model copies the pattern.
- **Prompts as code:** versioned, reviewed and tested like any other code.

**The live scenario (functional requirement)**
*FR: "Classify support tickets into 8 categories."* "Classify this ticket" gives inconsistent labels, and someone edits the prompt in production on Friday with no record, then accuracy drops.

**What the interviewer is really checking**
Whether you have an engineering process, or just favourite phrases.

**How I answer it** (120-second answer, point by point)
1. **A good system prompt** has: role, goal, tools and when to use them, rules and limits, output format, and one or two examples.
2. **Be specific:** "Explain quantum computing" is weak. "Explain it to a software developer in simple terms, in short paragraphs, with a real-world analogy, avoiding heavy math" is much better.
3. **Few-shot:** 2 to 5 high-quality, representative examples in a consistent format, including tricky cases. Works well for classification and extraction.
4. **Prompts as code:**
   - Files in Git (`prompts/classify.md`), never strings scattered across Java.
   - PR review like any change.
   - Tests: golden cases that run in CI.
   - A version recorded with every request, for tracing and rollback.
   - Comparing versions on the same evaluation set before release.
5. **Separate instructions from data:** delimit user or retrieved content, and tell the model it's data. This reduces, but doesn't remove, prompt injection (bank 66 Q11).

**Trade-offs and what can go wrong**
- Long prompts cost tokens on every call.
- Examples can bias the model towards their exact content. Vary them.
- Prompts tuned on one model may behave differently on another, so re-evaluate after a model change.

**Follow-ups to expect**
- *How do you test a prompt?* -> Bank 78 Q11.
- *In Spring AI?* -> `PromptTemplate`, with templates as classpath resources.

**60-second answer**
"A good prompt states the role, goal, tools, rules, format and an example or two, and it's specific about audience and constraints. Few-shot means adding 2 to 5 representative examples in a consistent format, which is especially good for classification and extraction. And prompts should be treated as code: files in Git, reviewed in PRs, tested against golden cases in CI, with the version logged on every request for rollback. I also delimit user data from instructions, and re-evaluate whenever the model changes."

### Q11 [mid] How does AI memory work? Explain semantic, episodic and procedural memory.
tags: memory, semantic-memory, episodic-memory, procedural-memory, long-term-memory, privacy, genai-fundamentals, reported-genai

**Start here: the concepts**
- LLMs are **stateless**: every call starts fresh. Memory is a system you build, stored outside the model and loaded into context.
- **Semantic:** facts, such as "prefers Python". **Episodic:** events, such as "fixed the login bug last week". **Procedural:** how to do a task.

**The live scenario (functional requirement)**
*FR: "A coding assistant remembers the user's stack, their past fixes, and the team's release process."* These are three kinds of memory, with different storage and update rules.

**What the interviewer is really checking**
That you can map each type to a design, and that you think about wrong or stale memory.

**How I answer it** (120-second answer, point by point)

| Type | Holds | Example | Storage and use |
|---|---|---|---|
| Short-term | This conversation | Last 10 messages | Window or summary |
| Semantic | Stable facts | "Prefers Python over R" | Key-value profile or vector store; **update on change** |
| Episodic | Events, with dates | "Compared Delhi to Kochi fares" | Timestamped log, retrieved by similarity and recency |
| Procedural | How to do tasks | "Steps to build a monthly report" | Instructions or skill files, loaded when relevant |

The flow: extract important facts during a chat, store them with a date and source, retrieve the relevant ones next time, and add them to the context.

Rules that matter:
1. **Don't store everything.** Store preferences, decisions, lessons. Never passwords, API keys, or raw personal data.
2. **Memories go stale.** Update or remove them on change, and date them. An old fact stated confidently is a new kind of bug.
3. **Let users view and delete** what's saved, which privacy law often requires anyway.
4. **Scope them:** per user and tenant. A leak between users is a serious incident.

**Trade-offs and what can go wrong**
- **Memory poisoning:** a malicious document or message can plant false "facts" that persist. Treat extracted memories as untrusted, and consider approval for important ones.
- Retrieving too much recreates context distraction (Q12).

**Follow-ups to expect**
- *In Spring AI?* -> Bank 66 Q6.
- *Agents?* -> Bank 68 Q6.

**60-second answer**
"LLMs are stateless, so memory is something we build outside the model, then load into context. Short-term is the current conversation. Semantic memory holds facts like preferences, and needs updating when they change. Episodic memory holds dated events, retrieved by similarity and recency. Procedural memory holds how to do tasks, as instructions or skill files. The risks are stale facts, secrets stored by accident, cross-user leaks, and poisoned memories. So I store selectively, date everything, scope by user, and let users see and delete it."

### Q12 [senior] A long AI conversation gets worse over time. What goes wrong with context, and how do you fix it?
tags: context-rot, context-distraction, context-clash, long-conversations, conflict-resolution, genai-fundamentals, reported-genai

**Start here: the concepts**
- **Context rot:** quality falls as old, outdated information piles up.
- **Context distraction:** too much history, so the model ignores your actual instruction.
- **Context clash:** two pieces of context disagree.

**The live scenario (functional requirement)**
*FR: "A coding assistant over a two-hour session."* The user said "remove the map feature" and "use Next.js, not React". Later it produces a React implementation with the map, because earlier messages still sit in the context.

**What the interviewer is really checking**
Whether you can diagnose these separately, since each one has a different fix.

**How I answer it** (120-second answer, point by point)

| Failure | Symptom | Fix |
|---|---|---|
| **Rot** | Brings back decisions you've reversed | Summarise and drop outdated parts; start fresh when the topic changes |
| **Distraction** | Generic reply that misses the actual request | Select less; put the main instruction clearly at the end |
| **Clash** | Doc A says Python 3.11 and doc B says 3.9, so the answer mixes them | Remove the conflict, or state which source wins |

1. **Rot:** a rolling summary should record **current decisions**, not the chronological story, and old superseded messages get removed from the window.
2. **Distraction:** more context isn't better. Keep only relevant retrieved chunks, compress tool output, and re-state the task right before the question.
3. **Clash:** add metadata such as date and version, and give a precedence rule in the prompt: "Follow the newest policy. If sources conflict, say so." In RAG, retrieve only the current version.
4. **Detecting it:** run long-session tests in your evaluation, not only single-turn questions. Watch quality against conversation length.
5. **Design choice:** for long tasks, sub-agents with their own clean context keep noise out of the main thread (bank 68 Q9).

**Trade-offs and what can go wrong**
- Summaries can drop or distort a key constraint. Keep decisions as a structured list, not free text.
- "Start a new chat" is a real fix, but only if key state has been saved outside the chat first.

**How I'd monitor it**
Tokens per turn, turn count at abandon, user corrections such as "I already told you", and quality scores by session length.

**Follow-ups to expect**
- *What about poisoned context?* -> Malicious content in retrieved text is a security issue, not only quality. See bank 66 Q11.

**60-second answer**
"There are three separate failures. Rot: outdated information piles up, and the model brings back decisions you've reversed, so I keep a summary of current decisions and drop what's superseded. Distraction: so much context that it misses the actual instruction, so I select less and restate the task at the end. Clash: two sources disagree, so I remove the conflict or give a precedence rule, such as newest wins. I test long sessions in evaluation, and for long tasks I'd use sub-agents with their own clean context."
