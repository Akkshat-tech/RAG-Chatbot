# Short Reflection

**What did we learn about the difference between simply prompting an LLM
and building a knowledge-grounded AI system using RAG?**

*(Fill this in with your own group's genuine experience after you've run
the evaluation — a few starting prompts, based on what this prototype makes
visible, are below.)*

- Prompting alone gives you no way to check *why* the model said something;
  RAG gives you a source you can point to (or the honest absence of one).
- Building the domain guard and ambiguity wrappers made it obvious how much
  of "good" chatbot behaviour is actually pre/post-processing around the
  LLM call, not the LLM call itself.
- The groundedness wrapper occasionally disagreed with what felt like a
  correct answer, or missed a genuinely unsupported claim — worth discussing
  what that shows about the limits of using an LLM to check itself.
- Chunk size/overlap and top-k directly changed answer quality in ways that
  simply "asking a better question" never could — retrieval design is its
  own skill, separate from prompt design.
- Note any case where the system correctly said "insufficient information"
  instead of guessing, and contrast that with what a bare LLM would likely
  have done with the same question.
