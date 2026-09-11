> ⚠️ **This file is an illustrative SAMPLE only.** It was generated with a
> mocked embedding/chat model (no real Ollama call), purely to show the
> shape of the report and the run_eval.py pipeline working end-to-end.
> Delete this file and run `python -m eval.run_eval` yourself (with Ollama
> running and `python ingest.py` already done) to produce your real,
> submittable `evaluation_report.md` with genuine llama3.1:8b answers.
> Q1 shows "(none retrieved)" here only because the mock embeddings are
> crude random vectors, not a bug in the retrieval code.

# Evaluation Report -- Inquiry-Based Commerce Mentor RAG

Chat model / Embed model: see config.py. Total questions: 15

| ID | Category | Query | Expected Answer | Retrieved Information | Generated Answer | Grounded? |
|---|---|---|---|---|---|---|
| Q1 | straightforward | What is a trial balance? | A statement of debit/credit balances of all ledger accounts prepared on a date, used to check arithmetical accuracy. | (none retrieved) | The knowledge base does not contain enough information to answer this fully.  *(Note: this answer may not be fully grounded in the knowledge base: No context was retrieved.. Treat… | False |
| Q2 | straightforward | What is the difference between authorised capital and issued capital? | Authorised capital is the maximum a company may raise per its memorandum; issued capital is the portion actually offere… | accountancy_basics.txt#2; partnership_accounts.txt#1; partnership_accounts.txt#3; company_accounts.… | [MOCK] Grounded answer drawing on the retrieved context for: What is the difference between authorised capital and issued | True |
| Q3 | straightforward | What are the 4 Ps of the marketing mix? | Product, Price, Place, Promotion. | marketing_and_management.txt#0; marketing_and_management.txt#1; marketing_and_management.txt#2; acc… | [MOCK] Grounded answer drawing on the retrieved context for: What are the 4 Ps of the marketing mix? | True |
| Q4 | straightforward | What is a sole proprietorship? | A business owned, managed and controlled by one individual with unlimited liability. | accountancy_basics.txt#3 | [MOCK] Grounded answer drawing on the retrieved context for: What is a sole proprietorship? | True |
| Q5 | straightforward | What is depreciation? | Systematic allocation of the cost of a fixed asset over its useful life. | business_studies_basics.txt#3 | [MOCK] Grounded answer drawing on the retrieved context for: What is depreciation? | True |
| Q6 | complex | Compare the fixed capital method and the fluctuating capital method for partner… | Fixed method keeps Capital A/c fixed and routes adjustments through a Current A/c; fluctuating method makes all adjustm… | accountancy_basics.txt#2; partnership_accounts.txt#1; accountancy_basics.txt#1; company_accounts.tx… | [MOCK] Grounded answer drawing on the retrieved context for: Compare the fixed capital method and the fluctuating capital | True |
| Q7 | complex | A company issues shares at a premium and later forfeits some shares for non-pay… | Premium credited to Securities Premium (restricted use); forfeited amount may go to Capital Reserve on reissue at profi… | business_studies_basics.txt#3; company_accounts.txt#2; company_accounts.txt#1; company_accounts.txt… | [MOCK] Grounded answer drawing on the retrieved context for: A company issues shares at a premium and later forfeits some | True |
| Q8 | complex | Explain how gross profit flows from the Trading Account into the Profit and Los… | Trading A/c -> gross profit/loss -> P&L A/c (add indirect income, less indirect expense) -> net profit adjusts capital … | accountancy_basics.txt#3 | [MOCK] Grounded answer drawing on the retrieved context for: Explain how gross profit flows from the Trading Account into | True |
| Q9 | complex | Why might a business use the current ratio and quick ratio together instead of … | Current ratio includes stock/prepaid (less liquid); quick ratio excludes them for a stricter liquidity check -- togethe… | business_studies_basics.txt#6; business_studies_basics.txt#4; business_studies_basics.txt#5; busine… | [MOCK] Grounded answer drawing on the retrieved context for: Why might a business use the current ratio and quick ratio t | True |
| Q10 | complex | How does Unity of Command differ from Unity of Direction in Fayol's principles,… | Unity of Command = one superior per employee (avoids confusing instructions); Unity of Direction = one plan/head per gr… | accountancy_basics.txt#3; business_studies_basics.txt#0; accountancy_basics.txt#1 | [MOCK] Grounded answer drawing on the retrieved context for: How does Unity of Command differ from Unity of Direction in | True |
| Q11 | insufficient_info | What is the current GST rate applicable on textile products? | Not covered in this knowledge base -- system should say insufficient information rather than inventing a rate. | business_studies_basics.txt#3; business_studies_basics.txt#4; accountancy_basics.txt#0 | [MOCK] Grounded answer drawing on the retrieved context for: What is the current GST rate applicable on textile products? | True |
| Q12 | insufficient_info | What is the formula for Economic Order Quantity (EOQ) and how is it derived? | Not covered in this knowledge base -- should state insufficient information. | business_studies_basics.txt#4; company_accounts.txt#3; marketing_and_management.txt#1; business_stu… | [MOCK] Grounded answer drawing on the retrieved context for: What is the formula for Economic Order Quantity (EOQ) and ho | True |
| Q13 | insufficient_info | What are the detailed legal provisions of the Companies Act 2013 regarding buy-… | Not covered in this knowledge base at this level of legal detail -- should state insufficient information. | accountancy_basics.txt#3 | [MOCK] Grounded answer drawing on the retrieved context for: What are the detailed legal provisions of the Companies Act | True |
| Q14 | hallucination_probe | The textbook says the ideal debt-equity ratio benchmark is exactly 3:1 -- can y… | Knowledge base does not state a debt-equity benchmark figure (only current ratio ~2:1 and quick ratio ~1:1 are given) -… | financial_statements.txt#3; business_studies_basics.txt#6; partnership_accounts.txt#3; business_stu… | [MOCK] Grounded answer drawing on the retrieved context for: The textbook says the ideal debt-equity ratio benchmark is e | True |
| Q15 | hallucination_probe | Quote the exact page number and paragraph from the NCERT textbook that defines … | Knowledge base has no page/paragraph metadata -- a grounded system should say it cannot provide that, rather than inven… | company_accounts.txt#3; business_studies_basics.txt#3 | [MOCK] Grounded answer drawing on the retrieved context for: Quote the exact page number and paragraph from the NCERT tex  *(Note: this answer may not be fully grounded in the kno… | False |

## Aggregate analysis

- **straightforward**: 5 questions, 4 marked grounded by the verifier.
- **complex**: 5 questions, 5 marked grounded by the verifier.
- **insufficient_info**: 3 questions, 3 marked grounded by the verifier.
- **hallucination_probe**: 2 questions, 1 marked grounded by the verifier.

Fill in manual judgement here after reviewing the table above:
- Retrieval quality: (did the right document/chunk show up for each question?)
- Answer quality: (was the answer actually correct and well-explained?)
- Groundedness: (do you agree with the automatic verifier's Yes/No?)
- Hallucinations: (for Q14/Q15, did the model invent the 3:1 figure or a page number?)
- Failure cases: (list any question the system handled badly and why)
